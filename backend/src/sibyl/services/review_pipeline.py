"""One review from start to finish: parse the PDF, describe its figures, find related work, review it and save it.

The review queue (``services.review_queue``) runs this for each job in the background; progress goes to a callback
instead of a connection, so a review does not depend on anyone watching it.
"""

from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, get_args

from anyio import from_thread, to_thread

from sibyl.schemas.reviews import ReviewCriteria
from sibyl.schemas.ws import ReviewResult, ReviewResults, ReviewStep
from sibyl.services.conferences import get_conference
from sibyl.services.figures import FigureDescriber, vlm_model_for
from sibyl.services.pdf_parser import PDFParser
from sibyl.services.related_work import SOURCES, RelatedWorkFinder, related_work_enabled
from sibyl.services.review_progress import ReviewProgressTracker
from sibyl.services.reviewer import PaperReview, ReviewSystem

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from sibyl.inference import InferenceEngine
    from sibyl.schemas.related_work import RelatedPaper
    from sibyl.schemas.review_config import ReviewDetail, ReviewMode
    from sibyl.schemas.ws import ReviewProgress
    from sibyl.storage.engine import Engine as Storage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReviewInputs:
    """Everything a review needs besides the engine: the paper, the form to answer and the user's choices."""

    pdf_path: Path
    filename: str
    model: str
    owner: str
    vlm: str | None = None
    """Vision model that describes figures: None uses the server default, ``none`` skips the step."""
    related: bool | None = None
    """Search for related work; None uses ``SIBYL_RELATED_WORK``."""
    sources: tuple[str, ...] | None = None
    """Where to search; None uses ``SIBYL_RELATED_WORK_SOURCES``."""
    detail: ReviewDetail | None = None
    mode: ReviewMode | None = None
    review_form: str | None = None
    review_form_filename: str | None = None
    conference_id: str | None = None


class ReviewFailedError(RuntimeError):
    """A review that could not be finished, with a message for the user."""


def planned_steps(engine_name: str, inputs: ReviewInputs) -> list[ReviewStep]:
    """List the steps this review will take, in order (figures and related work only when enabled)."""
    optional: dict[ReviewStep, bool] = {"figures": _vlm(engine_name, inputs) is not None, "related_work": _search_related(inputs)}
    return [step for step in get_args(ReviewStep) if optional.get(step, True)]


def _vlm(engine_name: str, inputs: ReviewInputs) -> str | None:
    return vlm_model_for(engine_name, inputs.vlm)


def _search_related(inputs: ReviewInputs) -> bool:
    return related_work_enabled(inputs.related) and bool(SOURCES if inputs.sources is None else inputs.sources)


async def _related_work(  # noqa: PLR0913
    engine: InferenceEngine, inputs: ReviewInputs, paper_text: str, paper_title: str, *, host: int, tracker: ReviewProgressTracker
) -> list[RelatedPaper]:
    """Search arXiv and Semantic Scholar for related work when enabled for this review; an empty list otherwise."""
    if not _search_related(inputs):
        return []
    finder = RelatedWorkFinder(engine, inputs.model, sources=inputs.sources)
    return await finder.find(paper_text, paper_title, slot=host, on_status=tracker.on_status("related_work"), on_progress=tracker.on_progress("related_work"))


async def _describe_figures(  # noqa: PLR0913
    engine: InferenceEngine, vlm_model: str | None, paper_text: str, images: dict[str, Any], *, host: int, tracker: ReviewProgressTracker
) -> tuple[str, int]:
    """Replace each figure with a vision model's description (the reviewer is text-only); return the text and the count."""
    describer = FigureDescriber(engine, vlm_model)
    paper_text, described = await describer.enrich(paper_text, images, slot=host, on_status=tracker.on_status("figures"), on_progress=tracker.on_progress("figures"))
    if described:
        await tracker.report("figures", f"Described {described} figure(s) with a vision model", done=1.0)
    return paper_text, described


