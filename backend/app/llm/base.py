"""
DevPilot AI - LLM Provider Abstract Base Interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication with LLM provider fails."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when LLM API rate limits (HTTP 429) are encountered."""
    pass


class LLMJsonParseError(LLMProviderError):
    """Raised when LLM output cannot be parsed into the expected JSON structure."""
    pass


@dataclass
class LLMResponse:
    """Structured response envelope from an LLM provider."""
    raw_text: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract interface that all LLM providers (Groq, Mock, etc.) must implement."""

    def __init__(self, model_name: str, temperature: float = 0.1) -> None:
        self.model_name = model_name
        self.temperature = temperature

    @abstractmethod
    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format_json: bool = True,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Send a chat completion request to the LLM.

        Args:
            system_prompt: System role instructions defining the QA persona and rules.
            user_prompt: User role prompt containing RAG context and target requirements.
            response_format_json: If True, request strict JSON output from the model.
            temperature: Sampling temperature override.
            max_tokens: Maximum tokens to generate.

        Returns:
            LLMResponse envelope containing response text and execution metadata.
        """
        pass
