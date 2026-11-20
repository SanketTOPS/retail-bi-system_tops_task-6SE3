"""
app/services/auth_service.py
─────────────────────────────
Business logic for authentication and user management.

Routers call these functions — zero FastAPI imports here (pure Python).
This keeps the service testable without spinning up an ASGI server.

Functions:
  - get_user_by_email     : DB lookup by email
  - register_user         : validate uniqueness, hash pw, persist
  - authenticate_user     : verify credentials, return User or None
  - is_first_user         : True if the users table is empty (first user → admin)
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


# ── Read helpers ──────────────────────────────────────────────────────────────
def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Look up a User by email address (case-insensitive).

    Args:
        db:    Active SQLAlchemy session.
        email: Email to look up.

    Returns:
        :class:`User` if found, else None.
    """
    return (
        db.query(User)
        .filter(User.email == email.lower().strip())
        .first()
    )


def is_first_user(db: Session) -> bool:
    """
    Return True if no users exist yet.
    Used to automatically grant admin role to the very first registered user.
    """
    return db.query(User).count() == 0


# ── Write helpers ─────────────────────────────────────────────────────────────
def register_user(db: Session, payload: UserCreate) -> User:
    """
    Create and persist a new User.

    Business rules:
      - Email is normalised to lowercase before storage and uniqueness check.
      - The first user ever created is automatically granted the ``admin`` role
        regardless of the requested role — a safety net for initial setup.
      - Password is hashed with bcrypt before storage.

    Args:
        db:      Active SQLAlchemy session.
        payload: Validated :class:`UserCreate` schema.

    Returns:
        The newly created :class:`User` ORM object (already flushed, not committed
        — the router's ``get_db`` dependency commits on success).

    Raises:
        :class:`~app.main.AppException` 409 if the email is already registered.
        (Raised in the router to keep this service free of HTTP concerns.)
    """
    normalised_email = payload.email.lower().strip()

    # First-user override: initial admin can't be locked out by role validation
    effective_role = payload.role
    if is_first_user(db):
        effective_role = "admin"
        logger.info(f"First user registration — granting admin role to {normalised_email}")

    user = User(
        email=normalised_email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=effective_role,
        is_active=True,
    )
    db.add(user)
    db.flush()   # gets the UUID assigned without committing the transaction
    logger.info(f"Registered user {user.id} email={normalised_email} role={effective_role}")
    return user


# ── Authentication ────────────────────────────────────────────────────────────
def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Verify email/password credentials.

    Args:
        db:       Active SQLAlchemy session.
        email:    Submitted email.
        password: Plain-text password from the login form.

    Returns:
        :class:`User` on success; None if credentials are wrong or user not found.
        Returning None (rather than raising) lets the router decide the HTTP status.
    """
    user = get_user_by_email(db, email)
    if user is None:
        # Run verify_password anyway to avoid timing-based email enumeration
        verify_password(password, "$2b$12$placeholder_hash_to_prevent_timing")
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning(f"Failed login attempt for email={email}")
        return None

    return user
