"""Tests for inference engines, context budgeting and hardware helpers."""

import asyncio
import contextlib
import json
import socket
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from sibyl.inference import AUTO_SLOT, GenerationRequest, create_engine
from sibyl.inference.base import estimate_tokens
from sibyl.inference.ollama_engine import MIN_OUTPUT_TOKENS, OllamaEngine, output_room
from sibyl.inference.ollama_gpus import pick_gpu
from sibyl.inference.openai_engine import OpenAICompatibleEngine, chat_json
from sibyl.inference.vllm_engine import VLLMEngine, VLLMServerPool, select_download_files
from sibyl.services import hardware
from sibyl.services.reviewer import fit_paper, strip_reasoning

FAKE_VLLM = [sys.executable, str(Path(__file__).with_name("fake_vllm.py"))]


def _request(**overrides: Any) -> GenerationRequest:
    values: dict[str, Any] = {"model": "m", "system": "s", "prompt": "p", "schema": {"type": "object"}, "temperature": 0.2, "context_length": 8192}
    return GenerationRequest(**(values | overrides))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# --- engine factory -------------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "cls"), [("ollama", OllamaEngine), ("vllm", VLLMEngine), ("openai", OpenAICompatibleEngine)])
def test_create_engine(name, cls):
    assert isinstance(create_engine(name), cls)


def test_create_engine_defaults_to_ollama(monkeypatch):
    monkeypatch.delenv("SIBYL_ENGINE", raising=False)
    assert isinstance(create_engine(), OllamaEngine)


def test_create_engine_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown SIBYL_ENGINE"):
        create_engine("tgi")


# --- context budgeting ----------------------------------------------------------------------------


def test_output_room_is_the_rest_of_the_context():
    request = _request(system="s" * 300, prompt="p" * 2700, context_length=8192)
    assert output_room(request) == 8192 - estimate_tokens("s" * 300 + "p" * 2700)
    assert output_room(_request(prompt="p" * 30_000, context_length=8192)) == MIN_OUTPUT_TOKENS


def test_ollama_lets_the_model_write_until_the_context_is_full():
    engine = OllamaEngine(hosts=["http://a:1"])
    client = AsyncMock()
    client.chat = AsyncMock(return_value=MagicMock(message=MagicMock(content="{}")))
    engine.clients = [client]

    asyncio.run(engine.generate_json(_request(context_length=16384)))
    assert client.chat.await_args is not None
    assert client.chat.await_args.kwargs["options"]["num_predict"] == output_room(_request(context_length=16384))

    asyncio.run(engine.generate_json(_request(max_tokens=100)))
    assert client.chat.await_args.kwargs["options"]["num_predict"] == 100


@pytest.mark.parametrize(("max_tokens", "expected"), [(None, None), (512, 512)])
def test_openai_payload_omits_max_tokens_unless_set(monkeypatch, max_tokens, expected):
    sent: dict[str, Any] = {}

    async def post(_self, _url, json):
        sent.update(json)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert asyncio.run(chat_json("http://server/v1", _request(max_tokens=max_tokens))) == "{}"
    assert sent.get("max_tokens") == expected


def test_fit_paper_trims_tail_only_when_needed():
    text = "a" * 300
    assert fit_paper(text, 1000) == (text, False)
    trimmed, truncated = fit_paper(text, 10)
    assert truncated
    assert trimmed.startswith("a" * 30)
    assert "truncated" in trimmed


def test_strip_reasoning_removes_think_block():
    assert strip_reasoning('<think>\nhmm\n</think>\n{"a": 1}') == '{"a": 1}'
    assert strip_reasoning('{"a": 1}') == '{"a": 1}'


# --- Ollama ---------------------------------------------------------------------------------------


def test_ollama_slot_mapping():
    engine = OllamaEngine(hosts=["http://a:1", "http://b:1"])
    assert engine.client_for_slot(AUTO_SLOT) is engine.clients[0]
    assert engine.client_for_slot(2) is engine.clients[1]
    assert engine.client_for_slot(5) is engine.clients[0]  # out of range falls back


