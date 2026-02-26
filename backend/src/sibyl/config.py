from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

MAX_SCORE: int = 5


class LLMConfig(BaseModel):
    """Configuration for a single LLM provider."""

    name: str
    temperature: float = 0.7
    max_tokens: int = 300000
