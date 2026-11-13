from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import config as cfg
from services import blocking_service, detection_service, trap_service
from services.request_utils import get_client_ip, get_role_from_request
from services.ws_manager import manager as ws_manager


class DetectionMiddleware(BaseHTTPMiddleware):
    """
    1. Score the source IP (Phase 6).
    2. If the score reached the trap level (or the IP is already trapped)
       and the request is for employee data, answer with synthetic data
       and never call the real route (Phase 7).

    The score is NEVER sent to the client; it goes to the logger through
    request.state.
    """

    async def dispatch(self, request, call_next):

        path = request.url.path

        if path.startswith(cfg.DETECTION_EXEMPT_PREFIXES):
            return await call_next(request)

        ip_address = get_client_ip(request)

        result = detection_service.record_request(
            ip=ip_address,
            method=request.method,
            path=path,
            params=dict(request.query_params),
            user_agent=request.headers.get("user-agent"),
        )

        request.state.suspicion_score = result.score
        request.state.suspicion_level = result.level

        ws_manager.broadcast_sync(
            "score_update",
            {
                "ip_address": ip_address,
                "score": result.score,
                "level": result.level,
                "breakdown": result.breakdown,
                "metrics": result.metrics,
            },
        )

        if cfg.TRAP_ENABLED:
            plan = trap_service.classify_request(
                request.method, path, request.query_params
            )

            flagged = (
                result.score >= cfg.TRAP_THRESHOLD
                or trap_service.is_sticky(ip_address)
            )

            # Only requests the real app would accept are redirected
            # (valid token, admin/hr role), so a trapped client cannot tell
            # the difference from a "no token" response.
            if (
                plan
                and flagged
                and get_role_from_request(request) in ("admin", "hr")
            ):
                reply = await run_in_threadpool(
                    trap_service.serve_redirected, ip_address, plan
                )

                request.state.is_trap = True

                # the trap said "429": count it, block the source if it keeps going
                if reply.status == 429:
                    await run_in_threadpool(
                        blocking_service.register_trap_refusal, ip_address
                    )

                return JSONResponse(
                    content=reply.body,
                    status_code=reply.status,
                    headers=reply.headers,
                )

        response = await call_next(request)

        if response.status_code == 401:
            detection_service.record_auth_failure(ip_address)

        return response
