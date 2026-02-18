"""LLM client implementations for local open-source models."""

from abc import ABC, abstractmethod
from typing import Optional

import requests

from .config import LLMConfig


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config: LLMConfig):
        """Initialize the LLM client.

        Args:
            config: LLM configuration

        """
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt for context

        Returns:
            Generated response text

        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the LLM provider."""
        ...


class OllamaClient(LLMClient):
    """Client for Ollama local LLM models."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.api_url or "http://localhost:11434"
        self.api_url = f"{self.base_url}/api/generate"

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using Ollama's API."""
        # Combine system prompt with user prompt if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300,  # 5 minute timeout for large models
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Failed to connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running. Error: {e}"
            )

    def get_name(self) -> str:
        return f"Ollama ({self.config.model})"


def create_client(provider: str, config: LLMConfig) -> LLMClient:
    """Factory function to create LLM clients.

    Args:
        provider: Provider name ('ollama')
        config: LLM configuration

    Returns:
        Initialized LLM client

    Raises:
        ValueError: If provider is not supported

    """
    clients = {
        "ollama": OllamaClient,
    }

    client_class = clients.get(provider)
    if not client_class:
        raise ValueError(
            f"Unsupported provider: {provider}. Supported providers: {list(clients.keys())}"
        )

    return client_class(config)
