import contextlib
import functools
import logging
import time
from typing import TYPE_CHECKING, Annotated, Any, cast, get_args

import anyio
from anyio import from_thread, to_thread
from decima.logger import CustomLogger
from fastapi import APIRouter, Query, WebSocket

from sibyl.schemas.review_config import ReviewDetail, ReviewMode
from sibyl.schemas.reviews import ReviewCriteria
from sibyl.schemas.ws import PullProgress, ReviewCompleted, ReviewProgress, ReviewResult, ReviewResults, ReviewStarted, ReviewStep, SocketError
from sibyl.services.conferences import get_conference
from sibyl.services.figures import FigureDescriber, vlm_model_for
from sibyl.services.pdf_parser import PDFParser
from sibyl.services.related_work import SOURCES, RelatedWorkFinder, parse_sources, related_work_enabled
from sibyl.services.review_progress import ReviewProgressTracker
from sibyl.services.reviewer import PaperReview, ReviewSystem
from sibyl.state import review_sessions, storage

if TYPE_CHECKING:
    from sibyl.inference import InferenceEngine
    from sibyl.schemas.related_work import RelatedPaper
    from sibyl.state import ReviewSession

router = APIRouter()


logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


@router.websocket("/pull")
async def pull_model(websocket: WebSocket, model_name: str = Query()) -> None:
    """WebSocket endpoint streaming model download progress from the active engine."""
    await websocket.accept()

    try:
        engine: InferenceEngine = websocket.app.state.engine
        logger.info(f"Downloading model {model_name}")
        async for part in engine.pull(model_name):  # progress goes to the client only: a log line per chunk fills the disk
            await websocket.send_json(PullProgress.model_validate(part).model_dump())
        logger.info(f"Downloaded model {model_name}")

    except Exception as e:
        logger.exception(f"Error during model pull for {model_name}")
        await websocket.send_json(SocketError(message=str(e)).model_dump())
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


async def _related_work(  # noqa: PLR0913
    engine: "InferenceEngine",
    model: str,
    paper_text: str,
    paper_title: str,
    *,
    host: int,
    requested: bool | None,
    sources: tuple[str, ...] | None,
    tracker: ReviewProgressTracker,
) -> "list[RelatedPaper]":
    """Search arXiv and Semantic Scholar for related work when enabled for this review; an empty list otherwise."""
    if not related_work_enabled(requested):
        return []
    finder = RelatedWorkFinder(engine, model, sources=sources)
    return await finder.find(paper_text, paper_title, slot=host, on_status=tracker.on_status("related_work"), on_progress=tracker.on_progress("related_work"))


async def _describe_figures(  # noqa: PLR0913
    engine: "InferenceEngine",
    vlm_model: str | None,
    paper_text: str,
    images: dict[str, Any],
    *,
    host: int,
    tracker: ReviewProgressTracker,
) -> tuple[str, int]:
    """Replace each figure with a vision model's description (the reviewer is text-only); return the text and the count."""
    describer = FigureDescriber(engine, vlm_model)
    paper_text, described = await describer.enrich(paper_text, images, slot=host, on_status=tracker.on_status("figures"), on_progress=tracker.on_progress("figures"))
    if described:
        await tracker.report("figures", f"Described {described} figure(s) with a vision model", done=1.0)
    return paper_text, described


def _record_run(review: PaperReview, session: "ReviewSession", *, vlm_model: str | None, figures: int, related: bool, host: int, started: float) -> None:  # noqa: PLR0913
    """Add the settings only the session knows to the review's recorded configuration."""
    if review.config is None:
        return
    review.config = review.config.model_copy(
        update={
            "review_form_name": session.get("review_form_filename") if session.get("review_form") else None,
            "vlm_model": vlm_model,
            "figures_described": figures,
            "related_work": related,
            "gpu": host - 1 if host > 0 else None,
            "duration_seconds": round(time.monotonic() - started, 1),
        }
    )


@router.websocket("/session/{session_id}")
async def websocket_endpoint(  # noqa: PLR0913
    websocket: WebSocket,
    session_id: str,
    model: str = Query(...),
    host: int = Query(0),
    vlm: str | None = Query(None),
    related: bool | None = Query(None),  # noqa: FBT001
    sources: str | None = Query(None),
    detail: Annotated[ReviewDetail | None, Query()] = None,
    mode: Annotated[ReviewMode | None, Query()] = None,
) -> None:
    """WebSocket endpoint for real-time review progress updates.

    ``host`` is the review slot: 0 lets the engine choose, ``n`` targets GPU ``n - 1``.
    ``vlm`` is the vision model that describes figures: omitted uses the server default, ``none`` skips the step.
    ``related`` searches arXiv and Semantic Scholar for related work before reviewing: omitted uses ``SIBYL_RELATED_WORK``.
    ``sources`` lists where to search, comma-separated (``arxiv``, ``semantic_scholar``): omitted uses
    ``SIBYL_RELATED_WORK_SOURCES``; none of them skips the search.
    ``detail`` (concise, standard, detailed) and ``mode`` (single, sections) default to ``SIBYL_REVIEW_DETAIL`` and
    ``SIBYL_REVIEW_MODE``.
    """
    await websocket.accept()
    session = review_sessions.get(session_id)

    if session is None:
        await websocket.send_json(SocketError(message="Session not found").model_dump())
        await websocket.close(code=1008)
        return

    started = time.monotonic()
    # GPU work (model servers, PDF models) starts inside this block and is released once no review has run for a while.
    async with websocket.app.state.gpu_activity.review():
        await _run_review(websocket, session, model=model, host=host, vlm=vlm, related=related, sources=parse_sources(sources), detail=detail, mode=mode, started=started)


