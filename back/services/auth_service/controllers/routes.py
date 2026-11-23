import os
import secrets
from datetime import timedelta

from db import connection
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from psycopg.errors import UniqueViolation
from psycopg.types.json import Json
from security import hash_one_time_code, hash_password, hash_token, validate_request_origin, verify_password

from ..models import AuthResponse, CodeInput, EmailInput, LoginRequest, PhoneInput, RegisterRequest, ResetPasswordInput
from ..models.repository import create_email_token, user_from_row


router = APIRouter()
SESSION_COOKIE = "gart_session"
SESSION_HOURS = 12


def _session_token(cookie_token: str | None, authorization: str | None) -> str:
    if cookie_token:
        return cookie_token
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return ""


def current_user(
    request: Request,
    gart_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> dict:
    validate_request_origin(request)
    token = _session_token(gart_session, authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    with connection() as db:
        row = db.execute(
            """
            SELECT u.* FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id
            WHERE s.session_hash = %s AND s.expires_at > CURRENT_TIMESTAMP
            """,
            (hash_token(token),),
        ).fetchone()
    if row is None or not row["active"]:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user_from_row(row)


def _set_session(response: Response, token: str) -> None:
    secure_cookie = os.getenv(
        "COOKIE_SECURE",
        "true" if os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"} else "false",
    ).lower() == "true"
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=secure_cookie,
        samesite="strict",
        max_age=SESSION_HOURS * 60 * 60,
        path="/",
    )


def _new_email_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _verify_code(db, user_id: int, purpose: str, code: str) -> bool:
    row = db.execute(
        """
        SELECT id, token_hash, attempts FROM auth_email_tokens
        WHERE user_id = %s AND purpose = %s AND consumed_at IS NULL
            AND expires_at > CURRENT_TIMESTAMP
        ORDER BY id DESC LIMIT 1 FOR UPDATE
        """,
        (user_id, purpose),
    ).fetchone()
    if row is None or row["attempts"] >= 5:
        return False
    if not secrets.compare_digest(row["token_hash"], hash_one_time_code(code)):
        db.execute("UPDATE auth_email_tokens SET attempts = attempts + 1 WHERE id = %s", (row["id"],))
        return False
    db.execute(
        "UPDATE auth_email_tokens SET consumed_at = CURRENT_TIMESTAMP WHERE id = %s",
        (row["id"],),
    )
    return True


def _issue_demo_code(user_id: int, purpose: str, message: str) -> dict[str, bool | str]:
    code = _new_email_code()
    with connection() as db:
        latest = db.execute(
            """
            SELECT created_at FROM auth_email_tokens
            WHERE user_id = %s AND purpose = %s AND created_at > CURRENT_TIMESTAMP - INTERVAL '60 seconds'
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, purpose),
        ).fetchone()
        if latest:
            raise HTTPException(status_code=429, detail="Espera un minuto antes de solicitar otro código.")
        db.execute(
            """
            UPDATE auth_email_tokens SET consumed_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND purpose = %s AND consumed_at IS NULL
            """,
            (user_id, purpose),
        )
        create_email_token(db, user_id, purpose, hash_one_time_code(code))
    return {"ok": True, "mode": "demo", "message": message, "demo_code": code}


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    validate_request_origin(request)
    client_ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )
    auth_error = None
    with connection() as db:
        attempt = db.execute(
            """
            SELECT attempts, locked_until FROM auth_login_attempts
            WHERE username = %s AND client_ip = %s FOR UPDATE
            """,
            (payload.username, client_ip),
        ).fetchone()
        now = db.execute(
            "SELECT CURRENT_TIMESTAMP AS now"
        ).fetchone()["now"]
        if attempt and attempt["locked_until"] and attempt["locked_until"] > now:
            auth_error = 429
        else:
            row = db.execute("SELECT * FROM auth_users WHERE username = %s", (payload.username,)).fetchone()
            password_ok = verify_password(payload.password, row["password"]) if row else verify_password(
                payload.password, "pbkdf2_sha256$310000$" + "00" * 16 + "$" + "00" * 32
            )
            if row is None or not password_ok or not row["active"]:
                attempts = attempt["attempts"] if attempt and attempt["locked_until"] is None else 0
                next_attempts = attempts + 1
                db.execute(
                    """
                    INSERT INTO auth_login_attempts (username, client_ip, attempts, locked_until)
                    VALUES (%s, %s, %s, CASE WHEN %s >= 5 THEN CURRENT_TIMESTAMP + INTERVAL '15 minutes' END)
                    ON CONFLICT (username, client_ip) DO UPDATE SET
                        attempts = EXCLUDED.attempts, locked_until = EXCLUDED.locked_until
                    """,
                    (payload.username, client_ip, next_attempts, next_attempts),
                )
                auth_error = 401
            else:
                db.execute(
                    "DELETE FROM auth_login_attempts WHERE username = %s AND client_ip = %s",
                    (payload.username, client_ip),
                )
                raw_token = secrets.token_urlsafe(32)
                db.execute(
                    """
                    INSERT INTO auth_sessions (session_hash, user_id, expires_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP + %s)
                    """,
                    (hash_token(raw_token), row["id"], timedelta(hours=SESSION_HOURS)),
                )
                user = user_from_row(row)
    if auth_error == 429:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Inténtalo más tarde.")
    if auth_error:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    _set_session(response, raw_token)
    return {"ok": True, "user": user}


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response) -> dict:
    validate_request_origin(request)
    permissions = ["works:read", "galleries:read", "content:read"]
    role = "VISITANTE"
    try:
        with connection() as db:
            cursor = db.execute(
                """
                INSERT INTO auth_users (username, email, phone, password, role, permissions, active, email_verified, phone_verified)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, FALSE, FALSE) RETURNING *
                """,
                (
                    payload.username, payload.email.strip().lower(), payload.phone,
                    hash_password(payload.password), role, Json(permissions),
                ),
            )
            row = cursor.fetchone()
            raw_token = secrets.token_urlsafe(32)
            db.execute(
                """
                INSERT INTO auth_sessions (session_hash, user_id, expires_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP + %s)
                """,
                (hash_token(raw_token), row["id"], timedelta(hours=SESSION_HOURS)),
            )
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="El usuario o correo ya está registrado.") from error
    _set_session(response, raw_token)
    return {"ok": True, "user": user_from_row(row)}


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return {"authenticated": True, "user": user}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    gart_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, bool]:
    validate_request_origin(request)
    token = _session_token(gart_session, authorization)
    if token:
        with connection() as db:
            db.execute("DELETE FROM auth_sessions WHERE session_hash = %s", (hash_token(token),))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    return {"ok": True}


@router.put("/email")
def update_email(payload: EmailInput, user: dict = Depends(current_user)) -> dict:
    email = payload.email.strip().lower()
    try:
        with connection() as db:
            db.execute(
                "UPDATE auth_users SET email = %s, email_verified = FALSE WHERE id = %s",
                (email, user["id"]),
            )
            db.execute(
                """
                UPDATE auth_email_tokens SET consumed_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND consumed_at IS NULL
                """,
                (user["id"],),
            )
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="Ese correo ya está asociado a otra cuenta.") from error
    return {"ok": True, "email_verified": False}


@router.put("/phone")
def update_phone(payload: PhoneInput, user: dict = Depends(current_user)) -> dict:
    with connection() as db:
        row = db.execute(
            "UPDATE auth_users SET phone = %s, phone_verified = FALSE WHERE id = %s RETURNING *",
            (payload.phone, user["id"]),
        ).fetchone()
        db.execute(
            """
            UPDATE auth_email_tokens SET consumed_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND purpose = 'verify_phone' AND consumed_at IS NULL
            """,
            (user["id"],),
        )
    return {"ok": True, "user": user_from_row(row)}


@router.post("/email/verification/request")
def request_email_verification(user: dict = Depends(current_user)) -> dict[str, bool | str]:
    if not user["email"]:
        raise HTTPException(status_code=422, detail="Agrega un correo antes de verificarlo.")
    if user["email_verified"]:
        return {"ok": True, "mode": "demo", "message": "El correo ya está verificado."}
    return _issue_demo_code(
        user["id"], "verify_email",
        "Modo demostración: en producción se enviaría un código OTP al correo registrado.",
    )


@router.post("/email/verification/confirm")
def confirm_email_verification(
    payload: CodeInput, user: dict = Depends(current_user)
) -> dict[str, bool]:
    with connection() as db:
        valid = _verify_code(db, user["id"], "verify_email", payload.code)
        if valid:
            db.execute("UPDATE auth_users SET email_verified = TRUE WHERE id = %s", (user["id"],))
    if not valid:
        raise HTTPException(status_code=400, detail="Código incorrecto.")
    return {"ok": True, "email_verified": True}


@router.post("/phone/verification/request")
def request_phone_verification(user: dict = Depends(current_user)) -> dict[str, bool | str]:
    if not user.get("phone"):
        raise HTTPException(status_code=422, detail="Agrega un teléfono antes de verificarlo.")
    if user["phone_verified"]:
        return {"ok": True, "mode": "demo", "message": "El teléfono ya está verificado."}
    return _issue_demo_code(
        user["id"], "verify_phone",
        "Modo demostración: en producción se enviaría un código OTP por SMS al teléfono registrado.",
    )


@router.post("/phone/verification/confirm")
def confirm_phone_verification(
    payload: CodeInput, user: dict = Depends(current_user)
) -> dict[str, bool]:
    with connection() as db:
        valid = _verify_code(db, user["id"], "verify_phone", payload.code)
        if valid:
            db.execute("UPDATE auth_users SET phone_verified = TRUE WHERE id = %s", (user["id"],))
    if not valid:
        raise HTTPException(status_code=400, detail="Código incorrecto.")
    return {"ok": True, "phone_verified": True}


@router.post("/artist/request")
def request_artist_role(user: dict = Depends(current_user)) -> dict[str, bool | dict]:
    if user["role"] == "ARTISTA":
        return {"ok": True, "user": user}
    if user["role"] != "VISITANTE":
        raise HTTPException(status_code=403, detail="Esta cuenta no puede solicitar el rol de artista.")
    if not user["email_verified"] or not user["phone_verified"]:
        raise HTTPException(status_code=403, detail="Verifica correo y teléfono antes de solicitar el rol de artista.")
    permissions = sorted(set(user["permissions"]) | {"works:submit"})
    with connection() as db:
        row = db.execute(
            "UPDATE auth_users SET role = 'ARTISTA', permissions = %s WHERE id = %s RETURNING *",
            (Json(permissions), user["id"]),
        ).fetchone()
    return {"ok": True, "user": user_from_row(row)}


@router.post("/password/forgot")
def forgot_password(payload: EmailInput, request: Request) -> dict[str, bool | str]:
    validate_request_origin(request)
    return {
        "ok": True,
        "mode": "demo",
        "message": "Modo demostración: la recuperación por correo no está habilitada y no se envió ningún mensaje.",
    }


@router.post("/password/reset")
def reset_password(payload: ResetPasswordInput, request: Request) -> dict[str, bool]:
    validate_request_origin(request)
    valid = False
    with connection() as db:
        row = db.execute(
            "SELECT id FROM auth_users WHERE lower(email) = %s AND email_verified = TRUE AND active = TRUE",
            (payload.email.strip().lower(),),
        ).fetchone()
        valid = row is not None and _verify_code(db, row["id"], "reset_password", payload.code)
        if valid:
            db.execute("UPDATE auth_users SET password = %s WHERE id = %s", (hash_password(payload.password), row["id"]))
            db.execute("DELETE FROM auth_sessions WHERE user_id = %s", (row["id"],))
    if not valid:
        raise HTTPException(status_code=400, detail="El código no es válido o ha vencido.")
    return {"ok": True}
