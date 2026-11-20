"""
app/agents/llm.py
──────────────────
Configures the LLM for CrewAI multi-agent orchestration.
Uses Google Gemini via LiteLLM with low temperature (0.2) to ensure
deterministic analytical reasoning and eliminate hallucinations.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from crewai import LLM

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_llm() -> LLM:
    """
    Initialize and return the configured CrewAI LLM instance.

    Model: settings.LLM_MODEL (e.g. 'gemini/gemini-1.5-pro')
    Temperature: 0.2 (low variance for analytical and financial precision)
    """
    api_key = settings.LLM_API_KEY
    if not api_key:
        logger.warning("LLM_API_KEY is not set in environment or .env file.")

    # LiteLLM uses GEMINI_API_KEY / GOOGLE_API_KEY environment variables
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        os.environ["GOOGLE_API_KEY"] = api_key

    logger.info("Initializing CrewAI LLM with model: %s, temp: 0.2", settings.LLM_MODEL)

    return LLM(
        model=settings.LLM_MODEL,
        api_key=api_key,
        temperature=0.2,
    )
