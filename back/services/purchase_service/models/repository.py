from db import connection
from security import token_pepper


def init_db() -> None:
    token_pepper()
    with connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS purchase_carts (
                user_id INTEGER PRIMARY KEY,
                items JSONB NOT NULL DEFAULT '[]'::jsonb
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS purchase_purchases (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                items JSONB NOT NULL,
                total DOUBLE PRECISION NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_payment',
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS purchase_checkouts (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                items JSONB NOT NULL,
                total DOUBLE PRECISION NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_confirmation',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '10 minutes',
                confirmed_at TIMESTAMPTZ
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS purchase_checkout_codes (
                checkout_id TEXT PRIMARY KEY REFERENCES purchase_checkouts(id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute("ALTER TABLE purchase_purchases ADD COLUMN IF NOT EXISTS checkout_id TEXT")
        db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS purchase_purchases_checkout_id_idx
            ON purchase_purchases (checkout_id) WHERE checkout_id IS NOT NULL
            """
        )