async def _run_review(  # noqa: PLR0913
    websocket: WebSocket,
    session: "ReviewSession",
    *,
    model: str,
    host: int,
    vlm: str | None,
    related: bool | None,
    sources: tuple[str, ...] | None,
    detail: ReviewDetail | None,
    mode: ReviewMode | None,
    started: float,
) -> None:
    """Parse the paper, describe its figures, find related work, review it and save the result, reporting progress."""
    try:
        engine: InferenceEngine = websocket.app.state.engine
        vlm_model = vlm_model_for(engine.name, vlm)
        search_related = related_work_enabled(related) and bool(SOURCES if sources is None else sources)
        optional: dict[ReviewStep, bool] = {"figures": vlm_model is not None, "related_work": search_related}
        steps = [step for step in get_args(ReviewStep) if optional.get(step, True)]
        await websocket.send_json(ReviewStarted(steps=steps).model_dump())

        async def send(message: ReviewProgress) -> None:
            await websocket.send_json(message.model_dump())

        tracker = ReviewProgressTracker(steps, send)
        await tracker.report("parse", "Extracting text and figures from the PDF...")

        parser = PDFParser(session["pdf_path"])

        def on_stage(message: str, done: float) -> None:  # runs in the parsing thread
            from_thread.run(functools.partial(tracker.report, "parse", message, done=done))

        # Marker is CPU/GPU heavy and synchronous: run it off the event loop so other requests stay responsive.
        metadata = await to_thread.run_sync(parser.get_metadata, host, on_stage)
        paper_text: str = metadata["text"]
        paper_title = (metadata or {}).get("title", "Unknown Paper")

        images = metadata.get("images") or {}
        await tracker.report("parse", f"Extracted {len(paper_text)} characters and {len(images)} figure(s)", done=1.0)

        paper_text, described = await _describe_figures(engine, vlm_model, paper_text, images, host=host, tracker=tracker)

        related_work = await _related_work(engine, model, paper_text, paper_title, host=host, requested=search_related, sources=sources, tracker=tracker)

        conference_id = session.get("conference_id")
        conference = get_conference(conference_id) if conference_id else None
        form_label = f" using the {conference.name} {conference.edition} reviewer form" if conference else ""

        try:
            await tracker.report("review", f"Reviewing with {model}{form_label}...")
            review: PaperReview = await ReviewSystem(engine, model).review_paper(
                paper_text,
                paper_title,
                model,
                review_form=session.get("review_form"),
                conference=conference,
                related_work=related_work,
                slot=host,
                on_status=tracker.on_status("review"),
                detail=detail,
                mode=mode,
                on_progress=tracker.on_progress("review"),
            )
            _record_run(review, session, vlm_model=vlm_model, figures=described, related=search_related, host=host, started=started)
            logger.info(f"Generated review for paper '{paper_title}' with model {model}")
        except Exception as e:
            logger.exception(f"Error during review with model {model}")
            await websocket.send_json(SocketError(message=f"Error reviewing with {model}: {e!s}").model_dump())
            return

        await tracker.report("save", "Saving to storage...", done=0.0)

        review_id = await to_thread.run_sync(lambda: storage.save_review(review=review, pdf_filename=session["filename"], pdf_path=session["pdf_path"], paper_text=paper_text))

        result = ReviewResult(
            paper_title=review.paper_title,
            reviewer_model=review.reviewer_model,
            criteria=ReviewCriteria.model_validate(review.criteria.model_dump(mode="json")),
            raw_response=review.raw_response,
            related_work=review.related_work,
            config=review.config,
        )
        completed = ReviewCompleted(review_id=review_id, results=ReviewResults(paper_title=paper_title, reviews=[result]))
        await websocket.send_json(completed.model_dump(mode="json"))

        session["status"] = "completed"
        session["reviews"] = [result.model_dump(mode="json")]

    except Exception as e:
        logger.exception("Review session failed")
        await websocket.send_json(SocketError(message=str(e)).model_dump())
    finally:
        if session.get("status") != "completed" and "pdf_path" in session and await anyio.Path(session["pdf_path"]).exists():
            with contextlib.suppress(Exception):
                await anyio.Path(session["pdf_path"]).unlink()
