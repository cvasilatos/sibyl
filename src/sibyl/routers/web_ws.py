import contextlib
import logging
from typing import cast

import anyio
import httpx
from decimalog.logger import CustomLogger
from fastapi import APIRouter, Query, WebSocket

from sibyl.comparison import ReviewComparison
from sibyl.config import OLLAMA_BASE_URL, LLMConfig, SibylConfig
from sibyl.llm.client.ollama import OllamaClient
from sibyl.pdf_parser import PDFParser
from sibyl.reviewer import PaperReview, ReviewSystem
from sibyl.routers.web_state import review_sessions, storage

router = APIRouter()

logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


@router.websocket("/pull")
async def pull_model(websocket: WebSocket, model_name: str) -> None:
    """WebSocket endpoint to pull a model from Ollama."""
    await websocket.accept()

    try:
        async with httpx.AsyncClient(timeout=600.0) as client, client.stream("POST", f"{OLLAMA_BASE_URL}/api/pull", json={"name": model_name}) as response:
            async for line in response.aiter_lines():
                if line:
                    await websocket.send_text(line)
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        await websocket.close()


@router.websocket("/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, model: str = Query(...)) -> None:
    """WebSocket endpoint for real-time review progress updates."""
    await websocket.accept()

    try:
        session = review_sessions[session_id]
        await websocket.send_json({"status": "progress", "progress": 10, "message": "Extracting text from PDF..."})

        config: LLMConfig = SibylConfig.from_env()

        parser = PDFParser(session["pdf_path"])
        metadata = parser.get_metadata()
        paper_text: str = parser.extract_text()
        paper_title = (metadata or {}).get("title", "Unknown Paper")

        await websocket.send_json({"status": "progress", "progress": 30, "message": f"Extracted {len(paper_text)} characters"})

        await websocket.send_json({"status": "progress", "progress": 40, "message": "Generating review..."})

        try:
            client = OllamaClient(config)
            reviewer = ReviewSystem(client)

            await websocket.send_json({"status": "progress", "progress": 50, "message": f"Reviewing with {model}..."})

            review: PaperReview = await reviewer.areview_paper(paper_text, paper_title, model)
            logger.info(f"Generated review for paper '{paper_title}' with model {model}:\n{review.raw_response}")
        except Exception as e:
            logger.exception(f"Error during review with model {model}")
            await websocket.send_json({"status": "error", "message": f"Error reviewing with {model}: {e!s}"})
            return

        await websocket.send_json({"status": "progress", "progress": 90, "message": "Comparing reviews..."})

        comparison = ReviewComparison([review])
        comparison_data = comparison.get_comparative_analysis()

        await websocket.send_json({"status": "progress", "progress": 95, "message": "Saving to storage..."})

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
                    "comparison": comparison_data,
                },
            }
        )

        session["status"] = "completed"
        session["reviews"] = reviews_dict
        session["comparison"] = comparison_data

    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        if session.get("status") != "completed" and "pdf_path" in session and await anyio.Path(session["pdf_path"]).exists():
            with contextlib.suppress(Exception):
                await anyio.Path(session["pdf_path"]).unlink()
