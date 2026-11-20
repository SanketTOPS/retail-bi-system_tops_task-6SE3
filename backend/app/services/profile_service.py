"""
app/services/profile_service.py
────────────────────────────────
Service layer for Business Profile operations.
Separates database access and business logic from the HTTP router.
"""

from __future__ import annotations

import logging
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business_profile import BusinessProfile
from app.schemas.profile import BusinessProfileCreate, BusinessProfileUpdate

logger = logging.getLogger(__name__)


def get_profile_by_user_id(db: Session, user_id: uuid.UUID) -> BusinessProfile | None:
    """Retrieve the business profile belonging to a specific user."""
    stmt = select(BusinessProfile).where(BusinessProfile.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_profile_by_id(db: Session, profile_id: uuid.UUID) -> BusinessProfile | None:
    """Retrieve a business profile by its primary key ID."""
    stmt = select(BusinessProfile).where(BusinessProfile.id == profile_id)
    return db.execute(stmt).scalar_one_or_none()


def get_all_profiles(db: Session, skip: int = 0, limit: int = 100) -> Sequence[BusinessProfile]:
    """Retrieve all business profiles with pagination (Admin only)."""
    stmt = (
        select(BusinessProfile)
        .order_by(BusinessProfile.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def create_profile(
    db: Session,
    user_id: uuid.UUID,
    payload: BusinessProfileCreate,
) -> BusinessProfile:
    """
    Create a new business profile linked to the specified user.
    Assumes caller has already verified that the user does not have an existing profile.
    """
    profile_data = payload.model_dump()
    profile = BusinessProfile(
        user_id=user_id,
        **profile_data,
    )
    db.add(profile)
    db.flush()
    logger.info("Created business profile %s for user %s (%s)", profile.id, user_id, profile.company_name)
    return profile


def update_profile(
    db: Session,
    profile: BusinessProfile,
    payload: BusinessProfileUpdate,
) -> BusinessProfile:
    """
    Apply partial or full updates to an existing business profile.
    Excludes fields that were not provided in the payload.
    """
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.flush()
    logger.info("Updated business profile %s (%s)", profile.id, profile.company_name)
    return profile


def delete_profile(db: Session, profile: BusinessProfile) -> None:
    """Delete a business profile."""
    profile_id = profile.id
    db.delete(profile)
    db.flush()
    logger.info("Deleted business profile %s", profile_id)
