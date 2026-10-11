"""
DevPilot AI - LLM Provider Factory.
Instantiates either Groq Cloud provider or Mock provider based on configuration and environment.
"""

import logging
from typing import Optional
from ..core.config import settings
from .base import BaseLLMProvider
from .groq_provider import GroqLLMProvider
from .mock_provider import MockLLMProvider

logger = logging.getLogger(__name__)


def get_llm_provider(
    force_mock: bool = False,
    model_override: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Get an active LLM provider instance.

    If force_mock is True or GROQ_API_KEY is not configured, returns MockLLMProvider.
    Otherwise returns GroqLLMProvider.
    """
    if force_mock or not settings.GROQ_API_KEY or settings.GROQ_API_KEY.strip() == "":
        logger.info("Using MockLLMProvider for contract-grounded test generation (offline / CI mode).")
        return MockLLMProvider(model_name=model_override or "mock-llama-3.3-70b")

    logger.info("Using GroqLLMProvider (model: %s)", model_override or settings.GROQ_MODEL)
    return GroqLLMProvider(
        api_key=settings.GROQ_API_KEY,
        model_name=model_override or settings.GROQ_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_retries=settings.LLM_MAX_RETRIES,
    )
