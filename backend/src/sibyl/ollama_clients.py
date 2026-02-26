"""Sibyl: An LLM-powered research paper review system."""

import logging
import os
from pathlib import Path
from typing import cast

from decima import CustomLogger
from ollama import AsyncClient, Client

logger: CustomLogger = cast("CustomLogger", logging.getLogger("sibyl.main"))

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
docker_ollama: dict[int, AsyncClient] = {
    0: AsyncClient(host="http://ollama-0:11434"),
    1: AsyncClient(host="http://ollama-1:11434"),
}

base_ollama_async: AsyncClient = AsyncClient(host=OLLAMA_BASE_URL)
base_ollama: Client = Client(host=OLLAMA_BASE_URL)


def _is_docker() -> bool:
    exists: bool = Path("/.dockerenv").exists()
    logger.debug(f"Checking if running in Docker environment...{exists}")
    return exists


def get_ollama_client() -> AsyncClient | Client:
    """Get the appropriate Ollama client based on the environment."""
    if _is_docker():
        return docker_ollama[0]
    return base_ollama
