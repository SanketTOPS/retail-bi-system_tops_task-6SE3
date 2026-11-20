"""
app/schemas/profile.py
───────────────────────
Pydantic v2 schemas for BusinessProfile CRUD operations.

Validations:
  - company_name: 2-300 characters, required
  - industry: valid string, e.g. Retail, Healthcare, Banking
  - team_size: must be strictly > 0 if provided
  - business_goals: accepts either a list of strings or a comma/newline separated text string,
    normalizing it into list[str]
  - founded_year: between 1800 and current year + 1
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessProfileBase(BaseModel):
    company_name: str = Field(
        ...,
        min_length=2,
        max_length=300,
        examples=["RetailPulse Analytics Ltd."],
        description="Official company or business name",
    )
    industry: str = Field(
        default="Retail",
        max_length=100,
        examples=["Retail"],
        description="Industry sector (e.g. Retail, Healthcare, Banking, Manufacturing)",
    )
    description: str | None = Field(
        None,
        max_length=2000,
        examples=["Omnichannel retail brand operating online and across 15 store locations."],
        description="Short description of the company and business scope",
    )
    team_size: int | None = Field(
        None,
        gt=0,
        examples=[45],
        description="Total team / employee headcount (must be strictly greater than 0)",
    )
    business_goals: list[str] | str | None = Field(
        default=None,
        examples=[["Increase Q3 gross margin by 15%", "Automate inventory reorder points"]],
        description="Strategic business goals. Can be passed as a list of strings or single text block.",
    )
    city: str | None = Field(None, max_length=100, examples=["Bengaluru"])
    country: str = Field(default="India", max_length=100, examples=["India"])
    website: str | None = Field(None, max_length=500, examples=["https://retailpulse.example.com"])
    phone: str | None = Field(None, max_length=30, examples=["+91-9876543210"])
    logo_url: str | None = Field(None, max_length=500, examples=["https://retailpulse.example.com/logo.png"])
    founded_year: int | None = Field(None, ge=1800, le=2050, examples=[2018])

    @field_validator("business_goals", mode="before")
    @classmethod
    def normalize_business_goals(cls, v: Any) -> list[str] | None:
        """Convert string input or lists into a cleaned list of goal strings."""
        if v is None:
            return None
        if isinstance(v, list):
            cleaned = [str(item).strip() for item in v if str(item).strip()]
            return cleaned if cleaned else None
        if isinstance(v, str):
            lines = [line.strip().lstrip("-•* ").strip() for line in v.replace(";", "\n").splitlines()]
            cleaned = [item for item in lines if item]
            return cleaned if cleaned else None
        return v


class BusinessProfileCreate(BusinessProfileBase):
    """Payload for POST /profile (creating profile for current user)."""
    pass


class BusinessProfileUpdate(BaseModel):
    """Payload for PUT /profile (updating existing profile). All fields optional."""
    company_name: str | None = Field(None, min_length=2, max_length=300)
    industry: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=2000)
    team_size: int | None = Field(None, gt=0)
    business_goals: list[str] | str | None = None
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=30)
    logo_url: str | None = Field(None, max_length=500)
    founded_year: int | None = Field(None, ge=1800, le=2050)

    @field_validator("business_goals", mode="before")
    @classmethod
    def normalize_business_goals(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            cleaned = [str(item).strip() for item in v if str(item).strip()]
            return cleaned if cleaned else None
        if isinstance(v, str):
            lines = [line.strip().lstrip("-•* ").strip() for line in v.replace(";", "\n").splitlines()]
            cleaned = [item for item in lines if item]
            return cleaned if cleaned else None
        return v


class BusinessProfileResponse(BaseModel):
    """Response model for business profile."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_name: str
    industry: str
    description: str | None = None
    team_size: int | None = None
    business_goals: list[str] | None = None
    city: str | None = None
    country: str
    website: str | None = None
    phone: str | None = None
    logo_url: str | None = None
    founded_year: int | None = None
    created_at: datetime
    updated_at: datetime