def _record_run(review: PaperReview, inputs: ReviewInputs, *, vlm_model: str | None, figures: int, related: bool, host: int, started: float) -> None:  # noqa: PLR0913
    """Add the settings only the run knows to the review's recorded configuration."""
    if review.config is None:
        return
    review.config = review.config.model_copy(
        update={
            "review_form_name": inputs.review_form_filename if inputs.review_form else None,
            "vlm_model": vlm_model,
            "figures_described": figures,
            "related_work": related,
            "gpu": host - 1 if host > 0 else None,
            "duration_seconds": round(time.monotonic() - started, 1),
        }
    )


async def run_review(
    engine: InferenceEngine,
    storage: Storage,
    inputs: ReviewInputs,
    *,
    host: int,
    send: Callable[[ReviewProgress], Awaitable[None]],
) -> tuple[str, ReviewResults]:
    """Review the paper on review slot ``host`` (0 = engine's choice, n = GPU n-1), save it and return its id and results.

    Progress goes to ``send``. Raises ``ReviewFailedError`` with a message for the user when the review fails.
    """
    started = time.monotonic()
    vlm_model = _vlm(engine.name, inputs)
    search_related = _search_related(inputs)
    tracker = ReviewProgressTracker(planned_steps(engine.name, inputs), send)
    await tracker.report("parse", "Extracting text and figures from the PDF...")

    parser = PDFParser(inputs.pdf_path)

    def on_stage(message: str, done: float) -> None:  # runs in the parsing thread
        from_thread.run(functools.partial(tracker.report, "parse", message, done=done))

    # Marker is CPU/GPU heavy and synchronous: run it off the event loop so other requests stay responsive.
    metadata = await to_thread.run_sync(parser.get_metadata, host, on_stage)
    paper_text: str = metadata["text"]
    paper_title = (metadata or {}).get("title", "Unknown Paper")

    images = metadata.get("images") or {}
    await tracker.report("parse", f"Extracted {len(paper_text)} characters and {len(images)} figure(s)", done=1.0)

    paper_text, described = await _describe_figures(engine, vlm_model, paper_text, images, host=host, tracker=tracker)

    related_work = await _related_work(engine, inputs, paper_text, paper_title, host=host, tracker=tracker)

    conference = get_conference(inputs.conference_id) if inputs.conference_id else None
    form_label = f" using the {conference.name} {conference.edition} reviewer form" if conference else ""

    try:
        await tracker.report("review", f"Reviewing with {inputs.model}{form_label}...")
        review: PaperReview = await ReviewSystem(engine, inputs.model).review_paper(
            paper_text,
            paper_title,
            inputs.model,
            review_form=inputs.review_form,
            conference=conference,
            related_work=related_work,
            slot=host,
            on_status=tracker.on_status("review"),
            detail=inputs.detail,
            mode=inputs.mode,
            on_progress=tracker.on_progress("review"),
        )
    except Exception as e:
        logger.exception(f"Error during review with model {inputs.model}")
        raise ReviewFailedError(f"Error reviewing with {inputs.model}: {e!s}") from e
    _record_run(review, inputs, vlm_model=vlm_model, figures=described, related=search_related, host=host, started=started)
    logger.info(f"Generated review for paper '{paper_title}' with model {inputs.model}")

    await tracker.report("save", "Saving to storage...", done=0.0)
    review_id = await to_thread.run_sync(
        lambda: storage.save_review(review=review, pdf_filename=inputs.filename, pdf_path=inputs.pdf_path, paper_text=paper_text, owner=inputs.owner)
    )

    result = ReviewResult(
        paper_title=review.paper_title,
        reviewer_model=review.reviewer_model,
        criteria=ReviewCriteria.model_validate(review.criteria.model_dump(mode="json")),
        raw_response=review.raw_response,
        related_work=review.related_work,
        config=review.config,
    )
    return review_id, ReviewResults(paper_title=paper_title, reviews=[result])
