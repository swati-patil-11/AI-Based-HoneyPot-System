from fastapi import Request
from jose import JWTError, jwt

from config import ALGORITHM, SECRET_KEY


def get_client_ip(request: Request) -> str:
    """
    Source IP of the TCP connection.

    X-Forwarded-For is deliberately NOT trusted: any client can fake it.
    (This is fine for a localhost lab. Behind a real proxy you would
    configure the proxy as trusted instead.)
    """
    if request.client:
        return request.client.host

    return "unknown"


def get_user_id_from_request(request: Request) -> int | None:
    """Read the user id from the JWT, if one is sent. Never raises."""
    header = request.headers.get("authorization", "")

    if not header.lower().startswith("bearer "):
        return None

    token = header[7:].strip()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None


def get_role_from_request(request: Request) -> str | None:
    """Read the role claim from the JWT, if a valid one is sent. Never raises."""
    header = request.headers.get("authorization", "")

    if not header.lower().startswith("bearer "):
        return None

    try:
        payload = jwt.decode(header[7:].strip(), SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("role")
    except JWTError:
        return None