def test_ollama_hosts_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOSTS", "http://ollama-0:11434, http://ollama-1:11434")
    assert OllamaEngine().hosts == ["http://ollama-0:11434", "http://ollama-1:11434"]
    monkeypatch.delenv("OLLAMA_HOSTS")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:9999")
    assert OllamaEngine().hosts == ["http://localhost:9999"]


def test_ollama_generate_sets_context_length():
    engine = OllamaEngine(hosts=["http://a:1"], keep_alive="5m")
    client = AsyncMock()
    client.chat = AsyncMock(return_value=MagicMock(message=MagicMock(content="{}")))
    engine.clients = [client]

    assert asyncio.run(engine.generate_json(_request(context_length=20480))) == "{}"
    assert client.chat.await_args is not None
    kwargs = client.chat.await_args.kwargs
    assert kwargs["options"]["num_ctx"] == 20480
    assert kwargs["format"] == {"type": "object"}
    assert kwargs["keep_alive"] == "5m"


@pytest.mark.parametrize(
    ("show", "expected"),
    [
        (MagicMock(modelinfo={"general.architecture": "llama", "llama.context_length": 8192}), 8192),  # model limit is lower
        (MagicMock(modelinfo={"qwen3.context_length": 131072}), 32768),  # SIBYL_MAX_CONTEXT is lower
        (MagicMock(modelinfo=None), 32768),  # limit unknown
        (RuntimeError("model not found"), 32768),
    ],
)
def test_ollama_caps_the_context_at_the_model_limit(monkeypatch, show, expected):
    monkeypatch.setenv("SIBYL_MAX_CONTEXT", "32768")
    engine = OllamaEngine(hosts=["http://a:1"])
    client = AsyncMock()
    client.show = AsyncMock(side_effect=show) if isinstance(show, Exception) else AsyncMock(return_value=show)
    engine.clients = [client]

    assert asyncio.run(engine.context_window("m")) == expected
    assert asyncio.run(engine.context_window("m")) == expected
    assert client.show.await_count == 1  # asked once per model


# --- vLLM / Hugging Face --------------------------------------------------------------------------


def test_select_download_files_prefers_safetensors():
    files = {
        "config.json": 1,
        "tokenizer.json": 2,
        "tokenizer_config.json": 1,
        "model-00001-of-00002.safetensors": 100,
        "model.safetensors.index.json": 1,
        "pytorch_model.bin": 100,
        "original/consolidated.pth": 100,
        "model.gguf": 50,
        "README.md": 1,
    }
    assert set(select_download_files(files)) == {
        "config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "model-00001-of-00002.safetensors",
        "model.safetensors.index.json",
    }


def test_select_download_files_falls_back_to_bin():
    assert "pytorch_model.bin" in select_download_files({"config.json": 1, "pytorch_model.bin": 10})


@pytest.mark.parametrize(
    ("setting", "native", "expected"),
    [
        ("", 131072, 32768),  # unset: the 32k default cap
        ("65536", 131072, 65536),
        ("65536", 8192, 8192),
        ("model", 131072, 131072),  # each model's full limit
        ("MODEL", None, 32768),  # limit unknown: the default
    ],
)
def test_max_context_setting(monkeypatch, setting, native, expected):
    from sibyl.inference.base import cap_context, max_context_setting

    monkeypatch.setenv("SIBYL_MAX_CONTEXT", setting)
    assert cap_context(native, max_context_setting()) == expected


