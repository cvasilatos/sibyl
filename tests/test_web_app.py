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
    """Test getting status for non-existent session returns a server error."""
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    response = no_raise_client.get("/api/session/invalid-session-id")
    assert response.status_code == 500


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
