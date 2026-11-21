"""Tests for inference engines, context budgeting and hardware helpers."""

import asyncio
import json
import socket
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sibyl.inference import AUTO_SLOT, GenerationRequest, create_engine
from sibyl.inference.ollama_engine import OllamaEngine
from sibyl.inference.openai_engine import OpenAICompatibleEngine
from sibyl.inference.vllm_engine import VLLMEngine, VLLMServerPool, select_download_files
from sibyl.services import hardware
from sibyl.services.reviewer import CONTEXT_STEP, MIN_CONTEXT, context_window, fit_paper, strip_reasoning

FAKE_VLLM = [sys.executable, str(Path(__file__).with_name("fake_vllm.py"))]


def _request(**overrides: Any) -> GenerationRequest:
    values: dict[str, Any] = {"model": "m", "system": "s", "prompt": "p", "schema": {"type": "object"}, "temperature": 0.2, "max_tokens": 100, "context_length": 8192}
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


def test_context_window_rounds_up_and_caps():
    assert context_window(10_000, 4_000, 32_768) == 14_336
    assert context_window(10_000, 4_000, 32_768) % CONTEXT_STEP == 0
    assert context_window(100, 100, 32_768) == MIN_CONTEXT
    assert context_window(100_000, 4_000, 32_768) == 32_768


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
    client.generate = AsyncMock(return_value=MagicMock(response="{}"))
    engine.clients = [client]

    assert asyncio.run(engine.generate_json(_request(context_length=20480))) == "{}"
    assert client.generate.await_args is not None
    kwargs = client.generate.await_args.kwargs
    assert kwargs["options"]["num_ctx"] == 20480
    assert kwargs["format"] == {"type": "object"}
    assert kwargs["keep_alive"] == "5m"


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