def test_full_model_context_with_ollama_and_vllm(monkeypatch):
    monkeypatch.setenv("SIBYL_MAX_CONTEXT", "model")
    engine = OllamaEngine(hosts=["http://a:1"])
    client = AsyncMock()
    client.show = AsyncMock(return_value=MagicMock(modelinfo={"llama.context_length": 131072}))
    engine.clients = [client]
    assert asyncio.run(engine.context_window("m")) == 131072

    vllm = VLLMEngine(pool=MagicMock())
    monkeypatch.setattr(vllm.store, "native_context_length", lambda _m: 40960)
    assert vllm.context_length("m") == 40960


def test_vllm_context_length_capped_by_model(monkeypatch):
    engine = VLLMEngine(max_context=32768, pool=MagicMock())
    monkeypatch.setattr(engine.store, "native_context_length", lambda _m: 8192)
    assert engine.context_length("small/model") == 8192
    monkeypatch.setattr(engine.store, "native_context_length", lambda _m: None)
    assert engine.context_length("unknown/model") == 32768


def _pool(tmp_path, gpus=(0, 1)) -> VLLMServerPool:
    base = _free_port()
    # Make sure base + gpu is also free for the second GPU.
    return VLLMServerPool(gpus=list(gpus), command=FAKE_VLLM, base_port=base, startup_timeout=30, log_dir=tmp_path, context_length=lambda _m: 4096)


def test_vllm_pool_starts_reuses_and_swaps(tmp_path):
    async def scenario():
        pool = _pool(tmp_path)
        engine = VLLMEngine(pool=pool, max_context=4096)
        try:
            statuses: list[str] = []

            async def on_status(message: str) -> None:
                statuses.append(message)

            first = json.loads(await engine.generate_json(_request(model="org/a", slot=1, on_status=on_status)))
            assert first == {"served_model": "org/a", "requested_model": "org/a", "has_schema": True}
            assert any("Starting vLLM" in s for s in statuses)
            pid = pool._servers[0].process.pid

            # Same model on the same GPU reuses the running server.
            await engine.generate_json(_request(model="org/a", slot=1))
            assert pool._servers[0].process.pid == pid

            # Auto slot prefers the GPU that already serves the model.
            assert pool.pick_gpu("org/a") == 0
            # A different model in auto mode goes to the empty GPU.
            assert pool.pick_gpu("org/b") == 1

            # A different model on the same GPU swaps the server.
            swapped = json.loads(await engine.generate_json(_request(model="org/b", slot=1)))
            assert swapped["served_model"] == "org/b"
            assert pool._servers[0].process.pid != pid
            assert [s["model"] for s in pool.status()] == ["org/b"]
        finally:
            await pool.shutdown()
        assert pool.status() == []

    asyncio.run(scenario())


def test_vllm_pool_reports_startup_failure(tmp_path):
    async def scenario():
        pool = _pool(tmp_path, gpus=(0,))
        with pytest.raises(RuntimeError, match="simulated load failure"):
            async with pool.lease(1, "crash/model"):
                pass
        assert pool.status() == []

    asyncio.run(scenario())


def test_vllm_pool_rejects_unmanaged_gpu(tmp_path):
    async def scenario():
        async with _pool(tmp_path, gpus=(0,)).lease(4, "org/a"):
            pass

    with pytest.raises(ValueError, match="not managed"):
        asyncio.run(scenario())


def test_openai_engine_cannot_download():
    engine = OpenAICompatibleEngine(base_url="http://localhost:1/v1")

    async def pull():
        async for _ in engine.pull("x"):
            pass

    with pytest.raises(Exception, match="cannot manage"):
        asyncio.run(pull())
    assert engine.info()["supports_downloads"] is False


# --- hardware -------------------------------------------------------------------------------------


def test_parse_ioreg_performance():
    sample = '"PerformanceStatistics" = {"Tiler Utilization %"=3,"Device Utilization %"=42,"In use system memory"=3217571840}'
    assert hardware.parse_ioreg_performance(sample) == {"Device Utilization %": 42, "In use system memory": 3217571840}


def test_torch_device_matches_platform():
    import torch

    device = hardware.torch_device(0)
    if torch.cuda.is_available():
        assert device.startswith("cuda:")
    elif torch.backends.mps.is_available():
        assert device == "mps"
    else:
        assert device == "cpu"


