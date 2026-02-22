import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

MAX_SCORE: int = 5


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

    ollama: LLMConfig | None = None

    def get_active_providers(self) -> list[str]:
        """Get list of active provider names.

        Returns:
            List of configured provider names

        """
        providers: list[str] = []
        if self.ollama:
            providers.append("ollama")
        return providers

    @classmethod
    def from_env(cls) -> "SibylConfig":
        """Create configuration from environment variables."""
        ollama_model: str | None = os.getenv("OLLAMA_MODEL")
        ollama: LLMConfig | None = None
        if ollama_model:
            ollama = LLMConfig(
                name="Ollama",
                api_url=OLLAMA_BASE_URL,
                model=ollama_model,
                temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "8000")),
            )

        return cls(ollama=ollama)
