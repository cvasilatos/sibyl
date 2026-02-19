"""Web application for the Sibyl research paper review system."""

import asyncio
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .comparison import ReviewComparison
from .config import SibylConfig
from .llm_client import create_client
from .pdf_parser import PDFParser
from .reviewer import PaperReview, ReviewSystem
from .storage import ReviewStorage

# Create FastAPI app
app = FastAPI(
    title="Sibyl Research Paper Review System",
    description="AI-powered research paper review using local LLMs",
    version="0.1.0",
)

# Add CORS middleware to allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active review sessions
review_sessions: Dict[str, Dict] = {}

# Store active model downloads
model_downloads: Dict[str, Dict] = {}

# Store active download tasks
download_tasks: Dict[str, asyncio.Task] = {}

# Initialize storage
storage = ReviewStorage()


class ReviewRequest(BaseModel):
    """Request model for paper review."""

    model_name: Optional[str] = None
    max_pages: Optional[int] = None


class ReviewResponse(BaseModel):
    """Response model for review results."""

    session_id: str
    paper_title: str
    reviews: List[Dict]
    comparison: Dict


class SessionStatus(BaseModel):
    """Status of a review session."""

    session_id: str
    status: str
    progress: int
    message: str
    paper_title: Optional[str] = None


@app.post("/api/upload")
async def upload_paper(file: UploadFile = File(...)):
    """Upload a PDF paper for review."""
    # Validate file extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only PDF files are supported"
        )

    # Read and validate PDF magic bytes
    content = await file.read()
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400, detail="Invalid PDF file. File does not appear to be a valid PDF"
        )

    # Create a session ID
    session_id = str(uuid.uuid4())

    # Save the uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{session_id}.pdf")

    with open(temp_path, "wb") as f:
        f.write(content)

    # Store session info
    review_sessions[session_id] = {
        "status": "uploaded",
        "pdf_path": temp_path,
        "filename": file.filename,
        "progress": 0,
        "message": "File uploaded successfully",
    }

    return {"session_id": session_id, "filename": file.filename}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time review progress updates.

    Query parameters:
        model: Optional model name to use for review (overrides env config)
    """
    await websocket.accept()

    if session_id not in review_sessions:
        await websocket.send_json({"status": "error", "message": "Session not found"})
        await websocket.close()
        return

    session = review_sessions[session_id]

    # Get optional model from query parameters
    selected_model = websocket.query_params.get("model")

    try:
        # Start the review process
        await websocket.send_json(
            {"status": "progress", "progress": 10, "message": "Extracting text from PDF..."}
        )

        # Load configuration
        config = SibylConfig.from_env()

        # Parse PDF
        parser = PDFParser(session["pdf_path"])
        metadata = parser.get_metadata()
        paper_text = parser.extract_text()
        paper_title = (metadata or {}).get("title", "Unknown Paper")

        await websocket.send_json(
            {
                "status": "progress",
                "progress": 30,
                "message": f"Extracted {len(paper_text)} characters",
            }
        )

        # Generate review
        await websocket.send_json(
            {"status": "progress", "progress": 40, "message": "Generating review..."}
        )

        # Get the active provider (defaulting to ollama)
        providers = config.get_active_providers()
        if not providers:
            await websocket.send_json({"status": "error", "message": "No LLM providers configured"})
            await websocket.close()
            return

        reviews = []
        for i, provider in enumerate(providers):
            try:
                provider_config = getattr(config, provider, None)
                if not provider_config:
                    await websocket.send_json(
                        {
                            "status": "error",
                            "message": f"Configuration for provider '{provider}' not found. Please check your .env file.",
                        }
                    )
                    await websocket.close()
                    return

                # Override model if selected by user
                if selected_model:
                    # Create a copy of the config with the selected model
                    from copy import deepcopy

                    provider_config = deepcopy(provider_config)
                    provider_config.model = selected_model

                client = create_client(provider, provider_config)
                reviewer = ReviewSystem(client)

                model_display = selected_model or provider_config.model
                progress = 40 + (50 * (i + 1) // len(providers))
                await websocket.send_json(
                    {
                        "status": "progress",
                        "progress": progress,
                        "message": f"Reviewing with {provider} ({model_display})...",
                    }
                )

                review = await reviewer.areview_paper(paper_text, paper_title)
                reviews.append(review)
            except AttributeError as e:
                await websocket.send_json(
                    {
                        "status": "error",
                        "message": f"Configuration error for provider '{provider}': {e!s}",
                    }
                )
                await websocket.close()
                return
            except Exception as e:
                await websocket.send_json(
                    {
                        "status": "error",
                        "message": f"Error reviewing with {provider}: {e!s}",
                    }
                )
                await websocket.close()
                return

        # Generate comparison
        await websocket.send_json(
            {"status": "progress", "progress": 90, "message": "Comparing reviews..."}
        )

        comparison = ReviewComparison(reviews)
        comparison_data = comparison.get_comparative_analysis()

        # Save reviews to storage
        await websocket.send_json(
            {"status": "progress", "progress": 95, "message": "Saving to storage..."}
        )

        for review in reviews:
            try:
                storage.save_review(
                    review=review,
                    pdf_filename=session["filename"],
                    pdf_path=session["pdf_path"],
                    paper_text=paper_text,
                )
            except Exception as e:
                # Log error but don't fail the whole operation
                print(f"Error saving review to storage: {e}")

        # Convert reviews to dict
        reviews_dict = [
            {
                "paper_title": r.paper_title,
                "reviewer_model": r.reviewer_model,
                "criteria": r.criteria.model_dump(),
                "raw_response": r.raw_response,
            }
            for r in reviews
        ]

        # Send results
        await websocket.send_json(
            {
                "status": "completed",
                "progress": 100,
                "message": "Review complete!",
                "results": {
                    "paper_title": paper_title,
                    "reviews": reviews_dict,
                    "comparison": comparison_data,
                },
            }
        )

        # Update session
        session["status"] = "completed"
        session["reviews"] = reviews_dict
        session["comparison"] = comparison_data

    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        # Note: PDFs are now stored in the storage system
        # Only clean up temp file if save to storage failed
        if session.get("status") != "completed":
            # Save failed, clean up temp file
            if "pdf_path" in session and os.path.exists(session["pdf_path"]):
                try:
                    os.remove(session["pdf_path"])
                except Exception:
                    pass


@app.get("/api/session/{session_id}", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """Get the status of a review session."""
    if session_id not in review_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = review_sessions[session_id]
    return SessionStatus(
        session_id=session_id,
        status=session["status"],
        progress=session["progress"],
        message=session["message"],
        paper_title=session.get("paper_title"),
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        config = SibylConfig.from_env()
        providers = config.get_active_providers()
        ollama_url = None
        if hasattr(config, "ollama") and config.ollama:
            ollama_url = getattr(config.ollama, "api_url", None)
        return {
            "status": "healthy",
            "providers": providers,
            "ollama_base_url": ollama_url,
            "storage_count": storage.count_reviews(),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


class SearchRequest(BaseModel):
    """Request model for search."""

    query: str
    limit: int = 10


@app.post("/api/search")
async def search_reviews(request: SearchRequest):
    """Search reviews using semantic similarity.

    Args:
        request: Search request with query and limit

    Returns:
        List of matching reviews with similarity scores

    """
    try:
        results = storage.search_reviews(request.query, limit=request.limit)
        return {
            "query": request.query,
            "results": [r.model_dump() for r in results],
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviews")
async def list_reviews(limit: int = 50, offset: int = 0):
    """List all stored reviews with pagination.

    Args:
        limit: Maximum number of reviews to return
        offset: Number of reviews to skip

    Returns:
        List of stored reviews

    """
    try:
        reviews = storage.list_reviews(limit=limit, offset=offset)
        total = storage.count_reviews()
        return {
            "reviews": [r.model_dump() for r in reviews],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviews/{review_id}")
async def get_review_details(review_id: str):
    """Get full details of a specific review.

    Args:
        review_id: ID of the review to retrieve

    Returns:
        Full review details including criteria

    """
    review = storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.delete("/api/reviews/{review_id}")
async def delete_review(review_id: str):
    """Delete a review by ID.

    Args:
        review_id: ID of the review to delete

    Returns:
        Success message

    """
    deleted = storage.delete_review(review_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted successfully", "id": review_id}


@app.get("/api/statistics")
async def get_statistics():
    """Get statistics about stored reviews.

    Returns:
        Statistics dictionary

    """
    try:
        stats = storage.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models")
async def list_models():
    """List available Ollama models.

    Returns:
        List of installed models from Ollama

    """
    try:
        config = SibylConfig.from_env()
        ollama_url = "http://localhost:11434"  # Default URL

        # Try to get URL from config if available
        if hasattr(config, "ollama") and config.ollama and hasattr(config.ollama, "api_url"):
            ollama_url = config.ollama.api_url or ollama_url

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()

            models_data = response.json()
            return {
                "models": models_data.get("models", []),
                "count": len(models_data.get("models", [])),
            }
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Ollama. Make sure Ollama is running. Error: {e!s}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/available")
async def list_available_models():
    """List available Ollama models that can be installed.

    Returns:
        List of models from Ollama library with installation status

    """
    try:
        import subprocess

        # Fetch all available models using curl command (equivalent to the bash command)
        try:
            result = subprocess.run(
                ["curl", "-s", "https://ollama.com/library"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            result.check_returncode()
            html_content = result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to httpx if curl not available
            async with httpx.AsyncClient(timeout=30.0) as client:
                library_response = await client.get("https://ollama.com/library")
                library_response.raise_for_status()
                html_content = library_response.text

        # Extract model names using regex (equivalent to: grep -oP 'href="/library/\K[^"]+')
        model_names = re.findall(r'href="/library/([^"]+)', html_content)

        # Remove duplicates and sort
        model_names = sorted(list(set(model_names)))

        # Get installed models
        config = SibylConfig.from_env()
        ollama_url = "http://localhost:11434"  # Default URL

        # Try to get URL from config if available
        if hasattr(config, "ollama") and config.ollama and hasattr(config.ollama, "api_url"):
            ollama_url = config.ollama.api_url or ollama_url

        installed_models = set()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{ollama_url}/api/tags")
                response.raise_for_status()
                models_data = response.json()
                installed_models = {m["name"].split(":")[0] for m in models_data.get("models", [])}
        except httpx.HTTPError:
            # If Ollama is not running, just mark all as not installed
            pass

        # Format the models
        available_models = []
        for model_name in model_names:
            model_info = {
                "name": model_name,
                "description": "Available from Ollama library",
                "size": "Unknown",  # Size info not available from this scraping
                "installed": model_name in installed_models,
            }
            available_models.append(model_info)

        return {"models": available_models, "count": len(available_models)}
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch models from Ollama library. Error: {e!s}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ModelDownloadRequest(BaseModel):
    """Request model for downloading an Ollama model."""

    model_name: str


@app.post("/api/models/download")
async def download_model(request: ModelDownloadRequest):
    """Initiate download/pull of an Ollama model asynchronously.

    Args:
        request: Model download request with model name

    Returns:
        Download ID for tracking progress via WebSocket

    """
    try:
        config = SibylConfig.from_env()
        ollama_url = "http://localhost:11434"  # Default URL

        # Try to get URL from config if available
        if hasattr(config, "ollama") and config.ollama and hasattr(config.ollama, "api_url"):
            ollama_url = config.ollama.api_url or ollama_url

        # Generate download ID
        download_id = str(uuid.uuid4())

        # Initialize download tracking
        model_downloads[download_id] = {
            "model_name": request.model_name,
            "status": "initiated",
            "progress": 0,
            "message": "Starting download...",
            "total": 0,
            "completed": 0,
        }

        # Start download in background task (async to avoid blocking)
        async def download_task():
            try:
                # Use httpx for async HTTP requests to avoid blocking the event loop
                async with httpx.AsyncClient(timeout=600.0) as client:
                    async with client.stream(
                        "POST",
                        f"{ollama_url}/api/pull",
                        json={"name": request.model_name},
                    ) as response:
                        response.raise_for_status()

                        # Process streaming response asynchronously
                        async for line in response.aiter_lines():
                            if line:
                                data = json.loads(line)

                                # Update progress tracking
                                download_info = model_downloads.get(download_id)
                                if not download_info:
                                    break  # Download was cancelled

                                status = data.get("status", "")
                                download_info["message"] = status

                                # Calculate progress based on bytes if available
                                if "total" in data and "completed" in data:
                                    download_info["total"] = data["total"]
                                    download_info["completed"] = data["completed"]
                                    if data["total"] > 0:
                                        download_info["progress"] = int(
                                            (data["completed"] / data["total"]) * 100
                                        )

                                # Check if download is complete
                                if status == "success":
                                    download_info["status"] = "completed"
                                    download_info["progress"] = 100
                                    download_info["message"] = (
                                        f"Model '{request.model_name}' downloaded successfully"
                                    )
                                    break

            except Exception as e:
                download_info = model_downloads.get(download_id)
                if download_info:
                    download_info["status"] = "error"
                    download_info["message"] = str(e)
            finally:
                # Clean up the task reference
                download_tasks.pop(download_id, None)

        # Start background task
        task = asyncio.create_task(download_task())
        download_tasks[download_id] = task

        return {
            "download_id": download_id,
            "model_name": request.model_name,
            "message": "Download started",
        }
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Ollama. Make sure Ollama is running. Error: {e!s}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/download/{download_id}")
async def get_download_status(download_id: str):
    """Get the status of a model download.

    Args:
        download_id: ID of the download to check

    Returns:
        Download progress and status

    """
    if download_id not in model_downloads:
        raise HTTPException(status_code=404, detail="Download not found")

    return model_downloads[download_id]


@app.websocket("/ws/models/download/{download_id}")
async def model_download_websocket(websocket: WebSocket, download_id: str):
    """WebSocket endpoint for real-time model download progress updates.

    Args:
        websocket: WebSocket connection
        download_id: ID of the download to track

    """
    await websocket.accept()

    if download_id not in model_downloads:
        await websocket.send_json({"status": "error", "message": "Download not found"})
        await websocket.close()
        return

    try:
        # Send progress updates
        while True:
            download_info = model_downloads.get(download_id)
            if not download_info:
                await websocket.send_json({"status": "error", "message": "Download cancelled"})
                break

            # Send current progress
            await websocket.send_json(download_info)

            # Check if download is complete or failed
            if download_info["status"] in ["completed", "error"]:
                break

            # Wait a bit before sending next update
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass  # Client disconnected, download continues in background
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        await websocket.close()


@app.get("/api/reviews/{review_id}/pdf")
async def download_review_pdf(review_id: str):
    """Download the PDF file associated with a review.

    Args:
        review_id: ID of the review

    Returns:
        PDF file as a download

    """
    try:
        review = storage.get_review(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        pdf_path = review.get("pdf_path")
        if not pdf_path or not Path(pdf_path).exists():
            raise HTTPException(status_code=404, detail="PDF file not found")

        # Return the PDF file with appropriate headers for download
        return FileResponse(
            pdf_path, media_type="application/pdf", filename=review.get("pdf_filename", "paper.pdf")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    ssl_certfile: Optional[str] = None,
    ssl_keyfile: Optional[str] = None,
):
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to bind to
        ssl_certfile: Path to SSL certificate file
        ssl_keyfile: Path to SSL key file

    """
    import uvicorn

    uvicorn.run(app, host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)


if __name__ == "__main__":
    run_server()
