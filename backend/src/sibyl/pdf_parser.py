"""PDF parsing utilities for extracting text from research papers."""

import functools
import io
import logging
import os
import re
import threading
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, cast

from decima.logger import CustomLogger
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

from sibyl.hardware import torch_device

if TYPE_CHECKING:
    from pypdf._page import PageObject

import pypdf

logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


_device_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)


@functools.cache
def _marker_models(device: str) -> dict:
    """Load Marker's layout/OCR models once per device instead of on every review."""
    logger.info(f"Loading Marker models on {device}")
    return create_model_dict(device=device)


class PDFParser:
    """Extract text content from PDF research papers."""

    def __init__(self, pdf_path: str) -> None:
        """Initialize the PDF parser.

        Args:
            pdf_path: Path to the PDF file

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._pdf_path: str = pdf_path
        self._grobid_url: str = os.getenv("GROBID_URL", "http://localhost:8070")

    def extract_text(self, max_pages: int | None = None) -> str:
        """Extract text from the PDF.

        Args:
            max_pages: Maximum number of pages to extract (None for all pages)

        Returns:
            Extracted text content

        """
        text_content = []

        with Path(self._pdf_path).open("rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            total_pages: int = len(pdf_reader.pages)
            pages_to_process: int = min(total_pages, max_pages) if max_pages else total_pages

            for page_num in range(pages_to_process):
                page: PageObject = pdf_reader.pages[page_num]
                text: str = page.extract_text()
                if text:
                    text_content.append(f"--- Page {page_num + 1} ---\n{text}")

        return "\n\n".join(text_content)

    def get_metadata(self, ollama_host: int) -> dict:
        """Extract metadata from the PDF.

        Args:
            ollama_host: Review slot (0 = auto, n = GPU n-1); selects CUDA, Apple MPS, or CPU

        Returns:
            Dictionary containing PDF metadata

        """
        return self._extract_metadata_grobid(ollama_host)

    def _extract_metadata_grobid(self, ollama_host: int) -> dict:
        """Extract metadata using GROBID service.

        Returns:
            Dictionary containing PDF metadata from GROBID, or None if extraction fails

        """
        device = torch_device(ollama_host)
        with _device_locks[device]:  # cached models are shared, so convert one PDF per device at a time
            converter = PdfConverter(artifact_dict=_marker_models(device))
            rendered = converter(io.BytesIO(Path(self._pdf_path).read_bytes()))
        text, _, images = text_from_rendered(rendered)
        self.logger.info(f"Extracted {len(text)} characters and {len(images)} images from PDF")

        # ``images`` maps Marker's figure placeholders (``![](_page_N_Figure_M.jpeg)``) to cropped PIL images.
        return {"title": self.get_marker_title(text), "author": "author", "text": text, "images": images}

    def get_marker_title(self, markdown_text: str) -> str:
        """Return the first level-one or level-two heading in Markdown text."""
        # Search for the first Level 1 or Level 2 header
        match = re.search(r"^#\s+(.*)", markdown_text, re.MULTILINE)
        if not match:
            match = re.search(r"^##\s+(.*)", markdown_text, re.MULTILINE)

        if match:
            return match.group(1).strip()
        return "Title Not Found"
