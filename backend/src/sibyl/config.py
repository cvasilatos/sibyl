import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

MAX_SCORE: int = 5

STORAGE_PATH: Path = Path(os.getenv("SIBYL_STORAGE_PATH") or Path(__file__).resolve().parents[2] / "sibyl_storage")
"""Where reviews (ChromaDB) and their PDFs are kept. Defaults to ``backend/sibyl_storage`` (``/app/sibyl_storage`` in
Docker) wherever the server is started from; a relative path used to create a new store in each working directory."""


class LLMConfig(BaseModel):
    """Configuration for a single LLM provider."""

    name: str
    temperature: float = 0.7
    max_tokens: int = 300000