@pytest.mark.skipif(not hardware.IS_MACOS, reason="Apple Silicon only")
def test_apple_gpu_listed_on_macos():
    data = hardware.list_gpus()
    assert data["available"] is True
    assert data["vendor"] == "apple"
    assert data["gpus"][0]["memory_total"] > 0


# --- Per-GPU Ollama servers -----------------------------------------------------------------------


def _gpu(index, free_gib, util):
    return {"index": index, "memory_free": free_gib * 2**30, "gpu_utilization": util}


def test_pick_gpu_prefers_idle_gpu_with_room():
    gpus = [_gpu(0, 120, 100), _gpu(1, 100, 0), _gpu(2, 120, 93), _gpu(3, 139, 0)]
    assert pick_gpu(gpus, 30 * 2**30, {}) == 3  # idle and most free memory
    assert pick_gpu(gpus, 30 * 2**30, {3: 1}) == 1  # GPU 3 already runs a Sibyl request
    assert pick_gpu(gpus, 130 * 2**30, {}) == 3  # only GPU 3 fits
    assert pick_gpu(gpus, 200 * 2**30, {}) is None  # split across GPUs


class _FakeServers:
    def __init__(self, choice):
        self.gpus = [0, 1, 2, 3]
        self.choice = choice
        self.leased: list[int] = []

    def choose(self, model, need):  # noqa: ARG002
        return self.choice

    @contextlib.asynccontextmanager
    async def lease(self, gpu, model, on_status=None):  # noqa: ARG002
        self.leased.append(gpu)
        yield f"http://127.0.0.1:{11500 + gpu}"


@pytest.mark.parametrize(("slot", "choice", "leased", "main"), [(3, None, [2], False), (AUTO_SLOT, 1, [1], False), (AUTO_SLOT, None, [], True), (9, None, [], True)])
def test_ollama_routes_requests_to_gpu_servers(slot, choice, leased, main):
    servers = _FakeServers(choice)
    engine = OllamaEngine(hosts=["http://a:1"], gpu_servers=servers)  # type: ignore[arg-type]
    engine._model_sizes["m"] = 5 * 2**30

    async def run():
        async with engine.client_for_request(_request(slot=slot)) as client:
            return client

    client = asyncio.run(run())
    assert servers.leased == leased
    assert (client is engine.admin) == main


def test_ollama_engine_with_explicit_hosts_does_not_start_gpu_servers():
    assert OllamaEngine(hosts=["http://a:1"]).gpu_servers is None


def test_ollama_release_stops_gpu_servers_and_unloads_only_models_sibyl_ran():
    servers = _FakeServers(None)
    servers.shutdown = AsyncMock()  # type: ignore[attr-defined]
    engine = OllamaEngine(hosts=["http://a:1"], gpu_servers=servers)  # type: ignore[arg-type]
    engine._model_sizes["big"] = 5 * 2**30
    admin = MagicMock()
    admin.ps = AsyncMock(return_value=MagicMock(models=[MagicMock(model="big"), MagicMock(model="someone-elses")]))
    admin.chat = AsyncMock()
    engine.clients = [admin]

    async def run():
        async with engine.client_for_request(_request(model="big", slot=AUTO_SLOT)):  # too big for one GPU: main server
            pass
        await engine.release_gpus()
        await engine.release_gpus()  # nothing left to unload

    asyncio.run(run())
    assert servers.shutdown.await_count == 2  # type: ignore[attr-defined]
    admin.chat.assert_awaited_once_with(model="big", messages=[], keep_alive=0)


def test_vllm_release_stops_its_servers():
    pool = MagicMock(shutdown=AsyncMock())
    asyncio.run(VLLMEngine(store=MagicMock(), pool=pool).release_gpus())
    pool.shutdown.assert_awaited_once()
