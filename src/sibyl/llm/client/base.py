"""LLM client implementations for local open-source models."""

from abc import ABC, abstractmethod

from sibyl.config import LLMConfig


class Base(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config: LLMConfig):
        """Initialize the LLM client.

        Args:
            config: LLM configuration

        """
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt for context

        Returns:
            Generated response text

        """
        ...

    @abstractmethod
    async def agenerate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a response from the LLM asynchronously.

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
