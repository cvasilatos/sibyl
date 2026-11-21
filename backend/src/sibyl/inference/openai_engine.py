"""Engine for any OpenAI-compatible server (vLLM, SGLang, LM Studio, llama.cpp server, ...)."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

import httpx

from sibyl.inference.base import EngineOperationNotSupportedError, GenerationRequest, InferenceEngine, env_float

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


async def chat_json(base_url: str, request: GenerationRequest, api_key: str | None = None, timeout: float = 1800.0) -> str:  # noqa: ASYNC109
    """Call ``/v1/chat/completions`` with a JSON-schema ``response_format`` and return the message content."""
    user_content: str | list[dict[str, Any]] = request.prompt
    if request.images:
        user_content = [
            {"type": "text", "text": request.prompt},
            *({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}} for image in request.images),
        ]
    payload = {
        "model": request.model,
        "messages": [{"role": "system", "content": request.system}, {"role": "user", "content": user_content}],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "response_format": {"type": "json_schema", "json_schema": {"name": "paper_review", "schema": request.schema, "strict": True}},
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout, headers=headers) as client:
        response = await client.post("/chat/completions", json=payload)
        if response.status_code >= 400:  # noqa: PLR2004
            raise RuntimeError(f"Inference server returned {response.status_code}: {response.text[:500]}")
        data = response.json()
    content = data["choices"][0]["message"].get("content") or ""
    logger.debug("Usage for %s: %s", request.model, json.dumps(data.get("usage", {})))
    return content


class OpenAICompatibleEngine(InferenceEngine):
    """Use an externally managed OpenAI-compatible server. Models are managed by that server, not by Sibyl."""

    name = "openai"
    label = "OpenAI-compatible server"
    supports_downloads = False

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        """Configure the server base URL (must include ``/v1``)."""
        self.base_url = base_url or os.getenv("SIBYL_OPENAI_BASE_URL", "http://localhost:1234/v1")
        self.api_key = api_key or os.getenv("SIBYL_OPENAI_API_KEY") or None
        self.timeout = env_float("SIBYL_REQUEST_TIMEOUT", 1800.0)

    async def list_installed(self) -> list[dict[str, Any]]:  # noqa: D102
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(base_url=self.base_url.rstrip("/"), timeout=30.0, headers=headers) as client:
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json().get("data", [])
        return [{"model": m["id"], "size": 0, "modified_at": "", "digest": m["id"]} for m in data]

    async def list_catalog(self) -> list[dict[str, Any]]:  # noqa: D102
        return []

    async def list_variants(self, name: str) -> list[str]:  # noqa: ARG002, D102
        return []

    async def pull(self, model: str) -> AsyncIterator[dict[str, Any]]:  # noqa: D102
        raise EngineOperationNotSupportedError(f"Download '{model}' in your inference server; Sibyl cannot manage its models.")
        yield {}  # pragma: no cover - makes this an async generator

    async def delete(self, model: str) -> None:  # noqa: D102
        raise EngineOperationNotSupportedError(f"Remove '{model}' in your inference server; Sibyl cannot manage its models.")

    async def generate_json(self, request: GenerationRequest) -> str:  # noqa: D102
        return await chat_json(self.base_url, request, api_key=self.api_key, timeout=self.timeout)
