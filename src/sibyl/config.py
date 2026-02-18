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
    api_key: Optional[str] = None  # Not needed for local models
    api_url: Optional[str] = None  # For Ollama base URL
    model: str
    temperature: float = 0.7
    max_tokens: int = 4000


class SibylConfig(BaseModel):
    """Main configuration for Sibyl."""

    ollama: Optional[LLMConfig] = None

    @classmethod
    def from_env(cls) -> "SibylConfig":
        """Create configuration from environment variables."""
        config_dict = {}

        # Ollama configuration
        ollama_model = os.getenv("OLLAMA_MODEL")
        if ollama_model:
            config_dict["ollama"] = LLMConfig(
                name="Ollama",
                api_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=ollama_model,
                temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "4000")),
            )

        return cls(**config_dict)

    def get_active_providers(self) -> list[str]:
        """Get list of active LLM providers."""
        providers = []
        if self.ollama:
            providers.append("ollama")
        return providers
