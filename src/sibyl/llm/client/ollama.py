import logging
from typing import TYPE_CHECKING, cast

import httpx
import requests

if TYPE_CHECKING:
    from decimalog.logger import CustomLogger
    from httpx._models import Response


from sibyl.config import OLLAMA_BASE_URL, LLMConfig
from sibyl.llm.client.base import Base


class OllamaClient(Base):
    """Client for Ollama local LLM models."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self._config: LLMConfig = config
        self._api_url = f"{OLLAMA_BASE_URL}/api/generate"

    def generate(self, prompt: str, model: str, system_prompt: str | None = None) -> str:
        """Generate a response using Ollama's API."""
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        self.logger.info(f"Generating response with Ollama model: {model}")
        response: requests.Response = requests.post(self._api_url, json=payload, timeout=300)
        response.raise_for_status()
        raw_response: str = response.json().get("response", "")
        self.logger.debug(f"Raw response from Ollama ({model}) ({len(raw_response)} chars)")
        return raw_response

    async def agenerate(self, prompt: str, model: str, system_prompt: str | None = None) -> str:
        """Generate a response using Ollama's API asynchronously."""
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"

        self.logger.info(f"Generating async response with Ollama model: {model}")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            self.logger.debug(f"Sending async request to Ollama API for model: {model}")
            response: Response = await client.post(self._api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            raw_response = result.get("response", "")
            self.logger.debug(f"Raw async response from Ollama ({model}) ({len(raw_response)} chars)")

        return raw_response
