"""
app/schemas/user.py
────────────────────
Pydantic v2 schemas for user-related request / response payloads.

Schema hierarchy:
  UserBase          → shared fields (email, full_name)
  ├── UserCreate    → registration request (adds password, optional role)
  ├── UserUpdate    → partial update (all optional)
  └── UserResponse  → API response (no password, adds id/role/timestamps)

TokenResponse       → login response (access_token + embedded user info)
BusinessProfileCreate / BusinessProfileResponse → profile CRUD schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Shared base
# ─────────────────────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    """Fields common to multiple user schemas."""

    email: EmailStr = Field(
        ...,
        examples=["alice@example.com"],
        description="Unique email address used for login",
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        examples=["Alice Johnson"],
        description="Display name (2–200 characters)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Registration request
# ─────────────────────────────────────────────────────────────────────────────
class UserCreate(UserBase):
    """
    Request body for POST /auth/register.

    Password rules (enforced by validator):
      - Minimum 8 characters
      - At least one uppercase letter
      - At least one digit
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["SecurePass1"],
        description="Min 8 chars, at least one uppercase and one digit",
    )
    role: str = Field(
        default="analyst",
        examples=["analyst"],
        description="User role: admin | manager | analyst (default: analyst)",
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Enforce minimum password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Ensure role is one of the allowed values."""
        allowed = {"admin", "manager", "analyst"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Update request (all fields optional for PATCH semantics)
# ─────────────────────────────────────────────────────────────────────────────
class UserUpdate(BaseModel):
    """Request body for PATCH /users/{user_id} (admin only)."""

    full_name: str | None = Field(None, min_length=2, max_length=200)
    is_active: bool | None = None
    role: str | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"admin", "manager", "analyst"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# API Response — user info returned to callers (NO password / hash)
# ─────────────────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    """
    Safe user representation returned by the API.
    hashed_password is NEVER included.
    """

    model_config = ConfigDict(from_attributes=True)  # allows ORM → schema conversion

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Login / Token schemas
# ─────────────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    """
    Response body for POST /auth/login.

    Returns the access token alongside embedded user info so the frontend
    can display the user's name and role immediately without a second /me request.
    """

    access_token: str = Field(..., description="JWT Bearer token")
    token_type: str = Field(default="bearer", description="Always 'bearer'")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    user: UserResponse = Field(..., description="Authenticated user details")


class TokenData(BaseModel):
    """Internal schema for parsed JWT claims (used in deps.py)."""

    sub: str
    email: str
    role: str


# ─────────────────────────────────────────────────────────────────────────────
# Business Profile schemas (Re-exported from profile module for convenience)
# ─────────────────────────────────────────────────────────────────────────────
from app.schemas.profile import BusinessProfileCreate, BusinessProfileResponse  # noqa: F401


# ─────────────────────────────────────────────────────────────────────────────
# Standard API envelope helpers
# ─────────────────────────────────────────────────────────────────────────────
class SuccessResponse(BaseModel):
    """Generic success envelope."""

    success: bool = True
    message: str


class UserWithProfileResponse(UserResponse):
    """Extended user response that includes the business profile if present."""

    business_profile: BusinessProfileResponse | None = None
