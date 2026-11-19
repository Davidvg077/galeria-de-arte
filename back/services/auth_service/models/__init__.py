from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(default="VISITANTE", pattern="^(VISITANTE|ARTISTA)$")


class EmailInput(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CodeInput(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class ResetPasswordInput(CodeInput):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class User(BaseModel):
    id: int
    username: str
    email: str | None = None
    email_verified: bool = False
    role: str
    permissions: list[str]
    active: bool = True


class AuthResponse(BaseModel):
    ok: bool = True
    user: User
