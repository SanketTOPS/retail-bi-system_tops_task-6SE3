"""
app/routers/auth.py
────────────────────
Authentication endpoints.

Routes:
  POST /api/v1/auth/register  — create a new user account
  POST /api/v1/auth/login     — exchange credentials for a JWT
                                (OAuth2PasswordRequestForm → Swagger Authorize works)
  GET  /api/v1/auth/me        — return the authenticated user's profile
  POST /api/v1/auth/profile   — create / update business profile for current user
  GET  /api/v1/auth/profile   — read current user's business profile

Design rules followed:
  - Routers are THIN: validation + call service + return response.
  - All business logic lives in app/services/auth_service.py.
  - AppException (from main.py) is used for all intentional errors so the
    global handler always returns the consistent JSON envelope.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import AppException
from app.models.business_profile import BusinessProfile
from app.schemas.user import (
    BusinessProfileCreate,
    BusinessProfileResponse,
    SuccessResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserWithProfileResponse,
)
from app.services.auth_service import (
    authenticate_user,
    get_user_by_email,
    register_user,
)
from app.utils.deps import get_current_active_user, require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/register
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "Email already registered"},
        422: {"description": "Validation error (password too weak, invalid email, etc.)"},
    },
)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account.

    **Business rules:**
    - Email must be unique across the system.
    - Password: min 8 chars, ≥1 uppercase, ≥1 digit.
    - Role defaults to `analyst`. Requesting a different role is accepted but
      overridden silently if you are the first user (auto-promoted to admin).
    - **First registered user** is always granted `admin` regardless of
      the requested role — ensures there is always at least one admin.
    """
    # 1. Check email uniqueness
    if get_user_by_email(db, payload.email):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{payload.email}' is already registered. Please log in.",
            code="EMAIL_ALREADY_EXISTS",
        )

    # 2. Delegate creation to service (pure Python, no HTTP awareness)
    user = register_user(db, payload)
    return UserResponse.model_validate(user)


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/login   — OAuth2 form (Swagger Authorize button compatible)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain a JWT access token",
    responses={
        200: {"description": "Login successful — returns JWT"},
        401: {"description": "Incorrect email or password"},
        403: {"description": "Account is deactivated"},
    },
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email + password and receive a JWT Bearer token.

    **Swagger Authorize**: Click the 🔒 button in /docs, enter your
    email as *username* and your password, then click Authorize.
    All subsequent requests in Swagger will include the Bearer header automatically.

    Uses `OAuth2PasswordRequestForm` which reads `username` and `password`
    from `application/x-www-form-urlencoded` body (OAuth2 spec).
    We treat `username` as the email field.
    """
    # 1. Verify credentials (timing-safe — service runs bcrypt even on miss)
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if user is None:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            code="INVALID_CREDENTIALS",
        )

    # 2. Check account is active
    if not user.is_active:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact an administrator.",
            code="ACCOUNT_DEACTIVATED",
        )

    # 3. Issue JWT
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role,
        expires_delta=expires,
    )

    logger.info(f"Successful login: user={user.id} role={user.role}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=int(expires.total_seconds()),
        user=UserResponse.model_validate(user),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /auth/me
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserWithProfileResponse,
    summary="Get current authenticated user",
    responses={
        200: {"description": "Current user details"},
        401: {"description": "Not authenticated"},
    },
)
def get_me(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserWithProfileResponse:
    """
    Return the profile of the currently authenticated user.

    Includes the business profile if one has been created.
    Use this after login to populate the frontend's user context/store.
    """
    # Eager-load the business profile within the same session
    profile = (
        db.query(BusinessProfile)
        .filter(BusinessProfile.user_id == current_user.id)
        .first()
    )

    response = UserWithProfileResponse.model_validate(current_user)
    if profile:
        response = response.model_copy(
            update={"business_profile": BusinessProfileResponse.model_validate(profile)}
        )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# GET /auth/users  — admin only: list all users
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
    dependencies=[Depends(require_roles("admin"))],
)
def list_users(db: Session = Depends(get_db)) -> list[UserResponse]:
    """
    Return all registered users.
    Restricted to admin role.
    """
    from app.models.user import User as UserModel
    users = db.query(UserModel).order_by(UserModel.created_at.desc()).all()
    return [UserResponse.model_validate(u) for u in users]
