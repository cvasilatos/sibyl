"""LLM client implementations for local open-source models."""

from abc import ABC, abstractmethod

from sibyl.config import LLMConfig


class Base(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the LLM client.

        Args:
            config: LLM configuration

        """
        self.config = config

    def get_name(self) -> str:
        """Get the name of this LLM client.

        Returns:
            The configured name of the LLM provider

        """
        return self.config.name

    @abstractmethod
    def generate(self, prompt: str, model_name: str) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            model_name: Name of the model to use

        Returns:
            Generated response text

        """
        ...

    @abstractmethod
    async def agenerate(self, prompt: str, model_name: str) -> str:
        """Generate a response from the LLM asynchronously.

        Args:
            prompt: The prompt to send to the LLM
            model_name: Name of the model to use

        Returns:
            Generated response text

        """
        ...
