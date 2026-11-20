"""
app/main.py
────────────
FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app with Swagger / ReDoc metadata
  - Configure CORS middleware
  - Register all routers (stubs for now — filled in later modules)
  - Attach global exception handlers (validation, custom AppException, generic 500)
  - Provide /health endpoint
  - Run create_all() on startup (dev convenience; production uses Alembic)
"""

import logging
import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, check_db_connection, engine

# ── Import all models so Base.metadata knows about every table ────────────────
import app.models  # noqa: F401  (registers all ORM models with Base)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("retail_bi")


# ─────────────────────────────────────────────────────────────────────────────
# Custom Application Exception
# ─────────────────────────────────────────────────────────────────────────────
class AppException(Exception):
    """
    Raise this anywhere in the codebase for predictable, structured errors.

    Usage:
        raise AppException(status_code=404, detail="Dataset not found", code="DATASET_NOT_FOUND")
    """

    def __init__(
        self,
        status_code: int = 400,
        detail: str = "An error occurred",
        code: str = "APP_ERROR",
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Runs once at startup before first request and once at shutdown.

    Startup:
      1. Create all DB tables (dev convenience — use Alembic for prod).
      2. Verify DB connectivity and log the result.
      3. Create the upload directory if it does not exist.

    Shutdown:
      - Dispose the connection pool gracefully.
    """
    import os

    # 1. Create tables with retry loop
    import time
    logger.info("Connecting to database and creating tables (if not exist)…")
    db_initialized = False
    for attempt in range(1, 6):
        try:
            Base.metadata.create_all(bind=engine)
            db_initialized = True
            logger.info("Database tables ready.")
            break
        except Exception as e:
            logger.warning("Database connection attempt %d/5 failed: %s. Retrying in 3s...", attempt, e)
            time.sleep(3)

    # 1b. Auto-seed default users if database is empty
    if db_initialized:
        try:
            from app.models.user import User
            from app.core.security import hash_password
            with SessionLocal() as db:
                if db.query(User).count() == 0:
                    logger.info("Database has no users. Auto-seeding initial users...")
                    initial_users = [
                        User(
                            email="admin@retailbi.com",
                            full_name="System Administrator",
                            hashed_password=hash_password("Admin@123"),
                            role="admin",
                            is_active=True,
                        ),
                        User(
                            email="manager@retailbi.com",
                            full_name="Business Manager",
                            hashed_password=hash_password("Manager@123"),
                            role="manager",
                            is_active=True,
                        ),
                        User(
                            email="analyst@retailbi.com",
                            full_name="Data Analyst",
                            hashed_password=hash_password("Analyst@123"),
                            role="analyst",
                            is_active=True,
                        ),
                    ]
                    db.add_all(initial_users)
                    db.commit()
                    logger.info("Default users seeded (admin@retailbi.com, manager@retailbi.com, analyst@retailbi.com).")
        except Exception as exc:
            logger.warning("Could not auto-seed default users: %s", exc)

    # 2. Health check
    if check_db_connection():
        logger.info("✅ PostgreSQL connection: OK")
    else:
        logger.error("❌ PostgreSQL connection: FAILED — check DATABASE_URL in .env")

    # 3. Upload dir
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory: {settings.UPLOAD_DIR!r}")

    logger.info(f"🚀 Retail BI API v{settings.APP_VERSION} ready | env={settings.APP_ENV}")
    yield

    # Shutdown
    engine.dispose()
    logger.info("Database connection pool disposed.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI-Powered Retail Business Intelligence System",
    description=(
        "Multi-agent AI platform for Retail Sales & Inventory Intelligence.\n\n"
        "**Industry**: Retail — Sales & Inventory\n"
        "**Dataset Period**: May 1, 2026 – Oct 31, 2026\n\n"
        "Powered by CrewAI + Gemini (LiteLLM) + FastAPI + PostgreSQL."
    ),
    version=settings.APP_VERSION,
    contact={
        "name": "Retail BI Team",
        "email": "admin@retailbi.local",
    },
    license_info={"name": "MIT"},
    docs_url="/docs",        # Swagger UI
    redoc_url="/redoc",      # ReDoc
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS Middleware
# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Global Exception Handlers
# ─────────────────────────────────────────────────────────────────────────────
def _error_envelope(
    status_code: int,
    code: str,
    detail: str | list,
) -> JSONResponse:
    """
    Consistent JSON error envelope used by all handlers:
    {
        "success": false,
        "error": {
            "code": "VALIDATION_ERROR",
            "detail": "...",
            "status_code": 422
        }
    }
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "detail": detail,
                "status_code": status_code,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handles Pydantic v2 request body / query param validation failures.
    Returns HTTP 422 with structured field-level error list.
    """
    errors = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    logger.warning(f"Validation error on {request.url}: {errors}")
    return _error_envelope(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        detail=errors,
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handles all intentional AppExceptions raised in services / routers.
    """
    logger.warning(f"AppException [{exc.code}] on {request.url}: {exc.detail}")
    return _error_envelope(
        status_code=exc.status_code,
        code=exc.code,
        detail=exc.detail,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for unhandled exceptions.
    Logs full traceback; returns generic 500 to client (never leaks internals).
    """
    logger.error(
        f"Unhandled exception on {request.method} {request.url}\n"
        + traceback.format_exc()
    )
    return _error_envelope(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        detail="An unexpected error occurred. Please try again later.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routers — add each module's router here as it is built
# ─────────────────────────────────────────────────────────────────────────────
from app.routers import auth as auth_router            # Module 2 ✅
from app.routers import profile as profile_router      # Module 3 ✅
from app.routers import datasets as datasets_router    # Module 4 ✅
from app.routers import analytics as analytics_router  # Module 5 ✅
from app.routers import analysis as analysis_router    # Module 8 ✅
from app.routers import approvals as approvals_router  # Module 9 ✅
from app.routers import chat as chat_router            # Module 10 ✅
from app.routers import reports as reports_router      # Module 11 ✅
from app.routers import admin as admin_router          # Module 12 ✅

app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(profile_router.router, prefix="/api/v1")
app.include_router(datasets_router.router, prefix="/api/v1")
app.include_router(analytics_router.router, prefix="/api/v1")
app.include_router(analysis_router.router, prefix="/api/v1")
app.include_router(approvals_router.router, prefix="/api/v1")
app.include_router(chat_router.router, prefix="/api/v1")
app.include_router(reports_router.router, prefix="/api/v1")
app.include_router(admin_router.router, prefix="/api/v1")

# All routers registered above (Modules 2–11) ✅


# ─────────────────────────────────────────────────────────────────────────────
# Health Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    response_description="System health status",
)
async def health_check() -> dict:
    """
    Returns application health status and DB connectivity.
    Used by load balancers, Docker HEALTHCHECK, and monitoring tools.
    """
    db_ok = check_db_connection()
    return {
        "success": True,
        "data": {
            "status": "healthy" if db_ok else "degraded",
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "database": "connected" if db_ok else "unreachable",
            "llm_model": settings.LLM_MODEL,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Static Frontend (React build — served from frontend/dist)
# Single-URL deployment: FastAPI serves both API (/api/v1/*) and React SPA
# ─────────────────────────────────────────────────────────────────────────────
_CANDIDATE_PATHS = [
    Path(__file__).resolve().parent.parent / "frontend" / "dist",        # Docker: /app/frontend/dist
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist", # Local repo root: frontend/dist
    Path("/app/frontend/dist"),                                          # Explicit container path
]
_FRONTEND_DIST = next((p for p in _CANDIDATE_PATHS if p.exists() and (p / "index.html").is_file()), None)

if _FRONTEND_DIST:
    logger.info("Serving React frontend from: %s", _FRONTEND_DIST)
    # Serve static assets (JS, CSS, images, etc.)
    if (_FRONTEND_DIST / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
            name="frontend_assets",
        )

    @app.get("/", include_in_schema=False, tags=["Frontend"])
    async def serve_root():
        """Root route serves the React SPA index.html."""
        return FileResponse(str(_FRONTEND_DIST / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False, tags=["Frontend"])
    async def serve_spa(full_path: str):
        """
        SPA catch-all: returns index.html for every non-API, non-asset route
        so React Router handles client-side navigation.
        """
        # Do not catch API or documentation endpoints
        if (
            full_path.startswith("api/")
            or full_path.startswith("assets/")
            or full_path in ("docs", "redoc", "openapi.json", "health")
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        # If a specific static file exists (favicon.ico, vite.svg, etc.) serve it
        file_path = _FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise serve index.html (React Router takes over client-side navigation)
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
else:
    @app.get("/", tags=["System"], include_in_schema=False)
    async def root() -> dict:
        """API root hint when frontend dist is not present."""
        return {
            "message": "Retail BI API is running. Visit /docs for Swagger UI.",
            "docs": "/docs",
            "health": "/health",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Dev Runner
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # hot-reload in dev
        log_level="info",
    )
