"""LLM client implementations for different providers."""

from abc import ABC, abstractmethod
from typing import Optional
import openai
import anthropic
try:
    from google import genai
except ImportError:
    # Fallback to older package if new one not available
    import google.generativeai as genai

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
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the LLM provider."""
        pass


class OpenAIClient(LLMClient):
    """Client for OpenAI GPT models."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = openai.OpenAI(api_key=config.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using OpenAI's API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content

    def get_name(self) -> str:
        return f"OpenAI ({self.config.model})"


class AnthropicClient(LLMClient):
    """Client for Anthropic Claude models."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=config.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using Anthropic's API."""
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def get_name(self) -> str:
        return f"Anthropic ({self.config.model})"


class GoogleClient(LLMClient):
    """Client for Google Gemini models."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            # Try new API first
            self.client = genai.Client(api_key=config.api_key)
            self.use_new_api = True
        except (AttributeError, TypeError):
            # Fall back to old API
            genai.configure(api_key=config.api_key)
            self.model = genai.GenerativeModel(config.model)
            self.use_new_api = False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using Google's Gemini API."""
        # Combine system prompt with user prompt if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        if self.use_new_api:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=full_prompt,
                config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                },
            )
            return response.text
        else:
            # Old API
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_tokens,
                ),
            )
            return response.text

    def get_name(self) -> str:
        return f"Google ({self.config.model})"


def create_client(provider: str, config: LLMConfig) -> LLMClient:
    """Factory function to create LLM clients.

    Args:
        provider: Provider name ('openai', 'anthropic', or 'google')
        config: LLM configuration

    Returns:
        Initialized LLM client

    Raises:
        ValueError: If provider is not supported
    """
    clients = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "google": GoogleClient,
    }

    client_class = clients.get(provider)
    if not client_class:
        raise ValueError(f"Unsupported provider: {provider}")

    return client_class(config)
