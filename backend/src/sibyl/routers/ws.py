import contextlib
import logging
import time
from typing import TYPE_CHECKING, Annotated, Any, cast

import anyio
from anyio import to_thread
from decima.logger import CustomLogger
from fastapi import APIRouter, Query, WebSocket

from sibyl.schemas.review_config import ReviewDetail, ReviewMode
from sibyl.schemas.reviews import ReviewCriteria
from sibyl.schemas.ws import PullProgress, ReviewCompleted, ReviewProgress, ReviewResult, ReviewResults, SocketError
from sibyl.services.conferences import get_conference
from sibyl.services.figures import FigureDescriber, vlm_model_for
from sibyl.services.pdf_parser import PDFParser
from sibyl.services.related_work import RelatedWorkFinder, related_work_enabled
from sibyl.services.reviewer import PaperReview, ReviewSystem
from sibyl.state import review_sessions, storage

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

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
    progress: "Callable[[int, str], Awaitable[None]]",
) -> "list[RelatedPaper]":
    """Search arXiv for related work when enabled for this review; an empty list otherwise."""
    if not related_work_enabled(requested):
        return []

    async def status(message: str) -> None:
        await progress(47, message)

    return await RelatedWorkFinder(engine, model).find(paper_text, paper_title, slot=host, on_status=status)


async def _describe_figures(  # noqa: PLR0913
    engine: "InferenceEngine",
    vlm_model: str | None,
    paper_text: str,
    images: dict[str, Any],
    *,
    host: int,
    progress: "Callable[[int, str], Awaitable[None]]",
) -> tuple[str, int]:
    """Replace each figure with a vision model's description (the reviewer is text-only); return the text and the count."""

    async def status(message: str) -> None:
        await progress(40, message)

    paper_text, described = await FigureDescriber(engine, vlm_model).enrich(paper_text, images, slot=host, on_status=status)
    if described:
        await progress(45, f"Described {described} figure(s) with a vision model")
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
    detail: Annotated[ReviewDetail | None, Query()] = None,
    mode: Annotated[ReviewMode | None, Query()] = None,
) -> None:
    """WebSocket endpoint for real-time review progress updates.

    ``host`` is the review slot: 0 lets the engine choose, ``n`` targets GPU ``n - 1``.
    ``vlm`` is the vision model that describes figures: omitted uses the server default, ``none`` skips the step.
    ``related`` searches arXiv for related work before reviewing: omitted uses ``SIBYL_RELATED_WORK``.
    ``detail`` (concise, standard, detailed) and ``mode`` (single, sections) default to ``SIBYL_REVIEW_DETAIL`` and
    ``SIBYL_REVIEW_MODE``.
    """
    await websocket.accept()
    session = review_sessions.get(session_id)

    if session is None:
        await websocket.send_json(SocketError(message="Session not found").model_dump())
        await websocket.close(code=1008)
        return

    async def progress(value: int, message: str) -> None:
        await websocket.send_json(ReviewProgress(progress=value, message=message).model_dump())

    started = time.monotonic()
    # GPU work (model servers, PDF models) starts inside this block and is released once no review has run for a while.
    async with websocket.app.state.gpu_activity.review():
        await _run_review(websocket, session, progress, model=model, host=host, vlm=vlm, related=related, detail=detail, mode=mode, started=started)


async def _run_review(  # noqa: PLR0913
    websocket: WebSocket,
    session: "ReviewSession",
    progress: "Callable[[int, str], Awaitable[None]]",
    *,
    model: str,
    host: int,
    vlm: str | None,
    related: bool | None,
    detail: ReviewDetail | None,
    mode: ReviewMode | None,
    started: float,
) -> None:
    """Parse the paper, describe its figures, find related work, review it and save the result, reporting progress."""
    try:
        await progress(10, "Extracting text from PDF...")

        parser = PDFParser(session["pdf_path"])
        # Marker is CPU/GPU heavy and synchronous: run it off the event loop so other requests stay responsive.
        metadata = await to_thread.run_sync(parser.get_metadata, host)
        paper_text: str = metadata["text"]
        paper_title = (metadata or {}).get("title", "Unknown Paper")

        await progress(30, f"Extracted {len(paper_text)} characters")

        engine: InferenceEngine = websocket.app.state.engine

        vlm_model = vlm_model_for(engine.name, vlm)
        paper_text, described = await _describe_figures(engine, vlm_model, paper_text, metadata.get("images") or {}, host=host, progress=progress)

        search_related = related_work_enabled(related)
        related_work = await _related_work(engine, model, paper_text, paper_title, host=host, requested=search_related, progress=progress)

        conference_id = session.get("conference_id")
        conference = get_conference(conference_id) if conference_id else None
        form_label = f" using the {conference.name} {conference.edition} reviewer form" if conference else ""

        try:
            await progress(50, f"Reviewing with {model}{form_label}...")

            async def on_status(message: str) -> None:
                await progress(60, message)

            review: PaperReview = await ReviewSystem(engine, model).review_paper(
                paper_text,
                paper_title,
                model,
                review_form=session.get("review_form"),
                conference=conference,
                related_work=related_work,
                slot=host,
                on_status=on_status,
                detail=detail,
                mode=mode,
            )
            _record_run(review, session, vlm_model=vlm_model, figures=described, related=search_related, host=host, started=started)
            logger.info(f"Generated review for paper '{paper_title}' with model {model}")
        except Exception as e:
            logger.exception(f"Error during review with model {model}")
            await websocket.send_json(SocketError(message=f"Error reviewing with {model}: {e!s}").model_dump())
            return

        await progress(90, "Saving to storage...")

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
