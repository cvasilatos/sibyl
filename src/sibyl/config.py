import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class LLMConfig(BaseModel):
    """Configuration for a single LLM provider."""

    name: str
    api_key: str | None = None
    api_url: str | None = None
    model: str
    temperature: float = 0.7
    max_tokens: int = 300000


class SibylConfig(BaseModel):
    """Main configuration for Sibyl."""

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Create configuration from environment variables."""
        config_dict = {}

        ollama_model: str | None = os.getenv("OLLAMA_MODEL")
        if ollama_model:
            config_dict["ollama"] = LLMConfig(
                name="Ollama",
                api_url=OLLAMA_BASE_URL,
                model=ollama_model,
                temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "8000")),
            )

        return config_dict["ollama"]
