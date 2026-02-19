"""Tests for the PDF parser module."""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from sibyl.pdf_parser import PDFParser


def test_pdf_parser_file_not_found():
    """Test PDFParser raises error for non-existent file."""
    with pytest.raises(FileNotFoundError):
        PDFParser("/nonexistent/file.pdf")


def test_pdf_parser_init_with_grobid_url():
    """Test PDFParser initialization with explicit GROBID URL."""
    with patch("pathlib.Path.exists", return_value=True):
        parser = PDFParser("/test/file.pdf", grobid_url="http://example.com:8070")
        assert parser.grobid_url == "http://example.com:8070"
        assert parser.use_grobid is True  # Should be enabled when URL is provided


def test_pdf_parser_init_with_grobid_enabled_env():
    """Test PDFParser initialization with GROBID enabled via environment."""
    with patch("pathlib.Path.exists", return_value=True), patch.dict(
        os.environ, {"GROBID_ENABLED": "true"}
    ):
        parser = PDFParser("/test/file.pdf")
        assert parser.use_grobid is True


def test_pdf_parser_init_with_grobid_disabled():
    """Test PDFParser initialization with GROBID disabled."""
    with patch("pathlib.Path.exists", return_value=True):
        parser = PDFParser("/test/file.pdf", use_grobid=False)
        assert parser.use_grobid is False


def test_get_metadata_pypdf_only():
    """Test metadata extraction using pypdf when metadata is available."""
    mock_metadata = {
        "/Title": "Test Paper",
        "/Author": "John Doe",
        "/Subject": "Test Subject",
        "/Creator": "Test Creator",
        "/Producer": "Test Producer",
    }

    with patch("pathlib.Path.exists", return_value=True), patch(
        "builtins.open", mock_open(read_data=b"fake pdf")
    ), patch("pypdf.PdfReader") as mock_reader:
        mock_reader.return_value.metadata = mock_metadata
        mock_reader.return_value.pages = [None, None, None]  # 3 pages

        parser = PDFParser("/test/file.pdf", use_grobid=False)
        metadata = parser.get_metadata()

        assert metadata["title"] == "Test Paper"
        assert metadata["author"] == "John Doe"
        assert metadata["subject"] == "Test Subject"
        assert metadata["num_pages"] == 3


def test_get_metadata_grobid_fallback():
    """Test GROBID fallback when pypdf metadata is empty."""
    # Mock empty pypdf metadata
    mock_metadata = {}

    # Mock GROBID TEI XML response
    grobid_response = """<?xml version="1.0" encoding="UTF-8"?>
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
        <teiHeader>
            <fileDesc>
                <titleStmt>
                    <title type="main">GROBID Extracted Title</title>
                </titleStmt>
                <sourceDesc>
                    <biblStruct>
                        <analytic>
                            <author>
                                <persName>
                                    <forename>Jane</forename>
                                    <surname>Smith</surname>
                                </persName>
                            </author>
                            <author>
                                <persName>
                                    <forename>Bob</forename>
                                    <surname>Jones</surname>
                                </persName>
                            </author>
                        </analytic>
                    </biblStruct>
                </sourceDesc>
            </fileDesc>
        </teiHeader>
    </TEI>"""

    with patch("pathlib.Path.exists", return_value=True), patch(
        "builtins.open", mock_open(read_data=b"fake pdf")
    ), patch("pypdf.PdfReader") as mock_reader, patch("requests.post") as mock_post:
        mock_reader.return_value.metadata = mock_metadata
        mock_reader.return_value.pages = [None, None]  # 2 pages

        # Mock GROBID response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = grobid_response
        mock_post.return_value = mock_response

        parser = PDFParser("/test/file.pdf", use_grobid=True)
        metadata = parser.get_metadata()

        assert metadata["title"] == "GROBID Extracted Title"
        assert metadata["author"] == "Jane Smith, Bob Jones"
        assert metadata["num_pages"] == 2


def test_get_metadata_grobid_failure_fallback():
    """Test fallback to pypdf when GROBID fails."""
    mock_metadata = {}

    with patch("pathlib.Path.exists", return_value=True), patch(
        "builtins.open", mock_open(read_data=b"fake pdf")
    ), patch("pypdf.PdfReader") as mock_reader, patch("requests.post") as mock_post:
        mock_reader.return_value.metadata = mock_metadata
        mock_reader.return_value.pages = [None]

        # Mock GROBID failure
        mock_post.side_effect = Exception("Connection error")

        parser = PDFParser("/test/file.pdf", use_grobid=True)
        metadata = parser.get_metadata()

        # Should fall back to pypdf metadata (which is empty in this case)
        assert metadata["title"] == "Unknown"
        assert metadata["author"] == "Unknown"


def test_parse_grobid_tei_with_abstract():
    """Test parsing GROBID TEI XML with abstract."""
    grobid_response = """<?xml version="1.0" encoding="UTF-8"?>
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
        <teiHeader>
            <fileDesc>
                <titleStmt>
                    <title type="main">Research Paper Title</title>
                </titleStmt>
                <sourceDesc>
                    <biblStruct>
                        <analytic>
                            <author>
                                <persName>
                                    <forename>Alice</forename>
                                    <surname>Wonder</surname>
                                </persName>
                            </author>
                        </analytic>
                    </biblStruct>
                </sourceDesc>
            </fileDesc>
            <profileDesc>
                <abstract>
                    <div>
                        <p>This is the abstract of the paper.</p>
                    </div>
                </abstract>
            </profileDesc>
        </teiHeader>
    </TEI>"""

    with patch("pathlib.Path.exists", return_value=True):
        parser = PDFParser("/test/file.pdf")
        metadata = parser._parse_grobid_tei(grobid_response)

        assert metadata["title"] == "Research Paper Title"
        assert metadata["author"] == "Alice Wonder"
        assert metadata["abstract"] == "This is the abstract of the paper."


def test_parse_grobid_tei_invalid_xml():
    """Test parsing invalid GROBID TEI XML."""
    invalid_xml = "This is not valid XML"

    with patch("pathlib.Path.exists", return_value=True):
        parser = PDFParser("/test/file.pdf")
        metadata = parser._parse_grobid_tei(invalid_xml)

        assert metadata is None


# Note: Full PDF parsing tests would require sample PDF files
# Additional tests can be implemented when sample PDFs are available
