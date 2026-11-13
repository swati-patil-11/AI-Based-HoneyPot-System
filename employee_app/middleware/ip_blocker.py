from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from security_database import SecuritySessionLocal
from services.blocking_service import get_active_block
from services.request_utils import get_client_ip


# Admin security endpoints stay reachable so you can never lock yourself
# out. They still require a valid admin JWT.
EXEMPT_PREFIXES = ("/admin/security",)


def _find_block(ip_address: str):
    db = SecuritySessionLocal()

    try:
        block = get_active_block(db, ip_address)

        if block is None:
            return None

        return block.expires_at.isoformat() + "Z"
    finally:
        db.close()


class IPBlockerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        if request.url.path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)

        ip_address = get_client_ip(request)

        expires_at = await run_in_threadpool(_find_block, ip_address)

        if expires_at:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Your IP address is temporarily blocked.",
                    "blocked_until_utc": expires_at,
                },
            )

        return await call_next(request)
