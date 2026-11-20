"""
app/utils/deps.py
──────────────────
FastAPI reusable dependencies for authentication and role-based access control.

Three exported callables used as Depends():
  - get_current_user       → validates JWT, returns live User ORM object
  - get_current_active_user → additionally enforces is_active == True
  - require_roles(*roles)  → factory that returns a role-checking dependency

Usage in a router:
    # Any authenticated user
    @router.get("/me")
    def me(user: User = Depends(get_current_active_user)):
        ...

    # Manager or Admin only
    @router.post("/approve")
    def approve(user: User = Depends(require_roles("manager", "admin"))):
        ...
"""

from __future__ import annotations

import logging
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import InvalidTokenError, TokenPayload, decode_access_token
from app.models.user import User

logger = logging.getLogger(__name__)

# ── OAuth2 Scheme ─────────────────────────────────────────────────────────────
# tokenUrl tells Swagger UI where to POST credentials to get the bearer token.
# This is the URL that the "Authorize" button in /docs calls.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Token → Payload ───────────────────────────────────────────────────────────
def _get_token_payload(token: str = Depends(oauth2_scheme)) -> TokenPayload:
    """
    Internal dependency: extracts and validates the JWT from the Authorization header.

    Returns:
        :class:`~app.core.security.TokenPayload` with typed fields.

    Raises:
        HTTP 401 if the token is missing, malformed, expired, or has an invalid signature.
    """
    try:
        return decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.reason,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── Payload → Live User ───────────────────────────────────────────────────────
def get_current_user(
    payload: TokenPayload = Depends(_get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the JWT ``sub`` claim to a live SQLAlchemy :class:`User` row.

    Why not just trust the JWT payload?
      The token is valid for up to ACCESS_TOKEN_EXPIRE_MINUTES. During that
      window a user could be deactivated or deleted. Hitting the DB on every
      request guarantees we always reflect the current state.

    Returns:
        The authenticated :class:`User` ORM object.

    Raises:
        HTTP 401 if the user UUID from the token does not exist in the DB.
    """
    try:
        user_uuid = uuid.UUID(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid UUID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found — token may be stale",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ── Active User Guard ─────────────────────────────────────────────────────────
def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Extends :func:`get_current_user` with an ``is_active`` check.

    Use this (not get_current_user) on every protected endpoint so that
    deactivating a user immediately locks them out without token revocation.

    Raises:
        HTTP 403 if the user account is marked inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact an administrator.",
        )
    return current_user


# ── Role Guard Factory ────────────────────────────────────────────────────────
def require_roles(*roles: str):
    """
    Dependency factory that enforces role-based access control.

    Returns a FastAPI dependency function that:
      1. Calls :func:`get_current_active_user` (validates token + is_active).
      2. Checks that the user's role is in the allowed ``roles`` set.
      3. Raises HTTP 403 with a descriptive message if the check fails.

    Args:
        *roles: One or more allowed role strings, e.g. "admin", "manager".

    Example::

        # Only admins can delete users
        @router.delete("/users/{user_id}")
        def delete_user(
            user_id: uuid.UUID,
            current_user: User = Depends(require_roles("admin")),
        ):
            ...

        # Both managers and admins can approve recommendations
        @router.post("/approvals/{rec_id}/decision")
        def decide(
            rec_id: uuid.UUID,
            current_user: User = Depends(require_roles("manager", "admin")),
        ):
            ...
    """
    allowed: frozenset[str] = frozenset(roles)

    def _role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {sorted(allowed)}. "
                    f"Your role: '{current_user.role}'."
                ),
            )
        return current_user

    # Give the inner function a unique name so FastAPI's dependency cache
    # treats different require_roles(...) calls as separate dependencies.
    _role_checker.__name__ = f"require_roles_{'_'.join(sorted(allowed))}"
    return _role_checker


# ── Convenience pre-built role dependencies ───────────────────────────────────
# Import and use these directly in routers for the most common patterns.

require_admin = require_roles("admin")
"""Allow only admin users."""

require_manager_or_admin = require_roles("manager", "admin")
"""Allow managers and admins (e.g. approval endpoints)."""

require_analyst_or_above = require_roles("analyst", "manager", "admin")
"""Allow any authenticated active user (all roles)."""
