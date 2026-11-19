from fastapi import Depends, HTTPException, Request

from security import validate_request_origin
from service_client import ServiceUnavailable, UpstreamError, get_json


def current_user(request: Request) -> dict:
    validate_request_origin(request)
    headers = {
        name: request.headers[name]
        for name in ("cookie", "authorization")
        if name in request.headers
    }
    try:
        result = get_json("AUTH_SERVICE_URL", "/api/auth/me", headers)
    except UpstreamError as error:
        if error.status_code == 401:
            raise HTTPException(status_code=401, detail="Authentication required.") from error
        raise HTTPException(status_code=502, detail="Authentication service rejected the request.") from error
    except ServiceUnavailable as error:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable.") from error
    return result["user"]


def require_permission(permission: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        if permission not in user.get("permissions", []):
            raise HTTPException(status_code=403, detail="You are not allowed to perform this action.")
        return user

    return dependency
