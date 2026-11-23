from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class EmailInput(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PhoneInput(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")


class CodeInput(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class ResetPasswordInput(CodeInput):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class User(BaseModel):
    id: int
    username: str
    email: str | None = None
    phone: str | None = None
    email_verified: bool = False
    phone_verified: bool = False
    role: str
    permissions: list[str]
    active: bool = True


class AuthResponse(BaseModel):
    ok: bool = True
    user: User
