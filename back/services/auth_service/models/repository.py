import os

from db import connection
from security import hash_password, hash_token, token_pepper


def init_db() -> None:
    token_pepper()
    with connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                permissions JSONB NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
        db.execute("ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS email TEXT")
        db.execute(
            "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE"
        )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS auth_users_email_lower_idx "
            "ON auth_users (lower(email)) WHERE email IS NOT NULL"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES auth_users(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row["column_name"]
            for row in db.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = 'auth_sessions'
                """
            )
        }
        if "token" in columns:
            db.execute("ALTER TABLE auth_sessions RENAME COLUMN token TO session_hash")
            columns.remove("token")
            columns.add("session_hash")
            for row in db.execute("SELECT session_hash FROM auth_sessions").fetchall():
                db.execute(
                    "UPDATE auth_sessions SET session_hash = %s WHERE session_hash = %s",
                    (hash_token(row["session_hash"]), row["session_hash"]),
                )
        if "session_hash" not in columns:
            db.execute("ALTER TABLE auth_sessions ADD COLUMN session_hash TEXT")
        db.execute("ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ")
        db.execute("DELETE FROM auth_sessions WHERE expires_at IS NULL OR expires_at <= CURRENT_TIMESTAMP")
        db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_sessions_session_hash_idx
            ON auth_sessions (session_hash)
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_login_attempts (
                username TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMPTZ,
                PRIMARY KEY (username, client_ip)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_email_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                purpose TEXT NOT NULL CHECK (purpose IN ('verify_email', 'reset_password')),
                token_hash TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ NOT NULL,
                consumed_at TIMESTAMPTZ
            )
            """
        )

        for row in db.execute("SELECT id, username, password FROM auth_users").fetchall():
            if not row["password"].startswith("pbkdf2_sha256$"):
                db.execute(
                    "UPDATE auth_users SET password = %s, active = CASE "
                    "WHEN username = 'admin' AND password = 'admin123' THEN FALSE ELSE active END "
                    "WHERE id = %s",
                    (hash_password(row["password"]), row["id"]),
                )

        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_password:
            if len(admin_password) < 12:
                raise RuntimeError("ADMIN_PASSWORD must contain at least 12 characters.")
            admin_user = os.getenv("ADMIN_USER", "admin")
            db.execute(
                """
                INSERT INTO auth_users (username, password, role, permissions, active)
                VALUES (%s, %s, 'WEBMASTER',
                    '["works:read","works:write","galleries:read","galleries:write","content:read","content:write"]'::jsonb, TRUE)
                ON CONFLICT (username) DO UPDATE SET
                    password = EXCLUDED.password, role = 'WEBMASTER',
                    permissions = EXCLUDED.permissions, active = TRUE
                """,
                (admin_user, hash_password(admin_password)),
            )


def user_from_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "email_verified": row["email_verified"],
        "role": row["role"],
        "permissions": row["permissions"],
        "active": row["active"],
    }


def create_email_token(db, user_id: int, purpose: str, token_hash: str) -> None:
    db.execute(
        """
        INSERT INTO auth_email_tokens (user_id, purpose, token_hash, expires_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '10 minutes')
        """,
        (user_id, purpose, token_hash),
    )
