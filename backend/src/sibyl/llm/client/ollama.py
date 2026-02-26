import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger


from ollama import AsyncClient, ChatResponse, Client

from sibyl.config import LLMConfig
from sibyl.llm.client.base import Base
from sibyl.web.model.llm_reply import LLMReply


class OllamaClient(Base):
    """Client for Ollama local LLM models."""

    def __init__(self, config: LLMConfig, host: str) -> None:
        """Initialize the Ollama client with the given configuration."""
        super().__init__(config)
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self._config: LLMConfig = config
        self.logger.info(f"Initializing OllamaClient with config: {self._config} and host: {host}")
        self._client = Client(host=host)
        self._async_client = AsyncClient(host=host)

    def generate(self, prompt: str, model_name: str) -> str:
        """Generate a response using the Ollama Python library."""
        self.logger.info(f"Generating response with Ollama model: {model_name}")
        response: ChatResponse = self._client.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={
                "temperature": self._config.temperature,
                "num_predict": self._config.max_tokens,
            },
        )
        raw_response: str = response.message.content or ""
        self.logger.debug(f"Raw response from Ollama ({model_name}) ({len(raw_response)} chars)")
        return raw_response

    async def agenerate(self, prompt: str, model_name: str) -> str:
        """Generate a response using the Ollama Python library asynchronously."""
        self.logger.debug(f"Sending async request to Ollama API for model: {model_name} - {prompt[:300]}...")
        response: ChatResponse = await self._async_client.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={
                "temperature": self._config.temperature,
                "num_predict": self._config.max_tokens,
            },
            format=LLMReply.model_json_schema(),
        )
        self.logger.debug(f"Raw async response from Ollama ({model_name})-{response}\n\n\n\n)")

        return response.message.content or ""
