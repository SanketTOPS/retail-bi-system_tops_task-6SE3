"""
app/core/database.py
─────────────────────
SQLAlchemy async-compatible synchronous engine setup.
Provides:
  - engine        : SQLAlchemy Engine connected to PostgreSQL
  - SessionLocal  : Session factory (used in get_db)
  - Base          : Declarative base shared by ALL ORM models
  - get_db        : FastAPI dependency that yields a DB session and
                    guarantees commit-on-success / rollback-on-error.
"""

from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
_raw_db_url = settings.DATABASE_URL
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif _raw_db_url.startswith("postgresql://") and not _raw_db_url.startswith("postgresql+"):
    _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    _raw_db_url,
    pool_pre_ping=True,          # test connections before use (handles DB restarts)
    pool_size=10,                # number of persistent connections in pool
    max_overflow=20,             # extra connections allowed beyond pool_size
    pool_recycle=1800,           # recycle connections after 30 min (avoids stale conn)
    echo=(settings.APP_ENV == "development"),  # log SQL only in dev
)


# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,      # keep attributes accessible after commit
)


# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Shared base for all ORM models.
    All models must import and subclass this Base so that
    Base.metadata.create_all() creates every table in one call.
    """
    pass


# ── FastAPI Dependency ────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy Session for use inside a FastAPI route.

    Usage:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...

    Guarantees:
        - Session is always closed (via finally).
        - On unhandled exception the transaction is rolled back,
          preventing partial writes.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Utility ───────────────────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """
    Verify that the database is reachable.
    Called from /health endpoint and application startup.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
