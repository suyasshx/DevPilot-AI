"""
DevPilot AI - Groq Cloud LLM Provider.
Provides fast, OpenAI-compatible chat completions using Llama 3 models on Groq LPUs.
"""

import time
import logging
import asyncio
from typing import Optional, Dict, Any
import httpx

from .base import (
    BaseLLMProvider,
    LLMResponse,
    LLMProviderError,
    LLMAuthenticationError,
    LLMRateLimitError,
)

logger = logging.getLogger(__name__)


class GroqLLMProvider(BaseLLMProvider):
    """
    High-performance Groq LPU inference provider.
    Supports JSON mode, structured prompting, and retry with exponential backoff.
    """

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: str,
        model_name: str = "llama-3.3-70b-versatile",
        temperature: float = 0.1,
        base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        super().__init__(model_name=model_name, temperature=temperature)
        if not api_key:
            raise LLMAuthenticationError("GROQ_API_KEY must be provided to initialize GroqLLMProvider.")
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format_json: bool = True,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Execute chat completion on Groq with exponential backoff on transient errors.
        """
        temp = temperature if temperature is not None else self.temperature
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temp,
            "max_tokens": max_tokens,
        }

        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "DevPilot-AI/1.0",
        }

        url = f"{self.base_url}/chat/completions"
        backoff_delays = [1.0, 2.5, 5.0]

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            last_exception: Optional[Exception] = None

            for attempt in range(self.max_retries + 1):
                start_time = time.perf_counter()
                try:
                    logger.debug(
                        "Dispatching completion to Groq (model=%s, attempt=%d/%d)",
                        self.model_name,
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    response = await client.post(url, headers=headers, json=payload)
                    latency_ms = (time.perf_counter() - start_time) * 1000.0

                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        if not choices:
                            raise LLMProviderError("Groq returned empty choices array in completion response.")

                        message_content = choices[0].get("message", {}).get("content", "")
                        usage = data.get("usage", {})

                        return LLMResponse(
                            raw_text=message_content,
                            model_name=data.get("model", self.model_name),
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            total_tokens=usage.get("total_tokens", 0),
                            latency_ms=latency_ms,
                            metadata={"finish_reason": choices[0].get("finish_reason")},
                        )

                    elif response.status_code == 401:
                        raise LLMAuthenticationError(
                            f"Groq authentication failed (HTTP 401). Verify GROQ_API_KEY. Detail: {response.text}"
                        )
                    elif response.status_code == 429:
                        if attempt < self.max_retries:
                            delay = backoff_delays[min(attempt, len(backoff_delays) - 1)]
                            logger.warning(
                                "Groq rate limit (429) hit. Backing off for %.1f seconds (attempt %d)...",
                                delay,
                                attempt + 1,
                            )
                            await asyncio.sleep(delay)
                            continue
                        raise LLMRateLimitError(f"Groq rate limit exceeded after retries. Detail: {response.text}")
                    elif response.status_code in (500, 502, 503, 504):
                        if attempt < self.max_retries:
                            delay = backoff_delays[min(attempt, len(backoff_delays) - 1)]
                            logger.warning(
                                "Groq transient server error (%d). Retrying in %.1f seconds...",
                                response.status_code,
                                delay,
                            )
                            await asyncio.sleep(delay)
                            continue
                        raise LLMProviderError(
                            f"Groq server error {response.status_code} after retries: {response.text}"
                        )
                    else:
                        raise LLMProviderError(
                            f"Groq API returned HTTP {response.status_code}: {response.text}"
                        )

                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    last_exception = exc
                    if attempt < self.max_retries:
                        delay = backoff_delays[min(attempt, len(backoff_delays) - 1)]
                        logger.warning(
                            "Network error contacting Groq: %s. Retrying in %.1f seconds...",
                            str(exc),
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise LLMProviderError(f"Failed to connect to Groq API after retries: {str(exc)}") from exc

            if last_exception:
                raise LLMProviderError(f"Groq completion failed: {str(last_exception)}") from last_exception
            raise LLMProviderError("Groq completion failed with unexpected termination.")
