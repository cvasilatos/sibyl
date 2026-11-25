"""vLLM engine: high-throughput GPU inference with models downloaded from Hugging Face.

Sibyl manages everything: models are downloaded into the Hugging Face cache from the Models tab, and a
``vllm serve`` process is started on demand on the requested GPU (one process per GPU). Requests that target
the same model on the same GPU share the server, so vLLM's continuous batching applies to them.
"""

from __future__ import annotations

import asyncio
import contextlib
import fnmatch
import json
import logging
import os
import shlex
import signal
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from sibyl.inference.base import AUTO_SLOT, GenerationRequest, InferenceEngine, cap_context, env_float, env_int, max_context_setting
from sibyl.inference.openai_engine import chat_json
from sibyl.services.hardware import nvidia_gpu_count

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

logger = logging.getLogger(__name__)

# Instruction-tuned open models that handle long scientific documents well. Shown first in the catalog.
RECOMMENDED_MODELS: list[tuple[str, str]] = [
    ("Qwen/Qwen3-8B", "Recommended · 8B · fits a single 24 GB GPU"),
    ("Qwen/Qwen3-14B", "Recommended · 14B · strong reviewer on 40-48 GB GPUs"),
    ("Qwen/Qwen3-32B", "Recommended · 32B · best Qwen dense model, needs 80 GB"),
    ("Qwen/Qwen3-30B-A3B-Instruct-2507", "Recommended · MoE 30B (3B active) · fast, long context"),
    ("google/gemma-3-12b-it", "Recommended · 12B · gated, needs HF_TOKEN"),
    ("google/gemma-3-27b-it", "Recommended · 27B · gated, needs HF_TOKEN"),
    ("mistralai/Mistral-Small-3.2-24B-Instruct-2506", "Recommended · 24B"),
    ("meta-llama/Llama-3.1-8B-Instruct", "Recommended · 8B · gated, needs HF_TOKEN"),
    ("meta-llama/Llama-3.3-70B-Instruct", "Recommended · 70B · gated, needs HF_TOKEN and 2+ GPUs"),
    ("microsoft/phi-4", "Recommended · 14B"),
    ("openai/gpt-oss-20b", "Recommended · 21B MoE"),
]

# Only download what vLLM needs: skip duplicate weight formats (.bin/.pth/.gguf/onnx) when safetensors exist.
_WEIGHT_PATTERNS = ["*.safetensors", "*.safetensors.index.json"]
_SUPPORT_PATTERNS = ["*.json", "*.model", "*.tiktoken", "*.txt", "*.jinja", "tokenizer*", "*.py"]
_FALLBACK_WEIGHT_PATTERNS = ["*.bin", "*.bin.index.json"]
_SKIP_PATTERNS = ["original/*", "onnx/*", "*.gguf", "*.pth", "*.msgpack", "*.h5"]


def select_download_files(files: dict[str, int]) -> dict[str, int]:
    """Choose which repo files to download (``{path: size}``), preferring safetensors weights."""

    def matches(path: str, patterns: list[str]) -> bool:
        name = path.rsplit("/", 1)[-1]
        return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)

    candidates = {p: s for p, s in files.items() if not matches(p, _SKIP_PATTERNS)}
    has_safetensors = any(p.endswith(".safetensors") for p in candidates)
    weights = _WEIGHT_PATTERNS if has_safetensors else _FALLBACK_WEIGHT_PATTERNS
    return {p: s for p, s in candidates.items() if matches(p, weights) or matches(p, _SUPPORT_PATTERNS)}


