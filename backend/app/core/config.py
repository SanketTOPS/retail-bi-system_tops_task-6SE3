"""
app/core/config.py
──────────────────
Centralised application settings loaded from the .env file.
All secrets are accessed ONLY through this module — never hardcoded.
Pydantic-Settings automatically reads values from environment / .env file.
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # ignore unknown env vars gracefully
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT Authentication ────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── LLM (Gemini via LiteLLM) ──────────────────────────────────────────────
    LLM_MODEL: str = "gemini/gemini-3.1-flash-lite"
    LLM_API_KEY: str

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── File Upload ───────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── App Meta ──────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS_ORIGINS as a Python list (split on comma)."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        """Return upload size limit in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings factory.
    Use via FastAPI Depends(get_settings) or direct import.
    The @lru_cache ensures the .env file is parsed exactly once per process.
    """
    return Settings()


# Module-level singleton — convenient for non-DI usage (e.g., agents layer)
settings: Settings = get_settings()
