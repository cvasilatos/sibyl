import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sibyl.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
308
%%EOF"""

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        f.write(pdf_content)
        return f.name


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_config_endpoint(client):
    """Test the config endpoint returns max_score."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "max_score" in data
    assert isinstance(data["max_score"], int)
    assert data["max_score"] > 0


def test_upload_pdf(client, sample_pdf):
    """Test uploading a PDF file."""
    with open(sample_pdf, "rb") as f:
        response = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "filename" in data
    assert data["filename"] == "test.pdf"

    Path(sample_pdf).unlink(missing_ok=True)


def test_upload_non_pdf(client):
    """Test uploading a non-PDF file is accepted by the upload endpoint."""
    response = client.post("/api/upload", files={"file": ("test.txt", b"Not a PDF", "text/plain")})

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


def test_upload_any_content(client):
    """Test uploading a file with pdf extension but arbitrary content is accepted."""
    response = client.post(
        "/api/upload",
        files={"file": ("fake.pdf", b"This is not a PDF", "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


def test_upload_returns_session_id(client):
    """Test uploading any file returns a session_id and filename."""
    response = client.post(
        "/api/upload",
        files={"file": ("paper.pdf", b"%PDF-1.4\nContent", "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "filename" in data


def test_session_not_found(client):
    """Test getting status for non-existent session returns 404."""
    response = client.get("/api/session/invalid-session-id")
    assert response.status_code == 404


def test_response_models():
    """Test that response models are properly defined."""
    from sibyl.web.model.review_request import ReviewRequest
    from sibyl.web.model.review_response import ReviewResponse
    from sibyl.web.model.session_status import SessionStatus

    request = ReviewRequest(model_name="llama3.2", max_pages=10)
    assert request.model_name == "llama3.2"
    assert request.max_pages == 10

    status = SessionStatus(
        session_id="test-id",
        status="processing",
        progress=50,
        message="Processing...",
        paper_title="Test Paper",
    )
    assert status.session_id == "test-id"
    assert status.status == "processing"
    assert status.progress == 50


def test_delete_all_reviews(client):
    """Test the delete all reviews endpoint."""
    response = client.delete("/api/reviews")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "message" in data


def test_list_reviews_with_search_query(client):
    """Test that the /api/reviews endpoint accepts a q query parameter."""
    response = client.get("/api/reviews?q=machine+learning")
    assert response.status_code == 200
    data = response.json()
    assert "reviews" in data
    assert isinstance(data["reviews"], list)


def test_get_model_tags_response_shape(client):
    """Test that the model tags endpoint returns model and tags fields."""
    from unittest.mock import AsyncMock, MagicMock, patch

    model_name = "deepseek-r1"
    fake_html = (
        '<a href="/library/deepseek-r1:1.5b">1.5b</a>'
        '<a href="/library/deepseek-r1:7b">7b</a>'
        '<a href="/library/deepseek-r1:latest">latest</a>'
        '<a href="/library/deepseek-r1:v1-preview">v1-preview</a>'
    )

    mock_response = MagicMock()
    mock_response.text = fake_html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("sibyl.routers.web_reviews.httpx.AsyncClient", return_value=mock_client):
        response = client.get(f"/api/models/available/{model_name}/tags")

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == model_name
    assert isinstance(data["tags"], list)
    assert "1.5b" in data["tags"]
    assert "7b" in data["tags"]
    # Non-size tags must be filtered out
    assert "latest" not in data["tags"]
    assert "v1-preview" not in data["tags"]


def test_available_models_installed_variants(client):
    """Test that list_available_models returns installed_variants and does not mark a base
    model as installed when only a specific variant (e.g. :7b) is installed."""
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_library_html = '<a href="/library/llama3">llama3</a>'

    library_response = MagicMock()
    library_response.text = fake_library_html
    library_response.raise_for_status = MagicMock()

    async def mock_get(url, *args, **kwargs):
        return library_response

    mock_httpx_client = AsyncMock()
    mock_httpx_client.__aenter__ = AsyncMock(return_value=mock_httpx_client)
    mock_httpx_client.__aexit__ = AsyncMock(return_value=None)
    mock_httpx_client.get = mock_get

    # Mock Ollama client list() – llama3:7b installed
    mock_model = MagicMock()
    mock_model.model = "llama3:7b"
    mock_list_response = MagicMock()
    mock_list_response.models = [mock_model]
    mock_ollama = AsyncMock()
    mock_ollama.list = AsyncMock(return_value=mock_list_response)
    client.app.state.ollama_clients = {0: mock_ollama}

    with patch("sibyl.routers.web_reviews.httpx.AsyncClient", return_value=mock_httpx_client):
        response = client.get("/api/models/available")

    assert response.status_code == 200
    data = response.json()
    models = {m["name"]: m for m in data["models"]}

    # llama3:7b is installed but llama3 (bare/latest) is NOT — so installed must be False
    assert "llama3" in models
    assert models["llama3"]["installed"] is False
    # The variant "7b" should be reported
    assert "7b" in models["llama3"]["installed_variants"]


def test_available_models_installed_latest_is_not_marked(client):
    """Test that a base model is NOT marked installed when only :latest variant is present.
    The user should always be able to install variants regardless of whether :latest is installed."""
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_library_html = '<a href="/library/mistral">mistral</a>'

    library_response = MagicMock()
    library_response.text = fake_library_html
    library_response.raise_for_status = MagicMock()

    async def mock_get(url, *args, **kwargs):
        return library_response

    mock_httpx_client = AsyncMock()
    mock_httpx_client.__aenter__ = AsyncMock(return_value=mock_httpx_client)
    mock_httpx_client.__aexit__ = AsyncMock(return_value=None)
    mock_httpx_client.get = mock_get

    # Mock Ollama client list() – mistral:latest installed
    mock_model = MagicMock()
    mock_model.model = "mistral:latest"
    mock_list_response = MagicMock()
    mock_list_response.models = [mock_model]
    mock_ollama = AsyncMock()
    mock_ollama.list = AsyncMock(return_value=mock_list_response)
    client.app.state.ollama_clients = {0: mock_ollama}

    with patch("sibyl.routers.web_reviews.httpx.AsyncClient", return_value=mock_httpx_client):
        response = client.get("/api/models/available")

    assert response.status_code == 200
    data = response.json()
    models = {m["name"]: m for m in data["models"]}

    # mistral:latest is installed → base model should NOT be marked installed
    # so users can still install other variants
    assert "mistral" in models
    assert models["mistral"]["installed"] is False
    # The variant "latest" should still be reported in installed_variants
    assert "latest" in models["mistral"]["installed_variants"]


def test_concurrent_requests():
    """Test that the backend can handle concurrent requests (doesn't hang)."""
    test_client = TestClient(app)

    responses = []
    for _ in range(5):
        response = test_client.get("/api/health")
        responses.append(response)

    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# ---------------------------------------------------------------------------
# GPU endpoints
# ---------------------------------------------------------------------------


def test_gpu_list_no_nvml(client):
    """Test GPU list endpoint when NVML is unavailable returns empty list."""
    response = client.get("/api/gpu")
    assert response.status_code == 200
    data = response.json()
    assert "gpus" in data
    assert "count" in data
    # When no GPU hardware present, available must be False and count 0
    if not data["available"]:
        assert data["count"] == 0
        assert data["gpus"] == []


def test_gpu_single_no_nvml(client):
    """Test the single GPU endpoint with or without available hardware."""
    response = client.get("/api/gpu/0")
    assert response.status_code in (200, 503, 404)
    if response.status_code == 200:
        assert response.json()["index"] == 0


# ---------------------------------------------------------------------------
# Statistics endpoint
# ---------------------------------------------------------------------------


def test_get_statistics_empty(client):
    """Test statistics endpoint returns zeros when no reviews exist."""
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.json()
    assert "total_reviews" in data
    assert isinstance(data["total_reviews"], int)


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------


def test_search_endpoint(client):
    """Test the semantic search endpoint returns expected structure."""
    from unittest.mock import patch

    from sibyl.routers.web_state import storage

    with patch.object(storage, "search_reviews", return_value=[]):
        response = client.post("/api/search", json={"query": "machine learning", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data
    assert "count" in data


# ---------------------------------------------------------------------------
# Review detail and delete endpoints
# ---------------------------------------------------------------------------


def test_get_review_not_found(client):
    """Test getting a non-existent review returns 404."""
    response = client.get("/api/reviews/nonexistent-id-12345")
    assert response.status_code == 404


def test_delete_review_not_found(client):
    """Test deleting a non-existent review returns 404."""
    test_client = TestClient(app, raise_server_exceptions=False)
    response = test_client.delete("/api/reviews/nonexistent-id-12345")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------


def test_root_health_check(client):
    """Test the root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "online"
    assert "system" in data


# ---------------------------------------------------------------------------
# WebSocket endpoints
# ---------------------------------------------------------------------------


def test_ws_pull_model_error_path(client):
    """Test the WebSocket pull model endpoint sends an error message when pull fails."""
    from unittest.mock import AsyncMock

    mock_ollama = AsyncMock()
    mock_ollama.pull = AsyncMock(side_effect=Exception("Ollama unavailable"))
    client.app.state.ollama_clients = {0: mock_ollama}

    with client.websocket_connect("/ws/pull?model_name=llama3") as ws:
        data = ws.receive_json()
        assert data["status"] == "error"
        assert "Ollama unavailable" in data["message"]


def test_ws_pull_model_success_path(client):
    """Test the WebSocket pull endpoint streams progress messages from Ollama pull."""
    from unittest.mock import AsyncMock

    from starlette.websockets import WebSocketDisconnect

    class FakePart:
        def __init__(self, data: dict) -> None:
            self._data = data

        def model_dump(self) -> dict:
            return self._data

    class FakeAsyncIter:
        def __init__(self) -> None:
            self._items = [
                FakePart({"status": "pulling", "completed": 50, "total": 100}),
                FakePart({"status": "success"}),
            ]
            self._idx = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._idx >= len(self._items):
                raise StopAsyncIteration
            item = self._items[self._idx]
            self._idx += 1
            return item

    mock_ollama = AsyncMock()
    mock_ollama.pull = AsyncMock(return_value=FakeAsyncIter())
    client.app.state.ollama_clients = {0: mock_ollama}

    received = []
    with client.websocket_connect("/ws/pull?model_name=llama3") as ws:
        try:
            while True:
                received.append(ws.receive_json())
        except WebSocketDisconnect:
            pass

    assert any(m.get("status") == "pulling" for m in received)
    assert any(m.get("status") == "success" for m in received)
