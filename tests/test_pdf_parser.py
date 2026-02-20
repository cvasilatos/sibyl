"""Tests for the PDF parser module."""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from sibyl.pdf_parser import PDFParser


def test_pdf_parser_file_not_found():
    """Test PDFParser raises FileNotFoundError when extracting text from a non-existent file."""
    parser = PDFParser("/nonexistent/file.pdf")
    with pytest.raises(FileNotFoundError):
        parser.extract_text()


def test_pdf_parser_init_default_grobid_url():
    """Test PDFParser initialization stores the GROBID URL from environment."""
    with patch.dict(os.environ, {"GROBID_URL": "http://custom-grobid:8070"}):
        parser = PDFParser("/test/file.pdf")
        assert parser._grobid_url == "http://custom-grobid:8070"


def test_pdf_parser_init_default_grobid_url_fallback(monkeypatch):
    """Test PDFParser initialization falls back to default GROBID URL."""
    monkeypatch.delenv("GROBID_URL", raising=False)
    parser = PDFParser("/test/file.pdf")
    assert parser._grobid_url == "http://localhost:8070"


def test_pdf_parser_init_stores_pdf_path():
    """Test PDFParser initialization stores the PDF path."""
    parser = PDFParser("/test/file.pdf")
    assert parser._pdf_path == "/test/file.pdf"


def test_get_metadata_pypdf_only():
    """Test metadata extraction using pypdf when GROBID returns nothing."""
    mock_metadata = {
        "/Title": "Test Paper",
        "/Author": "John Doe",
        "/Subject": "Test Subject",
        "/Creator": "Test Creator",
        "/Producer": "Test Producer",
    }

    with patch("pathlib.Path.open", mock_open(read_data=b"fake pdf")), patch(
        "pypdf.PdfReader"
    ) as mock_reader, patch.object(PDFParser, "_extract_metadata_grobid", return_value=None):
        mock_reader.return_value.metadata = mock_metadata
        mock_reader.return_value.pages = [None, None, None]

        parser = PDFParser("/test/file.pdf")
        metadata = parser.get_metadata()

        assert metadata["title"] == "Test Paper"
        assert metadata["author"] == "John Doe"
        assert metadata["subject"] == "Test Subject"
        assert metadata["num_pages"] == 3


def test_get_metadata_grobid_fallback():
    """Test GROBID enriches pypdf metadata when available."""
    mock_metadata = {}

    grobid_bibtex = """@article{unknown,
  title = {GROBID Extracted Title},
  author = {Jane Smith, Bob Jones},
}"""

    with patch("pathlib.Path.open", mock_open(read_data=b"fake pdf")), patch(
        "pypdf.PdfReader"
    ) as mock_reader, patch("requests.post") as mock_post:
        mock_reader.return_value.metadata = mock_metadata
        mock_reader.return_value.pages = [None, None]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = grobid_bibtex
        mock_post.return_value = mock_response

        parser = PDFParser("/test/file.pdf")
        metadata = parser.get_metadata()

        assert metadata["title"] == "GROBID Extracted Title"
        assert metadata["author"] == "Jane Smith, Bob Jones"
        assert metadata["num_pages"] == 2


def test_get_metadata_grobid_failure_raises():
    """Test that get_metadata raises an exception when GROBID request fails."""
    mock_metadata = {}

    with patch(
        "builtins.open", mock_open(read_data=b"fake pdf")
    ), patch("pypdf.PdfReader") as mock_reader, patch("requests.post") as mock_post:
        mock_reader.return_value.metadata = mock_metadata
        mock_reader.return_value.pages = [None]

        mock_post.side_effect = Exception("Connection error")

        parser = PDFParser("/test/file.pdf")
        with pytest.raises(Exception):
            parser.get_metadata()


def test_parse_grobid_bibtex_with_fields():
    """Test parsing GROBID BibTeX with title, author, and abstract."""
    bibtex = """@article{test,
  title = {Research Paper Title},
  author = {Alice Wonder},
  abstract = {This is the abstract of the paper.},
}"""

    parser = PDFParser("/test/file.pdf")
    metadata = parser._parse_grobid_bibtex(bibtex)

    assert metadata["title"] == "Research Paper Title"
    assert metadata["author"] == "Alice Wonder"
    assert metadata["abstract"] == "This is the abstract of the paper."


def test_parse_grobid_bibtex_missing_fields():
    """Test parsing GROBID BibTeX with no recognized fields returns Unknown defaults."""
    bibtex = "@article{test,}"

    parser = PDFParser("/test/file.pdf")
    metadata = parser._parse_grobid_bibtex(bibtex)

    assert metadata["title"] == "Unknown"
    assert metadata["author"] == "Unknown"
    assert "abstract" not in metadata
