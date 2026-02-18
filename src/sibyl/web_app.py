"""Web application for the Sibyl research paper review system."""

import asyncio
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .comparison import ReviewComparison
from .config import SibylConfig
from .llm_client import create_client
from .pdf_parser import PDFParser
from .reviewer import PaperReview, ReviewSystem

# Create FastAPI app
app = FastAPI(
    title="Sibyl Research Paper Review System",
    description="AI-powered research paper review using local LLMs",
    version="0.1.0",
)

# Store active review sessions
review_sessions: Dict[str, Dict] = {}


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


# Serve static files (HTML, CSS, JS)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface."""
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sibyl - Research Paper Review</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }
                .container {
                    background: white;
                    border-radius: 12px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                h1 {
                    color: #333;
                    margin-bottom: 10px;
                }
                .subtitle {
                    color: #666;
                    margin-bottom: 30px;
                }
                .upload-area {
                    border: 3px dashed #667eea;
                    border-radius: 8px;
                    padding: 40px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s;
                    margin-bottom: 20px;
                }
                .upload-area:hover {
                    border-color: #764ba2;
                    background: #f8f9ff;
                }
                .upload-area.dragover {
                    background: #e8eaff;
                    border-color: #764ba2;
                }
                input[type="file"] {
                    display: none;
                }
                button {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: 600;
                    transition: transform 0.2s;
                }
                button:hover:not(:disabled) {
                    transform: translateY(-2px);
                }
                button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .progress-container {
                    display: none;
                    margin-top: 20px;
                }
                .progress-bar {
                    background: #e0e0e0;
                    border-radius: 10px;
                    height: 20px;
                    overflow: hidden;
                    margin-bottom: 10px;
                }
                .progress-fill {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    height: 100%;
                    width: 0%;
                    transition: width 0.3s;
                }
                .results {
                    display: none;
                    margin-top: 30px;
                }
                .review-card {
                    background: #f8f9ff;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-left: 4px solid #667eea;
                }
                .review-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }
                .score {
                    font-size: 24px;
                    font-weight: bold;
                    color: #667eea;
                }
                .recommendation {
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                }
                .recommendation.accept {
                    background: #d4edda;
                    color: #155724;
                }
                .recommendation.revise {
                    background: #fff3cd;
                    color: #856404;
                }
                .recommendation.reject {
                    background: #f8d7da;
                    color: #721c24;
                }
                .section {
                    margin-bottom: 15px;
                }
                .section-title {
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 5px;
                }
                .section-content {
                    color: #666;
                    line-height: 1.6;
                }
                .comparison-stats {
                    background: #f0f0f0;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .stat-row {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                }
                .error {
                    background: #f8d7da;
                    color: #721c24;
                    padding: 15px;
                    border-radius: 6px;
                    margin-top: 20px;
                }
                @media (max-width: 768px) {
                    .container {
                        padding: 20px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔮 Sibyl</h1>
                <p class="subtitle">AI-Powered Research Paper Review System</p>
                
                <div class="upload-area" id="uploadArea">
                    <div>📄</div>
                    <p>Drag and drop a PDF file here or click to browse</p>
                    <p style="color: #999; font-size: 14px;">Supports research papers in PDF format</p>
                    <input type="file" id="fileInput" accept=".pdf">
                </div>
                
                <button id="reviewBtn" disabled>Start Review</button>
                
                <div class="progress-container" id="progressContainer">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <p id="progressMessage">Initializing...</p>
                </div>
                
                <div class="results" id="results"></div>
            </div>
            
            <script>
                const uploadArea = document.getElementById('uploadArea');
                const fileInput = document.getElementById('fileInput');
                const reviewBtn = document.getElementById('reviewBtn');
                const progressContainer = document.getElementById('progressContainer');
                const progressFill = document.getElementById('progressFill');
                const progressMessage = document.getElementById('progressMessage');
                const results = document.getElementById('results');
                
                let selectedFile = null;
                let sessionId = null;
                let ws = null;
                
                // File input handling
                uploadArea.addEventListener('click', () => fileInput.click());
                
                fileInput.addEventListener('change', (e) => {
                    if (e.target.files.length > 0) {
                        selectedFile = e.target.files[0];
                        uploadArea.querySelector('p').textContent = `Selected: ${selectedFile.name}`;
                        reviewBtn.disabled = false;
                    }
                });
                
                // Drag and drop
                uploadArea.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    uploadArea.classList.add('dragover');
                });
                
                uploadArea.addEventListener('dragleave', () => {
                    uploadArea.classList.remove('dragover');
                });
                
                uploadArea.addEventListener('drop', (e) => {
                    e.preventDefault();
                    uploadArea.classList.remove('dragover');
                    if (e.dataTransfer.files.length > 0) {
                        selectedFile = e.dataTransfer.files[0];
                        fileInput.files = e.dataTransfer.files;
                        uploadArea.querySelector('p').textContent = `Selected: ${selectedFile.name}`;
                        reviewBtn.disabled = false;
                    }
                });
                
                // Review button click
                reviewBtn.addEventListener('click', async () => {
                    if (!selectedFile) return;
                    
                    reviewBtn.disabled = true;
                    results.style.display = 'none';
                    results.innerHTML = '';
                    progressContainer.style.display = 'block';
                    
                    const formData = new FormData();
                    formData.append('file', selectedFile);
                    
                    try {
                        const response = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (!response.ok) {
                            throw new Error('Upload failed');
                        }
                        
                        const data = await response.json();
                        sessionId = data.session_id;
                        
                        // Connect WebSocket for progress updates
                        connectWebSocket(sessionId);
                        
                    } catch (error) {
                        console.error('Error:', error);
                        results.innerHTML = '<div class="error">Error: Failed to upload file. Please try again.</div>';
                        results.style.display = 'block';
                        progressContainer.style.display = 'none';
                        reviewBtn.disabled = false;
                    }
                });
                
                function connectWebSocket(sessionId) {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    ws = new WebSocket(`${protocol}//${window.location.host}/ws/${sessionId}`);
                    
                    ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        
                        if (data.status === 'progress') {
                            progressFill.style.width = data.progress + '%';
                            progressMessage.textContent = data.message;
                        } else if (data.status === 'completed') {
                            progressContainer.style.display = 'none';
                            displayResults(data.results);
                            reviewBtn.disabled = false;
                        } else if (data.status === 'error') {
                            progressContainer.style.display = 'none';
                            results.innerHTML = `<div class="error">Error: ${data.message}</div>`;
                            results.style.display = 'block';
                            reviewBtn.disabled = false;
                        }
                    };
                    
                    ws.onerror = () => {
                        console.error('WebSocket error');
                        progressContainer.style.display = 'none';
                        results.innerHTML = '<div class="error">Connection error. Please try again.</div>';
                        results.style.display = 'block';
                        reviewBtn.disabled = false;
                    };
                }
                
                function displayResults(data) {
                    let html = '';
                    
                    // Comparison statistics
                    if (data.comparison) {
                        const stats = data.comparison.score_statistics;
                        html += `
                            <div class="comparison-stats">
                                <h3>Overall Statistics</h3>
                                <div class="stat-row">
                                    <strong>Mean Score:</strong>
                                    <span>${stats.mean.toFixed(2)}/10</span>
                                </div>
                                <div class="stat-row">
                                    <strong>Score Range:</strong>
                                    <span>${stats.min} - ${stats.max}</span>
                                </div>
                                <div class="stat-row">
                                    <strong>Consensus:</strong>
                                    <span>${data.comparison.consensus}</span>
                                </div>
                            </div>
                        `;
                    }
                    
                    // Individual reviews
                    data.reviews.forEach((review, index) => {
                        const criteria = review.criteria;
                        const recClass = criteria.recommendation.toLowerCase().includes('accept') ? 'accept' :
                                       criteria.recommendation.toLowerCase().includes('reject') ? 'reject' : 'revise';
                        
                        html += `
                            <div class="review-card">
                                <div class="review-header">
                                    <h3>${review.reviewer_model}</h3>
                                    <div>
                                        <span class="score">${criteria.overall_score}/10</span>
                                        <span class="recommendation ${recClass}">${criteria.recommendation}</span>
                                    </div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Novelty</div>
                                    <div class="section-content">${criteria.novelty}</div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Methodology</div>
                                    <div class="section-content">${criteria.methodology}</div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Results</div>
                                    <div class="section-content">${criteria.results}</div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Clarity</div>
                                    <div class="section-content">${criteria.clarity}</div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Impact</div>
                                    <div class="section-content">${criteria.impact}</div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Strengths</div>
                                    <div class="section-content">${criteria.strengths}</div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Limitations</div>
                                    <div class="section-content">${criteria.limitations}</div>
                                </div>
                                
                                <div class="section">
                                    <div class="section-title">Detailed Feedback</div>
                                    <div class="section-content">${criteria.detailed_feedback}</div>
                                </div>
                            </div>
                        `;
                    });
                    
                    results.innerHTML = html;
                    results.style.display = 'block';
                }
            </script>
        </body>
        </html>
        """
    )


@app.post("/api/upload")
async def upload_paper(file: UploadFile = File(...)):
    """Upload a PDF paper for review."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Create a session ID
    session_id = str(uuid.uuid4())

    # Save the uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{session_id}.pdf")

    with open(temp_path, "wb") as f:
        content = await file.read()
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
    """WebSocket endpoint for real-time review progress updates."""
    await websocket.accept()

    if session_id not in review_sessions:
        await websocket.send_json({"status": "error", "message": "Session not found"})
        await websocket.close()
        return

    session = review_sessions[session_id]

    try:
        # Start the review process
        await websocket.send_json(
            {"status": "progress", "progress": 10, "message": "Extracting text from PDF..."}
        )

        # Load configuration
        config = SibylConfig.from_env()

        # Parse PDF
        parser = PDFParser(session["pdf_path"])
        paper_text = parser.extract_text()
        paper_title = getattr(parser, "title", "Unknown Paper")

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
            await websocket.send_json(
                {"status": "error", "message": "No LLM providers configured"}
            )
            await websocket.close()
            return

        reviews = []
        for i, provider in enumerate(providers):
            provider_config = getattr(config, provider)
            client = create_client(provider, provider_config)
            reviewer = ReviewSystem(client)

            progress = 40 + (50 * (i + 1) // len(providers))
            await websocket.send_json(
                {
                    "status": "progress",
                    "progress": progress,
                    "message": f"Reviewing with {provider}...",
                }
            )

            review = reviewer.review_paper(paper_text, paper_title)
            reviews.append(review)

        # Generate comparison
        await websocket.send_json(
            {"status": "progress", "progress": 95, "message": "Comparing reviews..."}
        )

        comparison = ReviewComparison(reviews)
        comparison_data = comparison.get_comparative_analysis()

        # Convert reviews to dict
        reviews_dict = [
            {
                "paper_title": r.paper_title,
                "reviewer_model": r.reviewer_model,
                "criteria": r.criteria.model_dump(),
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
        # Clean up temporary file
        if os.path.exists(session["pdf_path"]):
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
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to bind to

    """
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
