"""
scripts/seed_users.py
──────────────────────
Database seeder — creates default users for local development and testing.

Run from the backend/ directory:
    py scripts/seed_users.py

Creates (skips if email already exists):
  - admin@retailbi.local   / Admin@123   role: admin
  - manager@retailbi.local / Manager@123 role: manager
  - analyst@retailbi.local / Analyst@123 role: analyst

IMPORTANT: Change these passwords immediately in a production environment.
Never use this script against a production database.
"""

from __future__ import annotations

import sys
import os

# Add the backend/ directory to sys.path so we can import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

# Load .env before importing settings (settings reads from .env on first import)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from app.core.config import settings  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402

# Ensure all models are registered with Base before create_all
import app.models  # noqa: F401, E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("seed")


# ── Seed data definition ──────────────────────────────────────────────────────
@dataclass
class SeedUser:
    email: str
    full_name: str
    password: str
    role: str


SEED_USERS: list[SeedUser] = [
    SeedUser(
        email="admin@retailbi.com",
        full_name="System Administrator",
        password="Admin@123",
        role="admin",
    ),
    SeedUser(
        email="manager@retailbi.com",
        full_name="Business Manager",
        password="Manager@123",
        role="manager",
    ),
    SeedUser(
        email="analyst@retailbi.com",
        full_name="Data Analyst",
        password="Analyst@123",
        role="analyst",
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _user_exists(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == email.lower()).count() > 0


def _create_user(db: Session, seed: SeedUser) -> User:
    user = User(
        email=seed.email.lower(),
        full_name=seed.full_name,
        hashed_password=hash_password(seed.password),
        role=seed.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


# ── Main ──────────────────────────────────────────────────────────────────────
def run_seed() -> None:
    """Create DB tables and insert seed users."""
    logger.info("=" * 60)
    logger.info("Retail BI — Database Seeder")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1]}")  # hide credentials
    logger.info("=" * 60)

    # Ensure tables exist (safe to call even if they already exist)
    logger.info("Creating database tables (if not exist)…")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables ready.")

    created_count = 0
    skipped_count = 0

    with SessionLocal() as db:
        for seed in SEED_USERS:
            if _user_exists(db, seed.email):
                logger.info(f"  SKIP   {seed.email:<35} (already exists)")
                skipped_count += 1
            else:
                user = _create_user(db, seed)
                logger.info(
                    f"  CREATE {seed.email:<35} role={seed.role:<10} id={user.id}"
                )
                created_count += 1

        db.commit()

    logger.info("=" * 60)
    logger.info(f"Seed complete — Created: {created_count} | Skipped: {skipped_count}")
    logger.info("=" * 60)
    logger.info("\nDefault credentials (CHANGE IN PRODUCTION):")
    logger.info("  Admin   : admin@retailbi.local    / Admin@123")
    logger.info("  Manager : manager@retailbi.local  / Manager@123")
    logger.info("  Analyst : analyst@retailbi.local  / Analyst@123")
    logger.info("\nSwagger UI: http://localhost:8000/docs")


if __name__ == "__main__":
    run_seed()
