import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from auth_client import current_user
from db import connection
from email_service import EmailConfigurationError, send_email
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from psycopg.errors import UniqueViolation
from psycopg.types.json import Json
from security import hash_one_time_code
from service_client import ServiceUnavailable, UpstreamError, get_json

from ..models import Cart, CartItem, Checkout, CheckoutInput, ConfirmInput, Purchase


router = APIRouter()
logger = logging.getLogger(__name__)


def _assert_owner(requested_id: int, user: dict) -> None:
    if requested_id != user["id"]:
        raise HTTPException(status_code=403, detail="You are not allowed to access this cart.")


def _items_from_json(value: list[dict] | str) -> list[CartItem]:
    return [CartItem(**item) for item in (json.loads(value) if isinstance(value, str) else value)]


def _purchase_from_row(row: dict) -> Purchase:
    items = row["items"]
    if isinstance(items, str):
        items = json.loads(items)
    return Purchase(
        id=row["id"],
        user_id=row["user_id"],
        items=items,
        total=row["total"],
        status=row["status"],
        created_at=row["created_at"],
    )


def _authenticated_headers(request: Request) -> dict[str, str]:
    return {
        name: request.headers[name]
        for name in ("cookie", "authorization")
        if name in request.headers
    }


def _load_work(request: Request, work_id: int) -> dict:
    try:
        work = get_json("WORKS_SERVICE_URL", f"/api/works/{work_id}", _authenticated_headers(request))
    except UpstreamError as error:
        if error.status_code == 404:
            raise HTTPException(status_code=422, detail="Una obra solicitada no existe.") from error
        raise HTTPException(status_code=502, detail="No se pudo validar una obra.") from error
    except ServiceUnavailable as error:
        raise HTTPException(status_code=503, detail="El catálogo de obras no está disponible.") from error
    if not work.get("available") or work.get("price") is None:
        raise HTTPException(status_code=409, detail="Una obra ya no está disponible para compra.")
    return work


def _send_purchase_code(email: str, code: str) -> None:
    try:
        send_email(
            email,
            "Confirma tu pedido GART Gallery",
            f"Tu código de confirmación es {code}. Vence en 10 minutos. "
            "El pedido quedará pendiente de pago; este paso no realiza ningún cobro.",
        )
    except EmailConfigurationError as error:
        logger.error("Purchase email delivery failed: %s", error)
        raise HTTPException(status_code=503, detail="El servicio de correo no está disponible.") from error


@router.get("/cart/{user_id}", response_model=Cart)
def get_cart(user_id: int, user: dict = Depends(current_user)) -> Cart:
    _assert_owner(user_id, user)
    with connection() as db:
        row = db.execute("SELECT items FROM purchase_carts WHERE user_id = %s", (user_id,)).fetchone()
        if row is None:
            db.execute("INSERT INTO purchase_carts (user_id, items) VALUES (%s, '[]')", (user_id,))
            return Cart(user_id=user_id)
    return Cart(user_id=user_id, items=_items_from_json(row["items"]))


@router.put("/cart/{user_id}", response_model=Cart)
def update_cart(user_id: int, items: list[CartItem], user: dict = Depends(current_user)) -> Cart:
    _assert_owner(user_id, user)
    if len(items) > 50:
        raise HTTPException(status_code=422, detail="El carrito admite hasta 50 obras.")
    with connection() as db:
        db.execute(
            """
            INSERT INTO purchase_carts (user_id, items) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET items = EXCLUDED.items
            """,
            (user_id, Json([item.model_dump() for item in items])),
        )
    return Cart(user_id=user_id, items=items)


@router.delete("/cart/{user_id}")
def clear_cart(user_id: int, user: dict = Depends(current_user)) -> dict[str, bool]:
    _assert_owner(user_id, user)
    with connection() as db:
        db.execute(
            """
            INSERT INTO purchase_carts (user_id, items) VALUES (%s, '[]')
            ON CONFLICT (user_id) DO UPDATE SET items = '[]'::jsonb
            """,
            (user_id,),
        )
    return {"ok": True}


