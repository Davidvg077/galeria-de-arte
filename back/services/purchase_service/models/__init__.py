from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartItem(BaseModel):
    work_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=20)


class CheckoutItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=20)


class Cart(BaseModel):
    user_id: int
    items: list[CartItem] = Field(default_factory=list)


class CheckoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CheckoutItem] = Field(min_length=1, max_length=50)


class ConfirmInput(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class Purchase(BaseModel):
    id: int
    user_id: int
    items: list[dict]
    total: float
    status: str
    created_at: datetime


class Checkout(BaseModel):
    id: str
    total: float
    status: str
    expires_at: datetime
    demo_mode: bool = True
    demo_code: str | None = None
