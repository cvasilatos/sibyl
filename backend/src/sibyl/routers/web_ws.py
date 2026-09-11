import contextlib
import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ollama import AsyncClient

import anyio
from decima.logger import CustomLogger
from fastapi import APIRouter, Query, WebSocket

from sibyl.pdf_parser import PDFParser
from sibyl.reviewer import PaperReview, ReviewSystem
from sibyl.routers.web_state import review_sessions, storage

router = APIRouter()

logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


@router.websocket("/pull")
async def pull_model(websocket: WebSocket, model_name: str = Query()) -> None:
    """WebSocket endpoint to pull a model from Ollama."""
    await websocket.accept()

    try:
        # If you stored them as a list: app.state.ollama_clients[0]
        # If you stored them as a dict: app.state.ollama_clients["default"]
        client: AsyncClient = websocket.app.state.ollama_clients[0]

        async for part in await client.pull(model=model_name, stream=True):
            logger.info(f"Pulling model {model_name}: {part}")
            data = part.model_dump() if hasattr(part, "model_dump") else part.dict()

            await websocket.send_json(data)

    except Exception as e:
        logger.exception(f"Error during model pull for {model_name}")
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@router.websocket("/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, model: str = Query(...), host: str = Query(...)) -> None:
    """WebSocket endpoint for real-time review progress updates."""
    await websocket.accept()
    session = review_sessions.get(session_id)

    if session is None:
        await websocket.send_json({"status": "error", "message": "Session not found"})
        await websocket.close(code=1008)
        return

    try:
        await websocket.send_json({"status": "progress", "progress": 10, "message": "Extracting text from PDF..."})

        parser = PDFParser(session["pdf_path"])
        metadata = parser.get_metadata(ollama_host=int(host))
        paper_text: str = metadata["text"]
        paper_title = (metadata or {}).get("title", "Unknown Paper")

        await websocket.send_json({"status": "progress", "progress": 30, "message": f"Extracted {len(paper_text)} characters"})

        await websocket.send_json({"status": "progress", "progress": 40, "message": "Generating review..."})

        try:
            for key, value in websocket.app.state.ollama_clients.items():
                logger.debug(f"Ollama client key: {key}, host: {value}")

            client: AsyncClient = websocket.app.state.ollama_clients[int(host) - 1]
            reviewer = ReviewSystem(client, model)

            await websocket.send_json({"status": "progress", "progress": 50, "message": f"Reviewing with {model}..."})

            review: PaperReview = await reviewer.review_paper(paper_text, paper_title, model)
            logger.info(f"Generated review for paper '{paper_title}' with model {model}:\n{review.raw_response}")
        except Exception as e:
            logger.exception(f"Error during review with model {model}")
            await websocket.send_json({"status": "error", "message": f"Error reviewing with {model}: {e!s}"})
            return

        await websocket.send_json({"status": "progress", "progress": 90, "message": "Saving to storage..."})

        review_id = storage.save_review(
            review=review,
            pdf_filename=session["filename"],
            pdf_path=session["pdf_path"],
            paper_text=paper_text,
        )

        reviews_dict = [
            {
                "paper_title": r.paper_title,
                "reviewer_model": r.reviewer_model,
                "criteria": r.criteria.model_dump(),
                "raw_response": r.raw_response,
            }
            for r in [review]
        ]

        await websocket.send_json(
            {
                "status": "completed",
                "progress": 100,
                "message": "Review complete!",
                "review_id": review_id,
                "results": {
                    "paper_title": paper_title,
                    "reviews": reviews_dict,
                },
            }
        )

        session["status"] = "completed"
        session["reviews"] = reviews_dict

    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        if session.get("status") != "completed" and "pdf_path" in session and await anyio.Path(session["pdf_path"]).exists():
            with contextlib.suppress(Exception):
                await anyio.Path(session["pdf_path"]).unlink()