@router.post("/purchases/checkout", response_model=Checkout, status_code=status.HTTP_202_ACCEPTED)
def create_checkout(
    payload: CheckoutInput,
    request: Request,
    idempotency_key: str = Header(min_length=16, max_length=128, alias="Idempotency-Key"),
    user: dict = Depends(current_user),
) -> Checkout:
    if not user.get("email_verified") or not user.get("email"):
        raise HTTPException(status_code=403, detail="Verifica tu correo antes de iniciar una compra.")

    with connection() as db:
        existing = db.execute(
            "SELECT * FROM purchase_checkouts WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()
    if existing:
        if existing["user_id"] != user["id"]:
            raise HTTPException(status_code=409, detail="La clave de operación ya fue utilizada.")
        if existing["expires_at"] <= datetime.now(timezone.utc) and existing["status"] == "pending_confirmation":
            raise HTTPException(status_code=410, detail="La confirmación del pedido venció.")
        return Checkout(
            id=existing["id"], total=existing["total"], status=existing["status"],
            expires_at=existing["expires_at"],
        )

    snapshots = []
    total = Decimal("0")
    for item in payload.items:
        work = _load_work(request, item.work_id)
        price = Decimal(str(work["price"]))
        if price < 0:
            raise HTTPException(status_code=409, detail="El precio de una obra no es válido.")
        total += price * item.quantity
        snapshots.append(
            {
                "work_id": item.work_id,
                "title": work["title"],
                "quantity": item.quantity,
                "unit_price": str(price),
            }
        )

    checkout_id = str(uuid.uuid4())
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        with connection() as db:
            cursor = db.execute(
                """
                INSERT INTO purchase_checkouts (id, user_id, idempotency_key, items, total)
                VALUES (%s, %s, %s, %s, %s) RETURNING expires_at
                """,
                (checkout_id, user["id"], idempotency_key, Json(snapshots), float(total)),
            )
            row = cursor.fetchone()
            db.execute(
                "INSERT INTO purchase_checkout_codes (checkout_id, code_hash) VALUES (%s, %s)",
                (checkout_id, hash_one_time_code(code)),
            )
    except UniqueViolation:
        with connection() as db:
            existing = db.execute(
                "SELECT * FROM purchase_checkouts WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
        if existing and existing["user_id"] == user["id"]:
            return Checkout(
                id=existing["id"], total=existing["total"], status=existing["status"],
                expires_at=existing["expires_at"],
            )
        raise HTTPException(status_code=409, detail="La clave de operación ya fue utilizada.")
    try:
        _send_purchase_code(user["email"], code)
    except HTTPException:
        with connection() as db:
            db.execute("DELETE FROM purchase_checkouts WHERE id = %s", (checkout_id,))
        raise
    return Checkout(
        id=checkout_id,
        total=float(total),
        status="pending_confirmation",
        expires_at=row["expires_at"],
    )


@router.post("/purchases", response_model=Checkout, status_code=status.HTTP_202_ACCEPTED, deprecated=True)
def create_purchase_compatibility(
    payload: CheckoutInput,
    request: Request,
    idempotency_key: str = Header(min_length=16, max_length=128, alias="Idempotency-Key"),
    user: dict = Depends(current_user),
) -> Checkout:
    return create_checkout(payload, request, idempotency_key, user)


@router.post("/purchases/{checkout_id}/code")
def resend_checkout_code(
    checkout_id: str,
    user: dict = Depends(current_user),
) -> dict[str, bool]:
    if not user.get("email_verified") or not user.get("email"):
        raise HTTPException(status_code=403, detail="Verifica tu correo antes de iniciar una compra.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    with connection() as db:
        checkout = db.execute(
            "SELECT id, status, expires_at FROM purchase_checkouts WHERE id = %s AND user_id = %s FOR UPDATE",
            (checkout_id, user["id"]),
        ).fetchone()
        if checkout is None:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        if checkout["status"] != "pending_confirmation" or checkout["expires_at"] <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="La confirmación del pedido venció.")
        recent = db.execute(
            "SELECT 1 FROM purchase_checkout_codes WHERE checkout_id = %s AND created_at > CURRENT_TIMESTAMP - INTERVAL '60 seconds'",
            (checkout_id,),
        ).fetchone()
        if recent:
            raise HTTPException(status_code=429, detail="Espera un minuto antes de solicitar otro código.")
        db.execute(
            """
            INSERT INTO purchase_checkout_codes (checkout_id, code_hash)
            VALUES (%s, %s)
            ON CONFLICT (checkout_id) DO UPDATE SET
                code_hash = EXCLUDED.code_hash, attempts = 0, created_at = CURRENT_TIMESTAMP
            """,
            (checkout_id, hash_one_time_code(code)),
        )
    try:
        _send_purchase_code(user["email"], code)
    except HTTPException:
        with connection() as db:
            db.execute("DELETE FROM purchase_checkout_codes WHERE checkout_id = %s", (checkout_id,))
        raise
    return {"ok": True}


@router.post("/purchases/{checkout_id}/confirm", response_model=Purchase)
def confirm_checkout(
    checkout_id: str,
    payload: ConfirmInput,
    user: dict = Depends(current_user),
) -> Purchase:
    invalid_code = False
    with connection() as db:
        checkout = db.execute(
            "SELECT * FROM purchase_checkouts WHERE id = %s FOR UPDATE",
            (checkout_id,),
        ).fetchone()
        if checkout is None or checkout["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        if checkout["status"] == "pending_payment":
            order = db.execute(
                "SELECT * FROM purchase_purchases WHERE checkout_id = %s",
                (checkout_id,),
            ).fetchone()
            return _purchase_from_row(order)
        if checkout["status"] != "pending_confirmation" or checkout["expires_at"] <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="La confirmación del pedido venció.")

        code_row = db.execute(
            "SELECT * FROM purchase_checkout_codes WHERE checkout_id = %s FOR UPDATE",
            (checkout_id,),
        ).fetchone()
        if code_row is None or code_row["attempts"] >= 5:
            invalid_code = True
        elif not secrets.compare_digest(code_row["code_hash"], hash_one_time_code(payload.code)):
            db.execute(
                "UPDATE purchase_checkout_codes SET attempts = attempts + 1 WHERE checkout_id = %s",
                (checkout_id,),
            )
            invalid_code = True
        else:
            db.execute("DELETE FROM purchase_checkout_codes WHERE checkout_id = %s", (checkout_id,))
            db.execute(
                """
                INSERT INTO purchase_purchases (user_id, items, total, status, created_at, checkout_id)
                VALUES (%s, %s, %s, 'pending_payment', %s, %s)
                """,
                (
                    user["id"], checkout["items"], checkout["total"],
                    datetime.now(timezone.utc), checkout_id,
                ),
            )
            order = db.execute(
                "SELECT * FROM purchase_purchases WHERE checkout_id = %s",
                (checkout_id,),
            ).fetchone()
            db.execute(
                "UPDATE purchase_checkouts SET status = 'pending_payment', confirmed_at = CURRENT_TIMESTAMP WHERE id = %s",
                (checkout_id,),
            )
    if invalid_code:
        raise HTTPException(status_code=400, detail="El código no es válido o ha vencido.")
    return _purchase_from_row(order)


@router.get("/purchases")
def list_purchases(
    user_id: int | None = None,
    user: dict = Depends(current_user),
) -> dict[str, list[Purchase]]:
    if user_id is not None and user_id != user["id"]:
        raise HTTPException(status_code=403, detail="You are not allowed to access these orders.")
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM purchase_purchases WHERE user_id = %s ORDER BY id",
            (user["id"],),
        ).fetchall()
    return {"items": [_purchase_from_row(row) for row in rows]}


@router.get("/purchases/{purchase_id}", response_model=Purchase)
def get_purchase(purchase_id: int, user: dict = Depends(current_user)) -> Purchase:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM purchase_purchases WHERE id = %s AND user_id = %s",
            (purchase_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    return _purchase_from_row(row)