class HuggingFaceStore:
    """Download, list and delete models in the local Hugging Face cache."""

    async def list_installed(self) -> list[dict[str, Any]]:
        """Return cached repos that look like loadable LLMs."""
        return await asyncio.to_thread(self._list_installed_sync)

    @staticmethod
    def _list_installed_sync() -> list[dict[str, Any]]:
        from huggingface_hub import scan_cache_dir  # noqa: PLC0415

        try:
            cache = scan_cache_dir()
        except Exception:
            return []
        models = []
        for repo in cache.repos:
            if repo.repo_type != "model":
                continue
            names = {f.file_name for rev in repo.revisions for f in rev.files}
            if "config.json" not in names or not any(n.endswith((".safetensors", ".bin")) for n in names):
                continue
            models.append(
                {
                    "model": repo.repo_id,
                    "size": repo.size_on_disk,
                    "modified_at": datetime.fromtimestamp(repo.last_modified, tz=UTC).isoformat(),
                    "digest": repo.repo_id,
                }
            )
        return sorted(models, key=lambda m: m["model"].lower())

    async def list_catalog(self, installed: set[str]) -> list[dict[str, Any]]:
        """Return recommended models followed by the most downloaded text-generation models on the Hub."""
        entries: dict[str, str] = dict(RECOMMENDED_MODELS)
        try:
            popular = await asyncio.to_thread(self._popular_models)
        except Exception:
            logger.warning("Could not fetch Hugging Face catalog; showing recommended models only", exc_info=True)
            popular = []
        for repo_id, downloads in popular:
            entries.setdefault(repo_id, f"Hugging Face · {downloads:,} downloads")
        return [{"name": name, "description": description, "size": "", "installed": name in installed, "installed_variants": []} for name, description in entries.items()]

    @staticmethod
    def _popular_models(limit: int = 200) -> list[tuple[str, int]]:
        from huggingface_hub import HfApi  # noqa: PLC0415

        models = HfApi().list_models(pipeline_tag="text-generation", sort="downloads", limit=limit)
        return [(m.id, m.downloads or 0) for m in models]

    async def pull(self, repo_id: str) -> AsyncIterator[dict[str, Any]]:
        """Download a repo snapshot, yielding byte-level progress by watching the cache directory."""
        from huggingface_hub import HfApi, snapshot_download  # noqa: PLC0415
        from huggingface_hub.constants import HF_HUB_CACHE  # noqa: PLC0415
        from huggingface_hub.file_download import repo_folder_name  # noqa: PLC0415

        yield {"status": f"resolving {repo_id}"}
        info = await asyncio.to_thread(HfApi().model_info, repo_id, files_metadata=True)
        files = select_download_files({s.rfilename: s.size or 0 for s in info.siblings or []})
        if not files:
            raise ValueError(f"{repo_id} has no downloadable weights")
        total = sum(files.values())
        blobs = Path(HF_HUB_CACHE) / repo_folder_name(repo_id=repo_id, repo_type="model") / "blobs"

        task = asyncio.create_task(asyncio.to_thread(snapshot_download, repo_id, allow_patterns=list(files)))
        while not task.done():
            await asyncio.wait({task}, timeout=1.0)
            done = sum(f.stat().st_size for f in blobs.glob("*") if f.is_file()) if blobs.exists() else 0
            yield {"status": f"downloading {repo_id}", "completed": min(done, total - 1) if total else 0, "total": total}
        task.result()  # re-raise download errors
        yield {"status": "success", "completed": total, "total": total}

    async def delete(self, repo_id: str) -> None:
        """Delete every cached revision of a repo."""

        def _delete() -> None:
            from huggingface_hub import scan_cache_dir  # noqa: PLC0415

            cache = scan_cache_dir()
            hashes = [rev.commit_hash for repo in cache.repos if repo.repo_id == repo_id for rev in repo.revisions]
            if not hashes:
                raise FileNotFoundError(f"{repo_id} is not downloaded")
            cache.delete_revisions(*hashes).execute()

        await asyncio.to_thread(_delete)

    @staticmethod
    def native_context_length(repo_id: str) -> int | None:
        """Read ``max_position_embeddings`` from the cached ``config.json`` if available."""
        from huggingface_hub import try_to_load_from_cache  # noqa: PLC0415

        path = try_to_load_from_cache(repo_id, "config.json")
        if not isinstance(path, str):
            return None
        config = json.loads(Path(path).read_text())
        for source in (config, config.get("text_config", {})):
            value = source.get("max_position_embeddings")
            if isinstance(value, int):
                return value
        return None


@dataclass
class _Server:
    model: str
    port: int
    process: asyncio.subprocess.Process
    log_path: Path
    inflight: int = 0
    idle: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def alive(self) -> bool:
        return self.process.returncode is None


