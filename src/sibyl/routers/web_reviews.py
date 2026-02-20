import asyncio
import re
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sibyl.storage.review import Review

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from sibyl.config import OLLAMA_BASE_URL
from sibyl.routers.web_state import review_sessions, storage
from sibyl.web.model.review_request import ReviewRequest
from sibyl.web.model.search_request import SearchRequest
from sibyl.web.model.session_status import SessionStatus

router = APIRouter()

# In-memory store for model pull jobs: pull_id -> status dict
_pull_jobs: dict[str, dict] = {}


@router.get("/session/{session_id}")
async def get_session_status(session_id: str) -> SessionStatus:
    session = review_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionStatus(
        session_id=session_id,
        status=session["status"],
        progress=session["progress"],
        message=session["message"],
        paper_title=session.get("paper_title"),
        results=session.get("results"),
    )


@router.get("/health")
async def health_check() -> dict:
    try:
        return {
            "status": "healthy",
            "ollama_base_url": OLLAMA_BASE_URL,
            "storage_count": storage.count_reviews(),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.post("/search")
async def search_reviews(request: SearchRequest) -> dict:
    results: list[Review] = storage.search_reviews(request.query, limit=request.limit)
    return {
        "query": request.query,
        "results": [r.model_dump() for r in results],
        "count": len(results),
    }


@router.get("/reviews")
async def list_reviews(limit: int = 50, offset: int = 0) -> dict:
    reviews: list[Review] = storage.list_reviews(limit=limit, offset=offset)
    total = storage.count_reviews()
    return {
        "reviews": [r.model_dump() for r in reviews],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/reviews/{review_id}")
async def get_review_details(review_id: str):
    review = storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    storage.delete_review(review_id)
    return {"message": "Review deleted successfully", "id": review_id}


@router.get("/statistics")
async def get_statistics() -> dict:
    return storage.get_statistics()


@router.get("/models")
async def list_models():
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()

        models_data = response.json()
        return {
            "models": models_data.get("models", []),
            "count": len(models_data.get("models", [])),
        }


@router.get("/models/available")
async def list_available_models() -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "curl",
            "-s",
            "https://ollama.com/library",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        if process.returncode != 0:
            raise RuntimeError(f"curl failed with return code {process.returncode}")
        html_content = stdout.decode("utf-8")
    except (TimeoutError, RuntimeError, FileNotFoundError):
        async with httpx.AsyncClient(timeout=30.0) as client:
            library_response = await client.get("https://ollama.com/library")
            library_response.raise_for_status()
            html_content = library_response.text

    model_names = re.findall(r'href="/library/([^\"]+)', html_content)
    model_names = sorted(set(model_names))

    installed_models = set()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            models_data = response.json()
            installed_models = {m["name"].split(":")[0] for m in models_data.get("models", [])}
    except httpx.HTTPError:
        pass

    available_models = []
    for model_name in model_names:
        model_info = {
            "name": model_name,
            "description": "Available from Ollama library",
            "size": "Unknown",
            "installed": model_name in installed_models,
        }
        available_models.append(model_info)

    return {"models": available_models, "count": len(available_models)}


@router.get("/reviews/{review_id}/pdf")
async def download_review_pdf(review_id: str) -> FileResponse:
    review = storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return FileResponse(review.get("pdf_path"), media_type="application/pdf", filename=review.get("pdf_filename", "paper.pdf"))


async def _run_review(session_id: str, model: str) -> None:
    """Background task: run the full review pipeline and update session state."""
    import contextlib
    import logging
    from typing import cast

    import anyio
    from decimalog.logger import CustomLogger

    from sibyl.comparison import ReviewComparison
    from sibyl.config import SibylConfig
    from sibyl.llm.client.ollama import OllamaClient
    from sibyl.pdf_parser import PDFParser
    from sibyl.reviewer import PaperReview, ReviewSystem

    logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))
    session = review_sessions[session_id]

    try:
        session.update({"status": "processing", "progress": 10, "message": "Extracting text from PDF..."})

        config = SibylConfig.from_env()
        parser = PDFParser(session["pdf_path"])
        metadata = parser.get_metadata()
        paper_text: str = parser.extract_text()
        paper_title = (metadata or {}).get("title", "Unknown Paper")
        session.update({"progress": 30, "message": f"Extracted {len(paper_text)} characters", "paper_title": paper_title})

        session.update({"progress": 50, "message": f"Reviewing with {model}..."})
        client = OllamaClient(config)
        reviewer = ReviewSystem(client)
        review: PaperReview = await reviewer.areview_paper(paper_text, paper_title, model_name=model)
        logger.info(f"Generated review for paper '{paper_title}' with model {model}")

        session.update({"progress": 90, "message": "Comparing reviews..."})
        comparison = ReviewComparison([review])
        comparison_data = comparison.get_comparative_analysis()

        session.update({"progress": 95, "message": "Saving to storage..."})
        storage.save_review(
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

        session.update({
            "status": "completed",
            "progress": 100,
            "message": "Review complete!",
            "results": {
                "paper_title": paper_title,
                "reviews": reviews_dict,
                "comparison": comparison_data,
            },
        })
    except Exception as e:
        logger.exception(f"Error during review for session {session_id}")
        session.update({"status": "error", "message": str(e)})
    finally:
        pdf_path = session.get("pdf_path")
        if session.get("status") != "completed" and pdf_path and await anyio.Path(pdf_path).exists():
            with contextlib.suppress(Exception):
                await anyio.Path(pdf_path).unlink()


@router.post("/session/{session_id}/review")
async def start_review(session_id: str, request: ReviewRequest, background_tasks: BackgroundTasks) -> dict:
    """Start the review process for an uploaded paper."""
    session = review_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") not in ("uploaded",):
        raise HTTPException(status_code=409, detail="Session is not in 'uploaded' state")

    model = request.model_name or "llama3.2"
    background_tasks.add_task(_run_review, session_id, model)
    return {"session_id": session_id, "status": "processing"}


async def _run_pull(pull_id: str, model_name: str) -> None:
    """Background task: pull a model from Ollama and track progress."""
    job = _pull_jobs[pull_id]
    try:
        async with httpx.AsyncClient(timeout=600.0) as client, client.stream("POST", f"{OLLAMA_BASE_URL}/api/pull", json={"name": model_name}) as response:
            async for line in response.aiter_lines():
                if line:
                    import json
                    try:
                        data = json.loads(line)
                        total = data.get("total", 0)
                        completed = data.get("completed", 0)
                        progress = int(completed / total * 100) if total else 0
                        job.update({"status": data.get("status", "pulling"), "progress": progress, "total": total, "completed": completed})
                        if data.get("status") == "success":
                            job["status"] = "success"
                            return
                    except Exception:
                        pass
        job["status"] = "success"
    except Exception as e:
        job.update({"status": "error", "message": str(e)})


@router.post("/models/pull")
async def pull_model_rest(model_name: str, background_tasks: BackgroundTasks) -> dict:
    """Start pulling a model from Ollama."""
    pull_id = str(uuid.uuid4())
    _pull_jobs[pull_id] = {"pull_id": pull_id, "model_name": model_name, "status": "pulling", "progress": 0}
    background_tasks.add_task(_run_pull, pull_id, model_name)
    return {"pull_id": pull_id, "model_name": model_name, "status": "pulling"}


@router.get("/models/pull/{pull_id}")
async def get_pull_status(pull_id: str) -> dict:
    """Get the status of a model pull job."""
    job = _pull_jobs.get(pull_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Pull job not found")
    return job
