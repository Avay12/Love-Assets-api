import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Enforced identically on the client (see the frontend's password rules) so the
# two never disagree about what is acceptable.
PASSWORD_MIN = 8


def validate_password(v: str) -> str:
    if len(v) < PASSWORD_MIN:
        raise ValueError(f"Password must be at least {PASSWORD_MIN} characters")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("Password must contain a letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain a number")
    return v


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: EmailStr
    password: str = Field(..., max_length=256)

    _check = field_validator("password")(validate_password)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., max_length=256)

    _check = field_validator("password")(validate_password)


class VerifyEmailRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    email_verified: bool = False
    has_password: bool = False
    providers: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    """The access token is returned for non-browser clients; browsers get it
    in an HTTP-only cookie and can ignore this field."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int
