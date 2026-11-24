"""Tests for VLM figure descriptions."""

import asyncio
import base64
import io
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from PIL import Image

from sibyl.inference import GenerationRequest
from sibyl.inference.ollama_engine import KEEP_LOADED, OllamaEngine
from sibyl.inference.openai_engine import chat_json
from sibyl.services import figures
from sibyl.services.figures import NOT_SHOWN, FigureDescriber, find_caption, find_figures, prefetch_vlm, vlm_model_for

MARKDOWN = """# Paper

Intro text.

![](_page_0_Figure_1.jpeg)

Figure 1: Accuracy versus training steps.

![](_page_0_Picture_2.jpeg)

More text.

![](_page_2_Figure_3.jpeg)

The end.
"""


def _image(size: tuple[int, int] = (400, 300)) -> Image.Image:
    return Image.new("RGB", size, "white")


def _images() -> dict[str, Image.Image]:
    return {"_page_0_Figure_1.jpeg": _image(), "_page_0_Picture_2.jpeg": _image((32, 32)), "_page_2_Figure_3.jpeg": _image((3000, 1500))}


class FakeEngine:
    """Records requests and returns a fixed figure description."""

    name = "ollama"
    supports_downloads = True

    def __init__(self, installed: list[str] | None = None, fail_on: int | None = None) -> None:
        self.installed = installed if installed is not None else ["qwen2.5vl:7b"]
        self.requests: list[GenerationRequest] = []
        self.pulled: list[str] = []
        self.fail_on = fail_on

    async def list_installed(self) -> list[dict[str, Any]]:
        return [{"model": m} for m in self.installed]

    async def pull(self, model: str):
        self.pulled.append(model)
        yield {"status": "downloading", "completed": 50, "total": 100}
        yield {"status": "success", "completed": 100, "total": 100}

    async def generate_json(self, request: GenerationRequest) -> str:
        self.requests.append(request)
        if self.fail_on == len(self.requests):
            raise RuntimeError("boom")
        return "<think>hmm</think>" + json.dumps({"description": f"A line plot ({len(self.requests)}).", "issues": ["Axis labels are tiny"]})


def test_vlm_model_for(monkeypatch):
    monkeypatch.delenv("SIBYL_VLM_MODEL", raising=False)
    assert vlm_model_for("ollama") == "qwen2.5vl:7b"
    assert vlm_model_for("vllm") == "Qwen/Qwen2.5-VL-7B-Instruct"
    assert vlm_model_for("openai") is None
    monkeypatch.setenv("SIBYL_VLM_MODEL", "gemma3:12b")
    assert vlm_model_for("openai") == "gemma3:12b"
    monkeypatch.setenv("SIBYL_VLM_MODEL", "none")
    assert vlm_model_for("ollama") is None


def test_vlm_model_for_prefers_the_requested_model(monkeypatch):
    monkeypatch.setenv("SIBYL_VLM_MODEL", "gemma3:12b")
    assert vlm_model_for("ollama", "llava:13b") == "llava:13b"
    assert vlm_model_for("ollama", "none") is None
    assert vlm_model_for("ollama", "") == "gemma3:12b"
    assert vlm_model_for("ollama", None) == "gemma3:12b"


def test_find_figures_skips_icons_and_reads_captions():
    found = find_figures(MARKDOWN, _images())
    assert [f.name for f in found] == ["_page_0_Figure_1.jpeg", "_page_2_Figure_3.jpeg"]
    assert found[0].page == 1
    assert found[0].caption == "Figure 1: Accuracy versus training steps."
    assert found[1].page == 3
    assert found[1].caption is None


def test_find_caption_before_placeholder():
    text = "Table 2: Results on ImageNet.\n\n![](t.jpeg)\n\nBody."
    start = text.index("![")
    assert find_caption(text, start, text.index(")") + 1) == "Table 2: Results on ImageNet."


def test_encode_image_downscales():
    data = base64.b64decode(figures.encode_image(_image((3000, 1500))))
    assert max(Image.open(io.BytesIO(data)).size) == figures.MAX_SIDE


def test_enrich_replaces_placeholders_with_descriptions():
    engine = FakeEngine()
    statuses: list[str] = []

    async def on_status(message: str) -> None:
        statuses.append(message)

    progress: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int) -> None:
        progress.append((done, total))

    describer = FigureDescriber(engine, "qwen2.5vl:7b")  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    text, count = asyncio.run(describer.enrich(MARKDOWN, _images(), slot=2, on_status=on_status, on_progress=on_progress))

    assert count == 2
    assert progress == [(0, 2), (1, 2), (2, 2)]
    assert "![](" not in text
    assert '<figure_description source="vision model qwen2.5vl:7b" page="1">\nA line plot (1).' in text
    assert "- Axis labels are tiny" in text
    assert "_page_0_Picture_2" not in text  # icon removed
    assert [r.keep_loaded for r in engine.requests] == [True, False]
    assert all(r.slot == 2 and len(r.images) == 1 for r in engine.requests)
    assert "Figure 1: Accuracy versus training steps." in engine.requests[0].prompt
    assert "Describing figure 2/2 with qwen2.5vl:7b..." in statuses


