"""Per-GPU Ollama servers, so a review runs on the GPU the user picked (or the least busy one).

One ``ollama serve`` can see every GPU, and Ollama has no per-request GPU setting: it puts a model wherever it likes.
When Sibyl talks to a single Ollama server on a multi-GPU NVIDIA machine, it starts one extra ``ollama serve`` per GPU
on demand, each pinned with ``CUDA_VISIBLE_DEVICES`` and reading the same model store. The main server (``OLLAMA_BASE_URL``)
stays in use for downloads, the model list and models too big for any single GPU, which it splits across all of them.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from sibyl.services import hardware

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

logger = logging.getLogger(__name__)

GIB = 1024**3
KV_BYTES_PER_TOKEN = 160 * 1024
"""Rough KV-cache cost per context token (8B models use ~128 KiB at fp16, 70B ~320 KiB)."""
WEIGHT_OVERHEAD = 1.15
"""Weights take a bit more VRAM than the file (compute graph, CUDA context)."""
RECENT_SECONDS = 300
"""A GPU that ran a model this recently is reused for it (Ollama may still hold it there)."""
BUSY_UTILIZATION = 50
"""A GPU above this utilization (percent) is busy: only used when no idle GPU has room."""

MODEL_STORE_CANDIDATES = (Path.home() / ".ollama" / "models", Path("/usr/share/ollama/.ollama/models"), Path("/var/lib/ollama/models"))


def find_model_store() -> Path | None:
    """Ollama's model directory: ``SIBYL_OLLAMA_MODELS``, ``OLLAMA_MODELS`` or the first default that holds manifests."""
    for name in ("SIBYL_OLLAMA_MODELS", "OLLAMA_MODELS"):
        if value := os.getenv(name, "").strip():
            return Path(value).expanduser()
    return next((p for p in MODEL_STORE_CANDIDATES if (p / "manifests").is_dir()), None)


def required_memory(model_size: int, context_length: int) -> int:
    """Estimated VRAM (bytes) to run a model whose file is ``model_size`` bytes with ``context_length`` tokens."""
    return int(model_size * WEIGHT_OVERHEAD) + context_length * KV_BYTES_PER_TOKEN + GIB


def pick_gpu(gpus: list[dict[str, Any]], need: int, inflight: dict[int, int]) -> int | None:
    """Pick the GPU for a model needing ``need`` bytes: one that fits, idle before busy, then least Sibyl work, then most free memory.

    ``None`` means no single GPU has room, so the model should be split across GPUs.
    """
    fitting = [g for g in gpus if g["memory_free"] >= need]
    if not fitting:
        return None
    best = min(
        fitting,
        key=lambda g: (g["gpu_utilization"] > BUSY_UTILIZATION, inflight.get(g["index"], 0), g["gpu_utilization"], -g["memory_free"]),
    )
    return int(best["index"])


@dataclass
class _Server:
    gpu: int
    port: int
    process: asyncio.subprocess.Process

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def alive(self) -> bool:
        return self.process.returncode is None


