"""Ollama engine: easiest setup, runs on NVIDIA (CUDA) and Apple Silicon (Metal)."""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import httpx
from ollama import AsyncClient

from sibyl.inference.base import AUTO_SLOT, GenerationRequest, InferenceEngine, cap_context, estimate_tokens, max_context_setting
from sibyl.inference.ollama_gpus import OllamaGpuServers, required_memory
from sibyl.services.model_catalog import ModelCatalog

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

KEEP_LOADED = "5m"


MIN_OUTPUT_TOKENS = 1024


def output_room(request: GenerationRequest) -> int:
    """Tokens left for the answer once the prompt fills its share of the context.

    Ollama has no "until the context is full" setting that is safe with schema-constrained output (``-1`` shifts the
    context and can loop forever), so the cap is the rest of the window. The prompt estimate errs high, so the real
    room is slightly larger.
    """
    return max(request.context_length - estimate_tokens(request.system + request.prompt), MIN_OUTPUT_TOKENS)


def ollama_hosts_from_env() -> list[str]:
    """Return Ollama hosts from ``OLLAMA_HOSTS`` (comma separated, one per GPU) or ``OLLAMA_BASE_URL``."""
    hosts = [h.strip() for h in os.getenv("OLLAMA_HOSTS", "").split(",") if h.strip()]
    return hosts or [os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")]


class OllamaEngine(InferenceEngine):
    """Run models through one or more Ollama servers (one server per GPU in multi-GPU setups)."""

    name = "ollama"
    label = "Ollama"
    supports_downloads = True

    def __init__(self, hosts: list[str] | None = None, keep_alive: str | None = None, gpu_servers: OllamaGpuServers | None = None) -> None:
        """Create clients for every configured Ollama host.

        With a single host (no ``OLLAMA_HOSTS``) on a multi-GPU machine, Sibyl starts its own per-GPU Ollama servers so
        reviews honor the chosen GPU (see ``ollama_gpus``).
        """
        self.hosts = hosts or ollama_hosts_from_env()
        self.clients = [AsyncClient(host=host) for host in self.hosts]
        if gpu_servers is None and hosts is None and len(self.hosts) == 1:
            gpu_servers = OllamaGpuServers.from_env()
        self.gpu_servers = gpu_servers
        self._gpu_clients: dict[str, AsyncClient] = {}
        self._model_sizes: dict[str, int] = {}
        # "0" unloads the model right after each review, freeing VRAM for PDF parsing on shared GPUs.
        self.keep_alive = keep_alive if keep_alive is not None else os.getenv("OLLAMA_KEEP_ALIVE", "0")
        self._native_context: dict[str, int | None] = {}

    @property
    def admin(self) -> AsyncClient:
        """Client used for model management (all hosts share one model store)."""
        return self.clients[0]

    def client_for_slot(self, slot: int) -> AsyncClient:
        """Map a review slot (0 = auto, n = GPU n-1) to an Ollama host."""
        if slot == AUTO_SLOT:
            return self.clients[0]
        index = slot - 1
        if index >= len(self.clients):
            logger.warning("Slot %s requested but only %s Ollama host(s) configured; using the first", slot, len(self.clients))
            return self.clients[0]
        return self.clients[index]

    async def model_size(self, model: str) -> int:
        """Size in bytes of an installed model's file (0 if unknown), cached."""
        if model not in self._model_sizes:
            with contextlib.suppress(Exception):
                for m in (await self.admin.list()).models:
                    self._model_sizes[m.model or ""] = m.size or 0
        return self._model_sizes.get(model, 0)

    @contextlib.asynccontextmanager
    async def client_for_request(self, request: GenerationRequest) -> AsyncIterator[AsyncClient]:
        """Client for the GPU the request asked for; on auto, the least busy GPU that fits the model, else all GPUs."""
        servers = self.gpu_servers
        if servers is None:
            yield self.client_for_slot(request.slot)
            return
        if request.slot == AUTO_SLOT:
            need = required_memory(await self.model_size(request.model), request.context_length)
            gpu = servers.choose(request.model, need)
            if gpu is None:  # too big for any single GPU (or no stats): the main server splits it across GPUs
                logger.info("%s needs ~%.0f GiB: no single GPU has room, splitting it across GPUs", request.model, need / 2**30)
                yield self.admin
                return
        else:
            gpu = request.slot - 1
            if gpu not in servers.gpus:
                logger.warning("GPU %s requested but this machine has GPUs %s; letting Ollama choose", gpu, servers.gpus)
                yield self.admin
                return
        async with servers.lease(gpu, request.model, request.on_status) as url:
            logger.info("Running %s on GPU %s", request.model, gpu)
            if url not in self._gpu_clients:
                self._gpu_clients[url] = AsyncClient(host=url)
            yield self._gpu_clients[url]

    async def native_context_length(self, model: str) -> int | None:
        """Return the model's own context limit (``<arch>.context_length`` from ``ollama show``), cached; ``None`` if unknown."""
        if model not in self._native_context:
            native: int | None = None
            try:
                info = (await self.admin.show(model)).modelinfo
                if isinstance(info, Mapping):
                    native = next((v for k, v in info.items() if k.endswith(".context_length") and isinstance(v, int)), None)
            except Exception as e:  # an unknown limit falls back to SIBYL_MAX_CONTEXT or the default
                logger.debug("Could not read the context length of %s: %s", model, e)
            self._native_context[model] = native
        return self._native_context[model]

    async def context_window(self, model: str) -> int:
        """``SIBYL_MAX_CONTEXT`` capped by the model's own limit (so Ollama never runs it past what it was trained on), or that limit itself for ``model``."""
        return cap_context(await self.native_context_length(model), max_context_setting())

    async def list_installed(self) -> list[dict[str, Any]]:  # noqa: D102
        response = await self.admin.list()
        return [
            {
                "model": m.model,
                "size": m.size or 0,
                "modified_at": m.modified_at.isoformat() if m.modified_at else "",
                "digest": m.digest or m.model,
            }
            for m in response.models
        ]

    async def list_catalog(self) -> list[dict[str, Any]]:  # noqa: D102
        installed = await self.admin.list()
        return await ModelCatalog(client_factory=httpx.AsyncClient).list_available(installed)

    async def list_variants(self, name: str) -> list[str]:  # noqa: D102
        return await ModelCatalog(client_factory=httpx.AsyncClient).list_tags(name)

    async def pull(self, model: str) -> AsyncIterator[dict[str, Any]]:  # noqa: D102
        self._native_context.pop(model, None)
        self._model_sizes.pop(model, None)
        async for part in await self.admin.pull(model=model, stream=True):
            yield part.model_dump() if hasattr(part, "model_dump") else dict(part)

    async def delete(self, model: str) -> None:  # noqa: D102
        self._native_context.pop(model, None)
        await self.admin.delete(model=model)

    async def generate_json(self, request: GenerationRequest) -> str:  # noqa: D102
        # /api/chat, not /api/generate: with a schema, generate returns an empty response for models that reason before
        # answering (gpt-oss, ...). Chat keeps the reasoning in ``message.thinking`` and the JSON in ``message.content``.
        user: dict[str, Any] = {"role": "user", "content": request.prompt}
        if request.images:
            user["images"] = request.images
        async with self.client_for_request(request) as client:
            response = await client.chat(
                model=request.model,
                messages=[{"role": "system", "content": request.system}, user],
                stream=False,
                format=request.schema,
                options={
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens if request.max_tokens is not None else output_room(request),
                    # Without this Ollama falls back to a small default context and silently drops most of the paper.
                    "num_ctx": request.context_length,
                },
                # Keep a model loaded between consecutive requests (e.g. one per figure) instead of reloading it each time.
                keep_alive=KEEP_LOADED if request.keep_loaded else self.keep_alive,
            )
        return response.message.content or ""

    async def aclose(self) -> None:  # noqa: D102
        if self.gpu_servers is not None:
            await self.gpu_servers.shutdown()
