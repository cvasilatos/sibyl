"""Pluggable inference engines for running open-source models.

Select one with ``SIBYL_ENGINE``:

- ``ollama`` (default): simplest; one Ollama server per GPU on Linux, or the native app on macOS (Metal).
- ``vllm``: fastest on NVIDIA GPUs; Sibyl downloads Hugging Face models and runs ``vllm serve`` per GPU.
- ``openai``: any OpenAI-compatible server you run yourself (LM Studio, llama.cpp server, SGLang, ...).
"""

import os

from sibyl.inference.base import AUTO_SLOT, EngineOperationNotSupportedError, GenerationRequest, InferenceEngine

ENGINES = ("ollama", "vllm", "openai")


def create_engine(name: str | None = None) -> InferenceEngine:
    """Create the engine named by ``name`` or the ``SIBYL_ENGINE`` environment variable."""
    choice = (name or os.getenv("SIBYL_ENGINE") or "ollama").strip().lower()
    if choice == "ollama":
        from sibyl.inference.ollama_engine import OllamaEngine  # noqa: PLC0415

        return OllamaEngine()
    if choice == "vllm":
        from sibyl.inference.vllm_engine import VLLMEngine  # noqa: PLC0415

        return VLLMEngine()
    if choice == "openai":
        from sibyl.inference.openai_engine import OpenAICompatibleEngine  # noqa: PLC0415

        return OpenAICompatibleEngine()
    raise ValueError(f"Unknown SIBYL_ENGINE '{choice}'. Choose one of: {', '.join(ENGINES)}")


__all__ = ["AUTO_SLOT", "ENGINES", "EngineOperationNotSupportedError", "GenerationRequest", "InferenceEngine", "create_engine"]
