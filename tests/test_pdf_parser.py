"""Tests for the PDF parser module."""

import pytest

from sibyl.pdf_parser import PDFParser


def test_pdf_parser_file_not_found():
    """Test PDFParser raises error for non-existent file."""
    with pytest.raises(FileNotFoundError):
        PDFParser("/nonexistent/file.pdf")


# Note: Full PDF parsing tests would require sample PDF files
# Additional tests can be implemented when sample PDFs are available
