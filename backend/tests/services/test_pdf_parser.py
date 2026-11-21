"""Tests for the PDF parser module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from sibyl.services.pdf_parser import PDFParser


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


def test_get_marker_title_h1():
    """Test get_marker_title extracts level-1 heading."""
    parser = PDFParser("/test/file.pdf")
    markdown = "# My Paper Title\n\nSome text here."
    assert parser.get_marker_title(markdown) == "My Paper Title"


def test_get_marker_title_h2_fallback():
    """Test get_marker_title falls back to level-2 heading when no h1 found."""
    parser = PDFParser("/test/file.pdf")
    markdown = "## Secondary Title\n\nSome text."
    assert parser.get_marker_title(markdown) == "Secondary Title"


def test_get_marker_title_not_found():
    """Test get_marker_title returns fallback text when no heading found."""
    parser = PDFParser("/test/file.pdf")
    assert parser.get_marker_title("Just plain text with no headings.") == "Title Not Found"


def test_get_marker_title_strips_whitespace():
    """Test get_marker_title strips surrounding whitespace from title."""
    parser = PDFParser("/test/file.pdf")
    markdown = "#   Spaced Title   \n\nContent."
    assert parser.get_marker_title(markdown) == "Spaced Title"
