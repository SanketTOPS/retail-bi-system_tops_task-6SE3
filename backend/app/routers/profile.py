"""
app/routers/profile.py
───────────────────────
Router for Business Profile CRUD operations.

Routes:
  POST /api/v1/profile      — Create business profile for current user (1 profile per user)
  GET  /api/v1/profile      — Fetch current user's business profile
  PUT  /api/v1/profile      — Update current user's business profile
  GET  /api/v1/profile/all  — List all business profiles (Admin only)
"""

from __future__ import annotations

import logging
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import AppException
from app.models.user import User
from app.schemas.profile import (
    BusinessProfileCreate,
    BusinessProfileResponse,
    BusinessProfileUpdate,
)
from app.services import profile_service
from app.utils.deps import get_current_active_user, require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Business Profile"])


@router.post(
    "",
    response_model=BusinessProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create business profile",
    description="Creates a new business profile for the authenticated user. Only one profile allowed per user.",
    responses={
        201: {"description": "Profile created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "User already has a business profile"},
    },
)
def create_my_profile(
    payload: BusinessProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BusinessProfileResponse:
    """Create a profile for the currently authenticated user."""
    existing = profile_service.get_profile_by_user_id(db, current_user.id)
    if existing:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Business profile already exists for this account. Use PUT /profile to update.",
            code="PROFILE_ALREADY_EXISTS",
        )

    profile = profile_service.create_profile(db, user_id=current_user.id, payload=payload)
    return BusinessProfileResponse.model_validate(profile)


@router.get(
    "",
    response_model=BusinessProfileResponse,
    summary="Get current user's business profile",
    description="Retrieves the business profile associated with the currently authenticated user.",
    responses={
        200: {"description": "Business profile details"},
        404: {"description": "Profile not found"},
    },
)
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BusinessProfileResponse:
    """Fetch the authenticated user's business profile."""
    profile = profile_service.get_profile_by_user_id(db, current_user.id)
    if not profile:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business profile found for this account. Create one via POST /profile.",
            code="PROFILE_NOT_FOUND",
        )
    return BusinessProfileResponse.model_validate(profile)


@router.put(
    "",
    response_model=BusinessProfileResponse,
    summary="Update business profile",
    description="Updates the existing business profile of the authenticated user.",
    responses={
        200: {"description": "Profile updated successfully"},
        404: {"description": "Profile not found"},
    },
)
def update_my_profile(
    payload: BusinessProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BusinessProfileResponse:
    """Update fields of current user's profile."""
    profile = profile_service.get_profile_by_user_id(db, current_user.id)
    if not profile:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business profile found to update. Create one via POST /profile first.",
            code="PROFILE_NOT_FOUND",
        )

    updated_profile = profile_service.update_profile(db, profile=profile, payload=payload)
    return BusinessProfileResponse.model_validate(updated_profile)


@router.get(
    "/all",
    response_model=list[BusinessProfileResponse],
    summary="List all business profiles (Admin only)",
    description="Returns a paginated list of all business profiles across the platform. Accessible only by admins.",
    responses={
        200: {"description": "List of business profiles"},
        403: {"description": "Forbidden: Requires admin role"},
    },
)
def list_all_profiles(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Sequence[BusinessProfileResponse]:
    """Admin-only endpoint to view all registered company profiles."""
    profiles = profile_service.get_all_profiles(db, skip=skip, limit=limit)
    return [BusinessProfileResponse.model_validate(p) for p in profiles]
