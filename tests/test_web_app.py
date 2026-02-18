"""Tests for the web application."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sibyl.web_app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    # Create a minimal PDF file
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


def test_root_endpoint(client):
    """Test the root endpoint returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Sibyl" in response.text
    assert "text/html" in response.headers["content-type"]


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_upload_pdf(client, sample_pdf):
    """Test uploading a PDF file."""
    with open(sample_pdf, "rb") as f:
        response = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "filename" in data
    assert data["filename"] == "test.pdf"

    # Clean up
    Path(sample_pdf).unlink(missing_ok=True)


def test_upload_non_pdf(client):
    """Test uploading a non-PDF file should fail."""
    response = client.post(
        "/api/upload", files={"file": ("test.txt", b"Not a PDF", "text/plain")}
    )

    assert response.status_code == 400
    assert "Only PDF files are supported" in response.text


def test_upload_fake_pdf(client):
    """Test uploading a file with .pdf extension but not actual PDF content."""
    response = client.post(
        "/api/upload",
        files={"file": ("fake.pdf", b"This is not a PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert "Invalid PDF file" in response.text


def test_upload_double_extension(client):
    """Test uploading a file with double extension."""
    response = client.post(
        "/api/upload",
        files={"file": ("malicious.pdf.exe", b"%PDF-1.4\nContent", "application/pdf")},
    )

    # Should fail because content type check or extension check
    assert response.status_code == 400


def test_session_not_found(client):
    """Test getting status for non-existent session."""
    response = client.get("/api/session/invalid-session-id")
    assert response.status_code == 404


def test_static_files_exist():
    """Test that static files exist."""
    static_dir = Path(__file__).parent.parent / "src" / "sibyl" / "static"
    assert (static_dir / "index.html").exists()
    assert (static_dir / "style.css").exists()
    assert (static_dir / "app.js").exists()


def test_response_models():
    """Test that response models are properly defined."""
    from sibyl.web_app import ReviewRequest, ReviewResponse, SessionStatus

    # Test ReviewRequest
    request = ReviewRequest(model_name="llama3.2", max_pages=10)
    assert request.model_name == "llama3.2"
    assert request.max_pages == 10

    # Test SessionStatus
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
