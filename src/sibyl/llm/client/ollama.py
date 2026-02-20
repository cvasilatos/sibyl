import logging
from typing import TYPE_CHECKING, cast

import requests

if TYPE_CHECKING:
    from decimalog.logger import CustomLogger


from ollama import AsyncClient, ChatResponse

from sibyl.config import OLLAMA_BASE_URL, LLMConfig
from sibyl.llm.client.base import Base
from sibyl.web.model.llm_reply import LLMReply


class OllamaClient(Base):
    """Client for Ollama local LLM models."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self._config: LLMConfig = config
        self._api_url = f"{OLLAMA_BASE_URL}/api/generate"

    def generate(self, prompt: str, model: str) -> str:
        """Generate a response using Ollama's API."""
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

    async def agenerate(self, prompt: str, model: str) -> str:
        """Generate a response using Ollama's API asynchronously."""
        self.logger.debug(f"Sending async request to Ollama API for model: {model} - {prompt[:300]}...")
        response: ChatResponse = await AsyncClient().chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
            format=LLMReply.model_json_schema(),
        )
        self.logger.debug(f"Raw async response from Ollama ({model})-{response}\n\n\n\n)")

        return response.message.content
