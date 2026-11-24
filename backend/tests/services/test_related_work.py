"""Tests for the related-work search (arXiv and Semantic Scholar)."""

import asyncio
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from sibyl.inference import GenerationRequest
from sibyl.schemas.related_work import RelatedPaper
from sibyl.services import related_work
from sibyl.services.related_work import (
    RelatedWorkFinder,
    arxiv_search_query,
    is_same_paper,
    parse_arxiv_feed,
    parse_semantic_scholar,
    parse_sources,
    related_work_enabled,
    render_related_work,
)


def _entry(arxiv_id: str, title: str, year: int = 2023, authors: tuple[str, ...] = ("Ada Lovelace", "Alan Turing")) -> str:
    names = "".join(f"<author><name>{name}</name></author>" for name in authors)
    return (
        f"<entry><id>http://arxiv.org/abs/{arxiv_id}v2</id><title>{title.replace(' ', '\n  ', 1)}</title>"
        f"<published>{year}-03-01T00:00:00Z</published><summary>Abstract of {title}.</summary>{names}</entry>"
    )


def _feed(*entries: str) -> str:
    return f'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{"".join(entries)}</feed>'


FEEDS = {
    "all:sparse AND all:attention": _feed(_entry("2301.00001", "Sparse Attention"), _entry("2301.00002", "Linear Attention")),
    "all:efficient AND all:transformers": _feed(_entry("2301.00002", "Linear Attention"), _entry("2405.12345", "Our Paper Title")),
}