class OllamaGpuServers:
    """Start one ``ollama serve`` per GPU on demand and route requests to them."""

    def __init__(  # noqa: PLR0913
        self,
        gpus: list[int],
        command: str,
        model_store: Path,
        base_port: int = 11500,
        log_dir: Path = Path("logs"),
        gpu_stats: Callable[[], list[dict[str, Any]]] | None = None,
        startup_timeout: float = 60.0,
    ) -> None:
        """Configure the servers; none is started until a request needs it."""
        self.gpus = gpus
        self.command = command
        self.model_store = model_store
        self.base_port = base_port
        self.log_dir = log_dir
        self.gpu_stats = gpu_stats or (lambda: hardware.list_gpus()["gpus"])
        self.startup_timeout = startup_timeout
        self.inflight: dict[int, int] = {}
        self._servers: dict[int, _Server] = {}
        self._recent: dict[str, tuple[int, float]] = {}
        self._locks = {gpu: asyncio.Lock() for gpu in gpus}

    @classmethod
    def from_env(cls) -> OllamaGpuServers | None:
        """Servers for this machine, or ``None`` when they are off, unneeded (one GPU) or impossible (no binary or store)."""
        if os.getenv("SIBYL_OLLAMA_GPU_SERVERS", "true").strip().lower() in {"0", "false", "no", "off"}:
            return None
        count = hardware.nvidia_gpu_count()
        if count < 2:  # noqa: PLR2004
            return None
        command = shutil.which(os.getenv("SIBYL_OLLAMA_COMMAND", "ollama"))
        store = find_model_store()
        if command is None or store is None:
            logger.warning(
                "%s NVIDIA GPUs but %s: GPU selection is not possible and every review runs where Ollama puts it. Set "
                "SIBYL_OLLAMA_MODELS to Ollama's model directory or use one Ollama server per GPU (OLLAMA_HOSTS).",
                count,
                "no ollama binary on PATH" if command is None else "Ollama's model directory was not found",
            )
            return None
        base_port = int(os.getenv("SIBYL_OLLAMA_BASE_PORT", "11500"))
        logger.info("Per-GPU Ollama servers enabled for %s GPUs (ports %s+, models in %s)", count, base_port, store)
        return cls(gpus=list(range(count)), command=command, model_store=store, base_port=base_port)

    def choose(self, model: str, need: int) -> int | None:
        """GPU for ``model`` needing ``need`` bytes of VRAM, or ``None`` to split it across GPUs on the main server.

        A GPU that recently ran the model (and may still hold it, e.g. between figure descriptions) is reused.
        """
        recent = self._recent.get(model)
        if recent is not None and time.monotonic() - recent[1] < RECENT_SECONDS and self._alive(recent[0]):
            return recent[0]
        try:
            stats = [g for g in self.gpu_stats() if g["index"] in self._locks]
        except Exception:  # monitoring failed: fall back to the main server
            logger.debug("GPU stats unavailable", exc_info=True)
            return None
        return pick_gpu(stats, need, self.inflight)

    def _alive(self, gpu: int) -> bool:
        server = self._servers.get(gpu)
        return server is not None and server.alive

    @contextlib.asynccontextmanager
    async def lease(self, gpu: int, model: str, on_status: Callable[[str], Awaitable[None]] | None = None) -> AsyncIterator[str]:
        """Yield the base URL of ``gpu``'s server for one request, counting it as in flight there."""
        url = await self.url_for(gpu, on_status)
        self.inflight[gpu] = self.inflight.get(gpu, 0) + 1
        try:
            yield url
        finally:
            self.inflight[gpu] -= 1
            self._recent[model] = (gpu, time.monotonic())

    async def url_for(self, gpu: int, on_status: Callable[[str], Awaitable[None]] | None = None) -> str:
        """Return the base URL of the server pinned to ``gpu``, starting it if needed."""
        if gpu not in self._locks:
            raise ValueError(f"GPU {gpu} does not exist (GPUs: {self.gpus})")
        async with self._locks[gpu]:
            server = self._servers.get(gpu)
            if server is None or not server.alive:
                if on_status:
                    await on_status(f"Starting Ollama on GPU {gpu}...")
                server = await self._start(gpu)
            return server.url

    async def _start(self, gpu: int) -> _Server:
        port = self.base_port + gpu
        env = {
            **os.environ,
            "CUDA_VISIBLE_DEVICES": str(gpu),
            "OLLAMA_HOST": f"127.0.0.1:{port}",
            "OLLAMA_MODELS": str(self.model_store),
            "OLLAMA_NOPRUNE": "1",  # never delete blobs from the shared store
        }
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"ollama-gpu{gpu}.log"
        logger.info("Starting Ollama on GPU %s (port %s)", gpu, port)
        with log_path.open("ab") as log:
            process = await asyncio.create_subprocess_exec(self.command, "serve", stdout=log, stderr=asyncio.subprocess.STDOUT, env=env, start_new_session=True)
        server = _Server(gpu=gpu, port=port, process=process)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.startup_timeout
        async with httpx.AsyncClient(timeout=2.0) as client:
            while True:
                if not server.alive:
                    tail = log_path.read_text(errors="replace")[-2000:]
                    raise RuntimeError(f"Ollama exited while starting on GPU {gpu} (see {log_path}):\n{tail}")
                with contextlib.suppress(httpx.HTTPError):
                    if (await client.get(f"{server.url}/api/version")).status_code == 200:  # noqa: PLR2004
                        break
                if loop.time() > deadline:
                    await self._stop(server)
                    raise TimeoutError(f"Ollama did not start on GPU {gpu} within {self.startup_timeout:.0f}s (see {log_path})")
                await asyncio.sleep(0.5)
        self._servers[gpu] = server
        return server

    async def _stop(self, server: _Server) -> None:
        if not server.alive:
            return
        with contextlib.suppress(ProcessLookupError):
            os.killpg(server.process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(server.process.wait(), timeout=20)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(server.process.pid, signal.SIGKILL)
            await server.process.wait()

    async def shutdown(self) -> None:
        """Stop every server this pool started."""
        for gpu in list(self._servers):
            await self._stop(self._servers.pop(gpu))
