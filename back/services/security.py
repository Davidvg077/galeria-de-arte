import hashlib
import hmac
import os
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

_PBKDF2_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_pepper() -> str:
    pepper = os.getenv("TOKEN_PEPPER")
    if pepper:
        if len(pepper) < 32:
            raise RuntimeError("TOKEN_PEPPER must contain at least 32 characters.")
        return pepper
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment in {"production", "prod"}:
        raise RuntimeError("TOKEN_PEPPER is required in production.")
    return "gart-gallery-development-token-pepper-not-for-production"


def hash_one_time_code(code: str) -> str:
    return hmac.new(token_pepper().encode(), code.encode(), hashlib.sha256).hexdigest()


def validate_request_origin(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if not origin:
        return
    configured_origin = os.getenv("FRONTEND_ORIGIN", "").rstrip("/")
    if configured_origin and origin.rstrip("/").casefold() == configured_origin.casefold():
        return
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    origin_parts = urlsplit(origin)
    if (
        not host
        or origin_parts.scheme.casefold() != scheme.casefold()
        or origin_parts.netloc.casefold() != host.casefold()
        or origin_parts.path not in ("", "/")
        or origin_parts.query
        or origin_parts.fragment
    ):
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
