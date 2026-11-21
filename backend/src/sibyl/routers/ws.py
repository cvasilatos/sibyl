import contextlib
import logging
from typing import TYPE_CHECKING, cast

import anyio
from anyio import to_thread
from decima.logger import CustomLogger
from fastapi import APIRouter, Query, WebSocket

from sibyl.services.conferences import get_conference
from sibyl.services.figures import FigureDescriber, vlm_model_for
from sibyl.services.pdf_parser import PDFParser
from sibyl.services.reviewer import PaperReview, ReviewSystem
from sibyl.state import review_sessions, storage

if TYPE_CHECKING:
    from sibyl.inference import InferenceEngine

router = APIRouter()

logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


@router.websocket("/pull")
async def pull_model(websocket: WebSocket, model_name: str = Query()) -> None:
    """WebSocket endpoint streaming model download progress from the active engine."""
    await websocket.accept()

    try:
        engine: InferenceEngine = websocket.app.state.engine
        async for part in engine.pull(model_name):
            logger.debug(f"Pulling model {model_name}: {part}")
            await websocket.send_json(part)

    except Exception as e:
        logger.exception(f"Error during model pull for {model_name}")
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@router.websocket("/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, model: str = Query(...), host: int = Query(0)) -> None:
    """WebSocket endpoint for real-time review progress updates.

    ``host`` is the review slot: 0 lets the engine choose, ``n`` targets GPU ``n - 1``.
    """
    await websocket.accept()
    session = review_sessions.get(session_id)

    if session is None:
        await websocket.send_json({"status": "error", "message": "Session not found"})
        await websocket.close(code=1008)
        return

    async def progress(value: int, message: str) -> None:
        await websocket.send_json({"status": "progress", "progress": value, "message": message})

    try:
        await progress(10, "Extracting text from PDF...")

        parser = PDFParser(session["pdf_path"])
        # Marker is CPU/GPU heavy and synchronous: run it off the event loop so other requests stay responsive.
        metadata = await to_thread.run_sync(parser.get_metadata, host)
        paper_text: str = metadata["text"]
        paper_title = (metadata or {}).get("title", "Unknown Paper")

        await progress(30, f"Extracted {len(paper_text)} characters")

        engine: InferenceEngine = websocket.app.state.engine

        async def figure_status(message: str) -> None:
            await progress(40, message)

        # The reviewer is text-only: a vision model describes each figure image and the description replaces it.
        describer = FigureDescriber(engine, vlm_model_for(engine.name))
        paper_text, described = await describer.enrich(paper_text, metadata.get("images") or {}, slot=host, on_status=figure_status)
        if described:
            await progress(45, f"Described {described} figure(s) with a vision model")

        conference_id = session.get("conference_id")
        conference = get_conference(conference_id) if conference_id else None
        form_label = f" using the {conference.name} {conference.edition} reviewer form" if conference else ""

        try:
            reviewer = ReviewSystem(engine, model)

            await progress(50, f"Reviewing with {model}{form_label}...")

            async def on_status(message: str) -> None:
                await progress(60, message)

            review: PaperReview = await reviewer.review_paper(
                paper_text,
                paper_title,
                model,
                review_form=session.get("review_form"),
                conference=conference,
                slot=host,
                on_status=on_status,
            )
            logger.info(f"Generated review for paper '{paper_title}' with model {model}")
        except Exception as e:
            logger.exception(f"Error during review with model {model}")
            await websocket.send_json({"status": "error", "message": f"Error reviewing with {model}: {e!s}"})
            return

        await progress(90, "Saving to storage...")

        review_id = await to_thread.run_sync(lambda: storage.save_review(review=review, pdf_filename=session["filename"], pdf_path=session["pdf_path"], paper_text=paper_text))

        reviews_dict = [
            {
                "paper_title": review.paper_title,
                "reviewer_model": review.reviewer_model,
                "criteria": review.criteria.model_dump(),
                "raw_response": review.raw_response,
            }
        ]

        await websocket.send_json(
            {
                "status": "completed",
                "progress": 100,
                "message": "Review complete!",
                "review_id": review_id,
                "results": {"paper_title": paper_title, "reviews": reviews_dict},
            }
        )

        session["status"] = "completed"
        session["reviews"] = reviews_dict

    except Exception as e:
        logger.exception("Review session failed")
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        if session.get("status") != "completed" and "pdf_path" in session and await anyio.Path(session["pdf_path"]).exists():
            with contextlib.suppress(Exception):
                await anyio.Path(session["pdf_path"]).unlink()
