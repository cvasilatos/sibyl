"""Configuration management for Sibyl."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class LLMConfig(BaseModel):
    """Configuration for a single LLM provider."""

    name: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4000


class SibylConfig(BaseModel):
    """Main configuration for Sibyl."""

    openai: Optional[LLMConfig] = None
    anthropic: Optional[LLMConfig] = None
    google: Optional[LLMConfig] = None

    @classmethod
    def from_env(cls) -> "SibylConfig":
        """Create configuration from environment variables."""
        config_dict = {}

        # OpenAI configuration
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            config_dict["openai"] = LLMConfig(
                name="OpenAI",
                api_key=openai_key,
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
            )

        # Anthropic configuration
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            config_dict["anthropic"] = LLMConfig(
                name="Anthropic",
                api_key=anthropic_key,
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            )

        # Google configuration
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            config_dict["google"] = LLMConfig(
                name="Google",
                api_key=google_key,
                model=os.getenv("GOOGLE_MODEL", "gemini-pro"),
            )

        return cls(**config_dict)

    def get_active_providers(self) -> list[str]:
        """Get list of active LLM providers."""
        providers = []
        if self.openai:
            providers.append("openai")
        if self.anthropic:
            providers.append("anthropic")
        if self.google:
            providers.append("google")
        return providers
