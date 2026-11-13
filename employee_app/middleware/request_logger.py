import time

from fastapi.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from models.security import RequestLog
from security_database import SecuritySessionLocal
from services import system_metrics_service
from services.request_utils import get_client_ip, get_user_id_from_request
from services.ws_manager import manager as ws_manager


def _write_log(entry: dict):
    db = SecuritySessionLocal()

    try:
        log_obj = RequestLog(**entry)
        db.add(log_obj)
        db.commit()
        db.refresh(log_obj)

        broadcast_data = dict(entry)
        broadcast_data["id"] = log_obj.id
        broadcast_data["timestamp"] = log_obj.timestamp.isoformat() + "Z"
        ws_manager.broadcast_sync("request_log", broadcast_data)
    except Exception as error:
        # Logging must never break a real request.
        print(f"[request_logger] could not write log: {error}")
        db.rollback()
    finally:
        db.close()


class RequestLoggerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        if request.url.path.startswith("/static"):
            return await call_next(request)

        system_metrics_service.count_request()
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000

            # Only metadata is stored. Request bodies (passwords!) are not.
            await run_in_threadpool(
                _write_log,
                {
                    "ip_address": get_client_ip(request),
                    "method": request.method,
                    "endpoint": request.url.path[:255],
                    "query_string": (request.url.query or None) and request.url.query[:500],
                    "status_code": status_code,
                    "response_time_ms": round(elapsed_ms, 2),
                    "user_agent": (request.headers.get("user-agent") or "")[:255] or None,
                    "user_id": get_user_id_from_request(request),
                    "suspicion_score": getattr(request.state, "suspicion_score", None),
                    "is_trap": bool(getattr(request.state, "is_trap", False)),
                },
            )