def test_enrich_marks_failed_figure_as_not_shown():
    engine = FakeEngine(fail_on=1)
    text, count = asyncio.run(FigureDescriber(engine, "qwen2.5vl:7b").enrich(MARKDOWN, _images()))  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    assert count == 1
    assert text.count(NOT_SHOWN) == 1


def test_enrich_without_vlm_marks_figures_not_shown():
    engine = FakeEngine()
    text, count = asyncio.run(FigureDescriber(engine, None).enrich(MARKDOWN, _images()))  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    assert count == 0
    assert text.count(NOT_SHOWN) == 2
    assert engine.requests == []


def test_enrich_without_figures_does_not_touch_engine():
    engine = MagicMock()
    text, count = asyncio.run(FigureDescriber(engine, "qwen2.5vl:7b").enrich("Just text.", {}))
    assert (text, count) == ("Just text.", 0)
    engine.list_installed.assert_not_called()


def test_enrich_downloads_missing_vlm(monkeypatch):
    monkeypatch.delenv("SIBYL_VLM_AUTO_PULL", raising=False)
    engine = FakeEngine(installed=[])
    _, count = asyncio.run(FigureDescriber(engine, "qwen2.5vl:7b").enrich(MARKDOWN, _images()))  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    assert engine.pulled == ["qwen2.5vl:7b"]
    assert count == 2


def test_enrich_skips_missing_vlm_when_auto_pull_off(monkeypatch):
    monkeypatch.setenv("SIBYL_VLM_AUTO_PULL", "false")
    engine = FakeEngine(installed=[])
    text, count = asyncio.run(FigureDescriber(engine, "qwen2.5vl:7b").enrich(MARKDOWN, _images()))  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    assert engine.pulled == []
    assert count == 0
    assert text.count(NOT_SHOWN) == 2


def test_prefetch_vlm_downloads_missing_model(monkeypatch):
    monkeypatch.delenv("SIBYL_VLM_MODEL", raising=False)
    monkeypatch.delenv("SIBYL_VLM_AUTO_PULL", raising=False)
    engine = FakeEngine(installed=[])
    assert asyncio.run(prefetch_vlm(engine)) is True  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    assert engine.pulled == ["qwen2.5vl:7b"]


def test_prefetch_vlm_skips_installed_or_disabled(monkeypatch):
    monkeypatch.delenv("SIBYL_VLM_MODEL", raising=False)
    engine = FakeEngine()
    assert asyncio.run(prefetch_vlm(engine)) is True  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    monkeypatch.setenv("SIBYL_VLM_MODEL", "none")
    assert asyncio.run(prefetch_vlm(FakeEngine(installed=[]))) is False  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    assert engine.pulled == []


def test_concurrent_ensure_model_pulls_once(monkeypatch):
    monkeypatch.delenv("SIBYL_VLM_AUTO_PULL", raising=False)
    engine = FakeEngine(installed=[])
    original_pull = engine.pull

    async def pull_and_install(model: str):
        async for part in original_pull(model):
            await asyncio.sleep(0)
            yield part
        engine.installed.append(model)

    engine.pull = pull_and_install  # ty: ignore[invalid-assignment]  # patch the fake to record the install

    async def both() -> list[bool]:
        describer = FigureDescriber(engine, "qwen2.5vl:7b")  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
        return list(await asyncio.gather(describer.ensure_model("qwen2.5vl:7b"), describer.ensure_model("qwen2.5vl:7b")))

    assert asyncio.run(both()) == [True, True]
    assert engine.pulled == ["qwen2.5vl:7b"]


def test_ollama_sends_images_and_keeps_model_loaded():
    engine = OllamaEngine(hosts=["http://a:1"], keep_alive="0")
    client = AsyncMock()
    client.chat = AsyncMock(return_value=MagicMock(message=MagicMock(content="{}")))
    engine.clients = [client]
    request = GenerationRequest(model="v", system="s", prompt="p", schema={}, temperature=0, max_tokens=10, context_length=8192, images=["abc"], keep_loaded=True)
    asyncio.run(engine.generate_json(request))
    assert client.chat.await_args is not None
    kwargs = client.chat.await_args.kwargs
    assert kwargs["messages"][1]["images"] == ["abc"]
    assert kwargs["keep_alive"] == KEEP_LOADED


@pytest.mark.parametrize("images", [[], ["abc"]])
def test_chat_json_image_parts(monkeypatch, images):
    sent: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    request = GenerationRequest(model="v", system="s", prompt="p", schema={}, temperature=0, max_tokens=10, context_length=8192, images=images)
    assert asyncio.run(chat_json("http://x/v1", request)) == "{}"
    content = sent["messages"][1]["content"]
    if images:
        assert content == [{"type": "text", "text": "p"}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}}]
    else:
        assert content == "p"
