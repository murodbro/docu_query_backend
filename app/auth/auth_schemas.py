from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (no password)."""

    id: str
    email: str
    name: str
    email_verified: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token data."""

    user_id: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    name: str = Field(..., min_length=1)


class PasswordChange(BaseModel):
    """Schema for changing password."""

    current_password: str
    new_password: str = Field(..., min_length=6)


class EmailVerification(BaseModel):
    """Schema for email verification."""

    token: str


class ResendVerification(BaseModel):
    """Schema for resending verification email."""

    email: EmailStr


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
