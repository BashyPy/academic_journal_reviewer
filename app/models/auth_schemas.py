"""Authentication schemas"""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# Password validation constants
PASSWORD_REGEX_LOWERCASE = r"[a-z]"
PASSWORD_REGEX_UPPERCASE = r"[A-Z]"
PASSWORD_REGEX_DIGIT = r"\d"
PASSWORD_REGEX_SPECIAL = r"[^a-zA-Z0-9]"
PASSWORD_ERROR_LOWERCASE = "Password must contain at least one lowercase letter"
PASSWORD_ERROR_UPPERCASE = "Password must contain at least one uppercase letter"
PASSWORD_ERROR_DIGIT = "Password must contain at least one digit"
PASSWORD_ERROR_SPECIAL = "Password must contain at least one special character"
OTP_ERROR_DIGITS = "OTP must contain only digits"


class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    username: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not re.search(PASSWORD_REGEX_LOWERCASE, v):
            raise ValueError(PASSWORD_ERROR_LOWERCASE)
        if not re.search(PASSWORD_REGEX_UPPERCASE, v):
            raise ValueError(PASSWORD_ERROR_UPPERCASE)
        if not re.search(PASSWORD_REGEX_DIGIT, v):
            raise ValueError(PASSWORD_ERROR_DIGIT)
        if not re.search(PASSWORD_REGEX_SPECIAL, v):
            raise ValueError(PASSWORD_ERROR_SPECIAL)
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not re.match(r"^\w+$", v):
            raise ValueError("Username can only contain alphanumeric characters and underscores")
        return v


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v):
        if not v.isdigit():
            raise ValueError(OTP_ERROR_DIGITS)
        return v


class LoginRequest(BaseModel):
    email_or_username: str
    password: str
    api_key: Optional[str] = None
    user: Optional[dict] = None


class PasskeyRegistrationRequest(BaseModel):
    credential: dict


class PasskeyAuthenticationRequest(BaseModel):
    credential: dict


class AuthResponse(BaseModel):
    """Response model for authentication endpoints."""

    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    user: Optional[dict] = None


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request model for password reset."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if not re.search(PASSWORD_REGEX_LOWERCASE, v):
            raise ValueError(PASSWORD_ERROR_LOWERCASE)
        if not re.search(PASSWORD_REGEX_UPPERCASE, v):
            raise ValueError(PASSWORD_ERROR_UPPERCASE)
        if not re.search(PASSWORD_REGEX_DIGIT, v):
            raise ValueError(PASSWORD_ERROR_DIGIT)
        if not re.search(PASSWORD_REGEX_SPECIAL, v):
            raise ValueError(PASSWORD_ERROR_SPECIAL)
        return v


class UpdatePasswordRequest(BaseModel):
    """Request model for updating password."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if not re.search(PASSWORD_REGEX_LOWERCASE, v):
            raise ValueError(PASSWORD_ERROR_LOWERCASE)
        if not re.search(PASSWORD_REGEX_UPPERCASE, v):
            raise ValueError(PASSWORD_ERROR_UPPERCASE)
        if not re.search(PASSWORD_REGEX_DIGIT, v):
            raise ValueError(PASSWORD_ERROR_DIGIT)
        if not re.search(PASSWORD_REGEX_SPECIAL, v):
            raise ValueError(PASSWORD_ERROR_SPECIAL)
        return v
