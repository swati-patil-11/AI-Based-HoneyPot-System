from pathlib import Path
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from security_database import SecuritySessionLocal
from services.blocking_service import get_active_block
from services.request_utils import get_client_ip


# Admin security endpoints stay reachable so you can never lock yourself
# out. They still require a valid admin JWT.
EXEMPT_PREFIXES = ("/admin/security", "/security-dashboard", "/static", "/ws/admin")

_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _find_block(ip_address: str):
    db = SecuritySessionLocal()

    try:
        block = get_active_block(db, ip_address)

        if block is None:
            return None

        return {
            "expires_at": block.expires_at.isoformat() + "Z",
            "reason": block.reason or "High Suspicious Behavior / Security Policy Violation",
        }
    finally:
        db.close()


class IPBlockerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        if request.url.path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)

        ip_address = get_client_ip(request)

        block_data = await run_in_threadpool(_find_block, ip_address)

        if block_data:
            accept = request.headers.get("accept", "")
            if "text/html" in accept:
                return _templates.TemplateResponse(
                    request=request,
                    name="blocked.html",
                    context={
                        "ip_address": ip_address,
                        "reason": block_data["reason"],
                        "expires_at": block_data["expires_at"],
                    },
                    status_code=403,
                )

            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Your IP address is temporarily blocked.",
                    "reason": block_data["reason"],
                    "blocked_until_utc": block_data["expires_at"],
                },
            )

        return await call_next(request)

