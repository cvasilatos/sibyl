"""Response models must keep every field their producers return.

FastAPI drops fields a response model doesn't declare, so a field added to a producer but not to its model would
silently vanish from the API. Each test feeds a producer's output through its model and checks nothing was lost.
"""

from typing import cast

from pydantic import BaseModel

from sibyl.schemas.conferences import ConferenceDetail, ConferenceList
from sibyl.schemas.engines import AvailableModels, EngineInfo, InstalledModels
from sibyl.schemas.gpu import GpuList
from sibyl.schemas.review_config import ReviewConfig, ReviewDetail, ReviewMode
from sibyl.schemas.reviews import FullReview, ReviewStatistics
from sibyl.services.conferences import get_conference, list_conferences


def assert_keeps_fields(model: type[BaseModel], data: dict[str, object]) -> None:
    """Validate data through the model and fail if any key, at any depth, is missing from the dump."""
    dumped = model.model_validate(data).model_dump()

    def walk(src: object, out: object, path: str) -> None:
        if isinstance(src, dict):
            assert isinstance(out, dict), path
            src_d = cast("dict[str, object]", src)
            out_d = cast("dict[str, object]", out)
            missing = set(src_d) - set(out_d)
            assert not missing, f"{model.__name__} drops {sorted(missing)} at {path or 'top level'}"
            for key, value in src_d.items():
                walk(value, out_d[key], f"{path}.{key}")
        elif isinstance(src, list):
            assert isinstance(out, list), path
            for i, (a, b) in enumerate(zip(src, out, strict=True)):
                walk(a, b, f"{path}[{i}]")

    walk(data, dumped, "")


def test_conference_list_keeps_fields() -> None:
    """Conference summaries keep every field."""
    items = list_conferences()
    assert items
    assert_keeps_fields(ConferenceList, {"conferences": items, "count": len(items)})


def test_conference_detail_keeps_fields() -> None:
    """A full conference template keeps every field."""
    template = get_conference(list_conferences()[0]["id"])
    assert template is not None
    assert_keeps_fields(ConferenceDetail, template.model_dump() | {"form_markdown": template.prompt_text()})


def test_engine_info_keeps_vllm_fields() -> None:
    """The extra gpus and servers fields from vLLM survive."""
    info = {"name": "vllm", "label": "vLLM", "supports_downloads": True, "platform": "linux", "machine": "x86_64"}
    servers = [{"gpu": 0, "model": "Qwen/Qwen3-8B", "port": 8100, "inflight": 1, "alive": True}]
    assert_keeps_fields(EngineInfo, info | {"gpus": [0, 1], "servers": servers})


def test_model_lists_keep_fields() -> None:
    """Installed and catalog model listings keep every field."""
    installed = {"model": "qwen3:8b", "size": 5, "modified_at": "2026-01-01T00:00:00", "digest": "abc"}
    assert_keeps_fields(InstalledModels, {"models": [installed], "count": 1})
    available = {"name": "qwen3", "description": "d", "size": "Unknown", "installed": False, "installed_variants": ["8b"]}
    assert_keeps_fields(AvailableModels, {"models": [available], "count": 1})


def test_gpu_list_keeps_fields() -> None:
    """GPU stats keep every field, with or without GPUs."""
    process = {"pid": 1, "memory_bytes": 10, "type": "compute", "name": "python"}
    gpu = {
        "index": 0,
        "name": "RTX",
        "gpu_utilization": 50,
        "memory_utilization": 20,
        "memory_used": 1,
        "memory_total": 2,
        "memory_free": 1,
        "temperature": 60,
        "power_usage_watts": 100.5,
        "power_limit_watts": 300.0,
        "fan_speed_percent": 30,
        "processes": [process],
    }
    assert_keeps_fields(GpuList, {"gpus": [gpu], "count": 1, "available": True, "vendor": "nvidia"})
    assert_keeps_fields(GpuList, {"gpus": [], "count": 0, "available": False, "vendor": None})


def test_full_review_keeps_fields() -> None:
    """A stored review keeps all criteria, including conference answers."""
    criteria = {
        "novelty": "n",
        "methodology": "m",
        "results": "r",
        "clarity": "c",
        "impact": "i",
        "limitations": "l",
        "strengths": "s",
        "score": 4,
        "recommendation": "Accept",
        "detailed_feedback": "f",
        "review_form_response": None,
        "conference": "neurips",
        "review_form_answers": {"soundness": 3, "summary": "ok"},
    }
    review = {
        "id": "1",
        "paper_title": "P",
        "pdf_filename": "p.pdf",
        "pdf_path": None,
        "reviewer_model": "qwen3:8b",
        "score": 4,
        "recommendation": "Accept",
        "created_at": "2026-01-01",
        "criteria": criteria,
        "raw_response": "{}",
        "related_work": [{"ref": "R1", "title": "T", "authors": ["A"], "year": 2024, "url": "https://arxiv.org/abs/2401.00001", "abstract": "a", "relation": "close"}],
        "config": ReviewConfig(engine="ollama", model="qwen3:8b", detail=ReviewDetail.STANDARD, mode=ReviewMode.SINGLE, temperature=0.7, context_length=32768).model_dump(
            mode="json"
        ),
    }
    assert_keeps_fields(FullReview, review)


def test_old_review_without_newer_criteria_still_loads() -> None:
    """Reviews stored before newer criteria fields existed still validate."""
    review = FullReview.model_validate(
        {
            "id": "1",
            "paper_title": "P",
            "pdf_filename": "p.pdf",
            "pdf_path": None,
            "reviewer_model": "m",
            "score": 3,
            "recommendation": "Reject",
            "created_at": "2025-01-01",
            "criteria": {"score": 3, "recommendation": "Reject"},
            "raw_response": "",
        }
    )
    assert review.criteria.conference is None


def test_statistics_keep_fields() -> None:
    """Review statistics keep every field."""
    stats = {"total_reviews": 2, "unique_papers": 1, "unique_models": 2, "recommendations": {"Accept": 2}}
    assert_keeps_fields(ReviewStatistics, stats)


def test_saved_form_models_keep_fields(tmp_path, monkeypatch) -> None:
    """Saved review forms keep every field in listings and in detail."""
    from sibyl import config
    from sibyl.schemas.review_forms import SavedFormDetail, SavedFormList
    from sibyl.services.review_forms import save_form

    monkeypatch.setattr(config, "STORAGE_PATH", tmp_path)
    form = save_form("Workshop", "form.md", "# Q1")
    assert_keeps_fields(SavedFormList, {"forms": [form.summary()], "count": 1})
    assert_keeps_fields(SavedFormDetail, form.model_dump())
