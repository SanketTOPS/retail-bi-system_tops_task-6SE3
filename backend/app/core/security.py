"""
app/core/security.py
─────────────────────
Cryptographic helpers for the auth layer.

Responsibilities:
  1. Password hashing   — bcrypt via passlib (never store plain text)
  2. JWT creation       — signed with SECRET_KEY / ALGORITHM from settings
  3. JWT decoding       — verify signature + expiry + token type claim
  4. Token payload type — typed dataclass avoids dict key typos downstream

This module has ZERO FastAPI / SQLAlchemy imports — it is pure crypto logic,
easily unit-tested in isolation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Password Hashing ──────────────────────────────────────────────────────────
# CryptContext manages algorithm upgrades gracefully (deprecated= "auto"
# rehashes old bcrypt rounds if the work factor is raised in future).
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Return a bcrypt hash of *plain_password*.

    Args:
        plain_password: The raw password string from the registration form.

    Returns:
        A bcrypt hash string (60 chars) safe to store in the DB.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time comparison of *plain_password* against *hashed_password*.

    Returns:
        True if the password matches; False otherwise.
        Never raises — returns False on any internal error.
    """
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# ── JWT Token Payload ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class TokenPayload:
    """
    Typed representation of a decoded JWT payload.

    Attributes:
        sub:   Subject — the user's UUID as a string.
        email: User email (embedded to avoid a DB lookup on every request).
        role:  User role string (admin | manager | analyst).
        exp:   Expiry as a UTC datetime.
        iat:   Issued-at as a UTC datetime.
    """

    sub: str
    email: str
    role: str
    exp: datetime
    iat: datetime


# ── JWT Creation ──────────────────────────────────────────────────────────────
def create_access_token(
    subject: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create and sign a JWT access token.

    The token payload contains:
      - ``sub``   : user UUID (string) — the standard JWT subject claim
      - ``email`` : user email embedded for fast /me lookups
      - ``role``  : RBAC role for the ``require_roles`` dependency
      - ``type``  : literal "access" — prevents refresh tokens being used as access tokens
      - ``exp``   : expiry (UTC)
      - ``iat``   : issued-at (UTC)

    Args:
        subject:      User UUID as a string.
        email:        User email address.
        role:         User role (admin | manager | analyst).
        expires_delta: Override the default expiry from settings.

    Returns:
        A signed JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(tz=timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,          # user UUID
        "email": email,
        "role": role,
        "type": "access",        # guard against refresh-token reuse
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"JWT created for sub={subject} role={role} exp={expire.isoformat()}")
    return token


# ── JWT Decoding ──────────────────────────────────────────────────────────────
class InvalidTokenError(Exception):
    """Raised by decode_access_token when verification fails for any reason."""

    def __init__(self, reason: str = "Invalid or expired token") -> None:
        self.reason = reason
        super().__init__(reason)


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode, verify signature, and validate a JWT access token.

    Validation steps performed by python-jose:
      1. Signature verification (HS256 with SECRET_KEY).
      2. Expiry check (raises JWTError if ``exp`` is in the past).
      3. We additionally check ``type == "access"`` to reject refresh tokens.

    Args:
        token: Raw JWT string from the Authorization header.

    Returns:
        A :class:`TokenPayload` with typed fields.

    Raises:
        :class:`InvalidTokenError` with a human-readable reason on any failure.
    """
    try:
        raw: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as exc:
        # JWTError covers: bad signature, expired, malformed header/payload
        raise InvalidTokenError(f"JWT decode failed: {exc}") from exc

    # Extra guard: reject tokens of the wrong type
    if raw.get("type") != "access":
        raise InvalidTokenError("Token type is not 'access'")

    # Mandatory claims
    sub = raw.get("sub")
    email = raw.get("email")
    role = raw.get("role")

    if not sub or not email or not role:
        raise InvalidTokenError("Token is missing required claims (sub/email/role)")

    return TokenPayload(
        sub=sub,
        email=email,
        role=role,
        exp=datetime.fromtimestamp(raw["exp"], tz=timezone.utc),
        iat=datetime.fromtimestamp(raw["iat"], tz=timezone.utc),
    )