class VLLMServerPool:
    """Start, reuse and swap one ``vllm serve`` process per GPU."""

    def __init__(  # noqa: PLR0913
        self,
        gpus: list[int],
        command: list[str],
        base_port: int = 8100,
        extra_args: list[str] | None = None,
        gpu_memory_utilization: float = 0.80,
        startup_timeout: float = 1200.0,
        log_dir: Path = Path("logs"),
        context_length: Callable[[str], int] | None = None,
    ) -> None:
        """Configure the pool; no process is started until a review needs one."""
        self.gpus = gpus
        self.command = command
        self.base_port = base_port
        self.extra_args = extra_args or []
        self.gpu_memory_utilization = gpu_memory_utilization
        self.startup_timeout = startup_timeout
        self.log_dir = log_dir
        self.context_length = context_length or (lambda _model: 32768)
        self._servers: dict[int, _Server] = {}
        self._locks: dict[int, asyncio.Lock] = {gpu: asyncio.Lock() for gpu in gpus}

    def pick_gpu(self, model: str) -> int:
        """Prefer a GPU already serving the model, then an empty GPU, then the least busy one."""
        serving = [g for g, s in self._servers.items() if s.model == model and s.alive]
        if serving:
            return min(serving, key=lambda g: self._servers[g].inflight)
        empty = [g for g in self.gpus if g not in self._servers or not self._servers[g].alive]
        if empty:
            return empty[0]
        return min(self.gpus, key=lambda g: self._servers[g].inflight)

    @asynccontextmanager
    async def lease(self, slot: int, model: str, on_status: Callable[[str], Awaitable[None]] | None = None) -> AsyncIterator[str]:
        """Yield the base URL of a server running ``model``, starting or swapping one if needed."""
        gpu = self.pick_gpu(model) if slot == AUTO_SLOT else slot - 1
        if gpu not in self._locks:
            raise ValueError(f"GPU {gpu} is not managed by Sibyl (configured GPUs: {self.gpus})")

        async def status(message: str) -> None:
            logger.info("[vLLM gpu %s] %s", gpu, message)
            if on_status:
                await on_status(message)

        async with self._locks[gpu]:
            server = self._servers.get(gpu)
            if server is not None and (server.model != model or not server.alive):
                if server.inflight and server.alive:
                    await status(f"Waiting for {server.model} to finish on GPU {gpu}...")
                    await server.idle.wait()
                await self._stop(gpu)
                server = None
            if server is None:
                server = await self._start(gpu, model, status)
            server.inflight += 1
            server.idle.clear()
        try:
            yield f"http://127.0.0.1:{server.port}/v1"
        finally:
            server.inflight -= 1
            if server.inflight == 0:
                server.idle.set()

    async def _start(self, gpu: int, model: str, status: Callable[[str], Awaitable[None]]) -> _Server:
        port = self.base_port + gpu
        args = [
            *self.command,
            "serve",
            model,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--served-model-name",
            model,
            "--max-model-len",
            str(self.context_length(model)),
            "--gpu-memory-utilization",
            str(self.gpu_memory_utilization),
            *self.extra_args,
        ]
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"vllm-gpu{gpu}.log"
        await status(f"Starting vLLM for {model} on GPU {gpu}...")
        with log_path.open("wb") as log:  # only the latest run: servers restart for every review after an idle period
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=log,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu)},
                start_new_session=True,  # lets us stop vLLM's worker processes as a group
            )
        server = _Server(model=model, port=port, process=process, log_path=log_path)
        server.idle.set()
        self._servers[gpu] = server

        started = time.monotonic()
        last_report = started
        async with httpx.AsyncClient(timeout=5.0) as client:
            while True:
                if not server.alive:
                    self._servers.pop(gpu, None)
                    tail = log_path.read_text(errors="replace")[-2000:]
                    raise RuntimeError(f"vLLM exited while loading {model} (see {log_path}):\n{tail}")
                with contextlib.suppress(httpx.HTTPError):
                    if (await client.get(f"http://127.0.0.1:{port}/health")).status_code == 200:  # noqa: PLR2004
                        break
                elapsed = time.monotonic() - started
                if elapsed > self.startup_timeout:
                    await self._stop(gpu)
                    raise TimeoutError(f"vLLM did not become ready for {model} within {self.startup_timeout:.0f}s (see {log_path})")
                if time.monotonic() - last_report > 15:  # noqa: PLR2004
                    await status(f"Loading {model} into GPU {gpu} ({elapsed:.0f}s)...")
                    last_report = time.monotonic()
                await asyncio.sleep(2)
        await status(f"{model} is ready on GPU {gpu}")
        return server

    async def _stop(self, gpu: int) -> None:
        server = self._servers.pop(gpu, None)
        if server is None or not server.alive:
            return
        logger.info("Stopping vLLM server for %s on GPU %s", server.model, gpu)
        with contextlib.suppress(ProcessLookupError):
            os.killpg(server.process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(server.process.wait(), timeout=60)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(server.process.pid, signal.SIGKILL)
            await server.process.wait()

    async def stop_model(self, model: str) -> None:
        """Stop every server running ``model`` (e.g. before deleting it)."""
        for gpu in [g for g, s in self._servers.items() if s.model == model]:
            async with self._locks[gpu]:
                server = self._servers.get(gpu)
                if server and server.model == model:
                    await server.idle.wait()
                    await self._stop(gpu)

    async def shutdown(self) -> None:
        """Stop all servers."""
        for gpu in list(self._servers):
            await self._stop(gpu)

    def status(self) -> list[dict[str, Any]]:
        """Describe running servers."""
        return [{"gpu": g, "model": s.model, "port": s.port, "inflight": s.inflight, "alive": s.alive} for g, s in sorted(self._servers.items())]


def _gpus_from_env() -> list[int]:
    configured = [int(g) for g in os.getenv("SIBYL_VLLM_GPUS", "").split(",") if g.strip()]
    return configured or list(range(nvidia_gpu_count())) or [0]


class VLLMEngine(InferenceEngine):
    """Download models from Hugging Face and serve them with vLLM on demand."""

    name = "vllm"
    label = "vLLM (Hugging Face models)"
    supports_downloads = True

    def __init__(self, store: HuggingFaceStore | None = None, pool: VLLMServerPool | None = None, max_context: int | None = None) -> None:
        """Configure from ``SIBYL_VLLM_*`` environment variables unless components are injected."""
        self.store = store or HuggingFaceStore()
        self.max_context: int | None = max_context if max_context is not None else max_context_setting()
        """Cap on the context window; ``None`` (``SIBYL_MAX_CONTEXT=model``) uses each model's full limit."""
        self.pool = pool or VLLMServerPool(
            gpus=_gpus_from_env(),
            command=shlex.split(os.getenv("SIBYL_VLLM_COMMAND", "vllm")),
            base_port=env_int("SIBYL_VLLM_BASE_PORT", 8100),
            extra_args=shlex.split(os.getenv("SIBYL_VLLM_EXTRA_ARGS", "")),
            gpu_memory_utilization=env_float("SIBYL_VLLM_GPU_MEMORY_UTILIZATION", 0.80),
            startup_timeout=env_float("SIBYL_VLLM_STARTUP_TIMEOUT", 1200.0),
            context_length=self.context_length,
        )
        self.timeout = env_float("SIBYL_REQUEST_TIMEOUT", 1800.0)

    def context_length(self, model: str) -> int:
        """Context window used for ``model``: the configured maximum capped by the model's native limit, or that limit for ``model``."""
        native = None
        with contextlib.suppress(Exception):
            native = self.store.native_context_length(model)
        return cap_context(native, self.max_context)

    def info(self) -> dict[str, Any]:  # noqa: D102
        return {**super().info(), "gpus": self.pool.gpus, "servers": self.pool.status()}

    def review_gpus(self) -> list[int]:  # noqa: D102
        return list(self.pool.gpus)

    async def list_installed(self) -> list[dict[str, Any]]:  # noqa: D102
        return await self.store.list_installed()

    async def list_catalog(self) -> list[dict[str, Any]]:  # noqa: D102
        installed = {m["model"] for m in await self.store.list_installed()}
        return await self.store.list_catalog(installed)

    async def list_variants(self, name: str) -> list[str]:  # noqa: ARG002, D102
        return []  # each Hugging Face repo is a single variant

    def pull(self, model: str) -> AsyncIterator[dict[str, Any]]:  # noqa: D102
        return self.store.pull(model)

    async def delete(self, model: str) -> None:  # noqa: D102
        await self.pool.stop_model(model)
        await self.store.delete(model)

    async def generate_json(self, request: GenerationRequest) -> str:  # noqa: D102
        async with self.pool.lease(request.slot, request.model, request.on_status) as base_url:
            if request.on_status and not request.images:
                await request.on_status(f"Generating review with {request.model}...")
            return await chat_json(base_url, request, timeout=self.timeout)

    async def release_gpus(self) -> None:  # noqa: D102
        await self.pool.shutdown()

    async def aclose(self) -> None:  # noqa: D102
        await self.pool.shutdown()
