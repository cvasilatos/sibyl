"""Tests for the PDF parser module."""

import os
from pathlib import Path
from unittest.mock import patch

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
    assert parser._pdf_path == Path("/test/file.pdf")


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


def test_release_models_drops_the_cached_marker_models(monkeypatch):
    from sibyl.services import pdf_parser

    loads: list[str] = []
    monkeypatch.setattr(pdf_parser, "create_model_dict", lambda device: loads.append(device) or {})
    pdf_parser._marker_models.cache_clear()
    pdf_parser._marker_models("cpu")
    pdf_parser._marker_models("cpu")
    pdf_parser.release_models()
    pdf_parser._marker_models("cpu")
    pdf_parser._marker_models.cache_clear()
    assert loads == ["cpu", "cpu"]  # cached until released, then loaded again by the next review


def test_stage_reports_before_running_and_passes_attributes_through():
    from sibyl.services.pdf_parser import _Stage

    events: list[str] = []

    class Builder:
        disable_ocr = True

        def __call__(self, document, provider):
            events.append(f"ran {document} {provider}")
            return "result"

    stage = _Stage(Builder(), "Detecting text lines", 0.45, lambda message, done: events.append(f"{message} {done}"))

    assert stage("doc", "pdf") == "result"
    assert events == ["Detecting text lines 0.45", "ran doc pdf"]
    assert stage.disable_ocr is True


def test_stage_names_read_like_words():
    from sibyl.services.pdf_parser import _stage_name

    class SectionHeaderProcessor:
        pass

    class LLMTableProcessor:
        pass

    assert _stage_name(SectionHeaderProcessor()) == "section header"
    assert _stage_name(LLMTableProcessor()) == "llm table"


def test_converter_wraps_builders_and_leaves_other_objects(monkeypatch):
    from marker.builders.layout import LayoutBuilder
    from marker.converters.pdf import PdfConverter

    from sibyl.services.pdf_parser import _ReportingConverter, _Stage

    layout = object.__new__(LayoutBuilder)
    other = object()
    monkeypatch.setattr(PdfConverter, "resolve_dependencies", lambda _self, cls: layout if cls is LayoutBuilder else other)
    converter = object.__new__(_ReportingConverter)
    converter._report = lambda _message, _done: None

    wrapped = converter.resolve_dependencies(LayoutBuilder)
    assert isinstance(wrapped, _Stage)
    assert wrapped._stage is layout
    assert converter.resolve_dependencies(object) is other