class FakeEngine:
    """Answers the query-writing and selection prompts in turn."""

    name = "ollama"

    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = replies
        self.requests: list[GenerationRequest] = []

    def context_length(self, _model: str) -> int:
        return 32768

    async def context_window(self, model: str) -> int:
        return self.context_length(model)

    async def generate_json(self, request: GenerationRequest) -> str:
        self.requests.append(request)
        reply = self.replies[len(self.requests) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply


def _arxiv_client(calls: list[str], *, fail: bool = False) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        query = parse_qs(urlparse(str(request.url)).query)["search_query"][0]
        calls.append(query)
        if fail:
            return httpx.Response(503)
        feeds = {key.lower(): feed for key, feed in FEEDS.items()}
        return httpx.Response(200, text=feeds.get(query.lower(), _feed()))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def no_throttle(monkeypatch):
    monkeypatch.setattr(related_work, "ARXIV_INTERVAL", 0.0)
    monkeypatch.setattr(related_work, "SEMANTIC_SCHOLAR_INTERVAL", 0.0)
    monkeypatch.setattr(related_work, "SEMANTIC_SCHOLAR_BACKOFF", 0.0)


QUERIES = json.dumps({"queries": ["sparse attention", "Efficient Transformers", "sparse attention"]})


def test_arxiv_search_query_requires_every_keyword():
    assert arxiv_search_query("Sparse attention for the long documents") == "all:Sparse AND all:attention AND all:long AND all:documents"
    assert arxiv_search_query("a AND or the") == ""
    assert arxiv_search_query("one two three four five six seven eight").count("all:") == related_work.MAX_QUERY_TERMS


def test_parse_arxiv_feed():
    papers = parse_arxiv_feed(_feed(_entry("2301.00001", "Sparse Attention", 2021)))
    assert papers == [
        RelatedPaper(
            ref="",
            title="Sparse Attention",
            authors=["Ada Lovelace", "Alan Turing"],
            year=2021,
            url="https://arxiv.org/abs/2301.00001",
            abstract="Abstract of Sparse Attention.",
        )
    ]


def test_parse_arxiv_feed_rejects_entities():
    bomb = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>&a;</title></entry></feed>'
    with pytest.raises(Exception, match="Entit"):
        parse_arxiv_feed(bomb)


def test_is_same_paper():
    assert is_same_paper("Our Paper Title", "our paper-title.")
    assert is_same_paper("Our Paper Titles", "Our Paper Title")
    assert not is_same_paper("Sparse Attention", "Linear Attention")
    assert not is_same_paper("", "")


def test_parse_sources():
    assert parse_sources(None) is None
    assert parse_sources("") == ()
    assert parse_sources(" Semantic_Scholar,bogus,arxiv,arxiv") == ("semantic_scholar", "arxiv")


def test_related_work_enabled(monkeypatch):
    monkeypatch.delenv("SIBYL_RELATED_WORK", raising=False)
    assert related_work_enabled()
    monkeypatch.setenv("SIBYL_RELATED_WORK", "false")
    assert not related_work_enabled()
    assert related_work_enabled(requested=True)
    monkeypatch.setenv("SIBYL_RELATED_WORK", "true")
    assert not related_work_enabled(requested=False)


def test_render_related_work():
    paper = RelatedPaper(ref="R1", title="Sparse Attention", authors=list("ABCDE"), year=2021, url="https://arxiv.org/abs/1", abstract="Abs.", relation="Same problem.")
    text = render_related_work([paper])
    assert text.startswith('<related_work>\n<paper ref="R1">')
    assert "Sparse Attention (2021) by A, B, C, D et al.\nhttps://arxiv.org/abs/1\n" in text
    assert "Relation to the submission (assessed from the abstract): Same problem." in text


def test_finder_searches_dedupes_and_selects():
    selection = json.dumps({"selected": [{"index": 2, "relation": "Competing method."}, {"index": 9, "relation": "bogus"}, {"index": 1, "relation": "Same task."}]})
    engine = FakeEngine([f"<think>plan</think>{QUERIES}", selection])
    calls: list[str] = []
    statuses: list[str] = []
    progress: list[tuple[int, int]] = []

    async def on_status(message: str) -> None:
        statuses.append(message)

    async def on_progress(done: int, total: int) -> None:
        progress.append((done, total))

    async def run():
        async with _arxiv_client(calls) as client:
            finder = RelatedWorkFinder(engine, "qwen3:8b", client, sources=("arxiv",))  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
            return await finder.find("# Our Paper Title\n\nAbstract...", "Our Paper Title", slot=2, on_status=on_status, on_progress=on_progress)

    papers = asyncio.run(run())

    # The duplicate query runs once; each paper appears once; the submission itself is dropped.
    assert calls == ["all:sparse AND all:attention", "all:Efficient AND all:Transformers"]
    assert [(p.ref, p.title, p.relation) for p in papers] == [
        ("R1", "Linear Attention", "Competing method."),
        ("R2", "Sparse Attention", "Same task."),
    ]
    candidates = engine.requests[1].prompt
    assert "[1] Sparse Attention (2023)" in candidates
    assert "[2] Linear Attention" in candidates
    assert candidates.count("Our Paper Title") == 1  # in the submission opening, not among the candidates
    assert all(r.model == "qwen3:8b" and r.slot == 2 and r.keep_loaded for r in engine.requests)
    assert statuses[-1] == "Found 2 related paper(s) on arXiv"
    # Queries written, then each of the two searches, then the selection: 4 tasks in all.
    assert progress == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_finder_falls_back_to_title_and_top_results():
    engine = FakeEngine([RuntimeError("model down"), RuntimeError("still down")])
    calls: list[str] = []

    async def run():
        async with _arxiv_client(calls) as client:
            return await RelatedWorkFinder(engine, "m", client, sources=("arxiv",)).find("text", "Efficient Transformers", on_status=None)  # ty: ignore[invalid-argument-type]  # duck-typed fake engine

    papers = asyncio.run(run())
    assert calls == ["all:Efficient AND all:Transformers"]
    assert [(p.ref, p.title, p.relation) for p in papers] == [("R1", "Linear Attention", ""), ("R2", "Our Paper Title", "")]


def test_finder_survives_arxiv_outage():
    engine = FakeEngine([QUERIES])
    calls: list[str] = []
    statuses: list[str] = []

    async def on_status(message: str) -> None:
        statuses.append(message)

    async def run():
        async with _arxiv_client(calls, fail=True) as client:
            return await RelatedWorkFinder(engine, "m", client, sources=("arxiv",)).find("text", "T", on_status=on_status)  # ty: ignore[invalid-argument-type]  # duck-typed fake engine

    assert asyncio.run(run()) == []
    assert len(calls) == 2
    assert statuses[-1] == "No related work found on arXiv; reviewing without it"
    assert len(engine.requests) == 1  # no selection call without candidates


S2_RESPONSE = {
    "total": 3,
    "data": [
        {
            "paperId": "abc",
            "title": "Linear  Attention",
            "abstract": "Also on arXiv.",
            "year": 2023,
            "url": "https://www.semanticscholar.org/paper/abc",
            "externalIds": {"ArXiv": "2301.00002"},
            "authors": [{"name": "Ada Lovelace"}],
        },
        {
            "paperId": "def",
            "title": "Attention in Journals",
            "abstract": None,
            "year": None,
            "url": "https://www.semanticscholar.org/paper/def",
            "externalIds": {"DOI": "10.1/x"},
            "authors": [],
        },
        {"paperId": "ghi", "title": None, "url": "https://www.semanticscholar.org/paper/ghi"},
    ],
}


def test_parse_semantic_scholar():
    papers = parse_semantic_scholar(S2_RESPONSE)
    assert [(p.title, p.url, p.year, p.abstract, p.authors) for p in papers] == [
        ("Linear Attention", "https://arxiv.org/abs/2301.00002", 2023, "Also on arXiv.", ["Ada Lovelace"]),
        ("Attention in Journals", "https://www.semanticscholar.org/paper/def", None, "", []),
    ]
    assert parse_semantic_scholar({}) == []


def test_finder_merges_arxiv_and_semantic_scholar():
    engine = FakeEngine([json.dumps({"queries": ["sparse attention"]}), RuntimeError("no selection")])
    calls: list[str] = []
    s2_calls: list[httpx.Request] = []
    progress: list[tuple[int, int]] = []
    statuses: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = parse_qs(urlparse(str(request.url)).query)
        if "semanticscholar" in request.url.host:
            s2_calls.append(request)
            # The first attempt is rate-limited and retried.
            return httpx.Response(429) if len(s2_calls) == 1 else httpx.Response(200, json=S2_RESPONSE)
        calls.append(params["search_query"][0])
        return httpx.Response(200, text=FEEDS["all:sparse AND all:attention"])

    async def on_progress(done: int, total: int) -> None:
        progress.append((done, total))

    async def on_status(message: str) -> None:
        statuses.append(message)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            finder = RelatedWorkFinder(engine, "m", client, sources=("arxiv", "semantic_scholar"))  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
            return await finder.find("text", "T", on_status=on_status, on_progress=on_progress)

    papers = asyncio.run(run())
    assert calls == ["all:sparse AND all:attention"]
    assert len(s2_calls) == 2
    assert parse_qs(urlparse(str(s2_calls[0].url)).query)["query"] == ["sparse attention"]
    # Linear Attention is on both sources and appears once; the journal paper only Semantic Scholar knows is added.
    assert [p.title for p in papers] == ["Sparse Attention", "Linear Attention", "Attention in Journals"]
    assert progress[0] == (1, 4)
    assert progress[-1] == (4, 4)
    assert statuses[-1] == "Found 3 related paper(s) on arXiv and Semantic Scholar"


def test_finder_without_sources_skips_search():
    engine = FakeEngine([])
    assert asyncio.run(RelatedWorkFinder(engine, "m", sources=()).find("text", "T")) == []  # ty: ignore[invalid-argument-type]  # duck-typed fake engine
    assert engine.requests == []


def test_review_prompt_includes_related_work():
    from sibyl.services.reviewer import ReviewSystem

    reply = json.dumps(
        {
            "novelty": "Close to [R1].",
            "methodology": "m",
            "results": "r",
            "clarity": "c",
            "impact": "i",
            "limitations": "l",
            "strengths": "s",
            "score": 3,
            "recommendation": "Major Revision",
            "detailed_feedback": "f",
        }
    )
    engine = FakeEngine([reply])
    paper = RelatedPaper(ref="R1", title="Sparse Attention", url="https://arxiv.org/abs/1", abstract="Abs.")

    review = asyncio.run(ReviewSystem(engine, "m").review_paper("paper body", "T", related_work=[paper]))  # ty: ignore[invalid-argument-type]  # duck-typed fake engine

    prompt = engine.requests[0].prompt
    assert prompt.index("<related_work>") < prompt.index("<research_paper>")
    assert '<paper ref="R1">' in prompt
    assert review.related_work == [paper]
