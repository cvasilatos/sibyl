"""PDF parsing utilities for extracting text from research papers."""

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decimalog.logger import CustomLogger
    from pypdf._page import PageObject

import pypdf
import requests

logger = logging.getLogger(__name__)


class PDFParser:
    """Extract text content from PDF research papers."""

    def __init__(self, pdf_path: str) -> None:
        """Initialize the PDF parser.

        Args:
            pdf_path: Path to the PDF file

        """
        logger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._grobid_url: str = os.getenv("GROBID_URL", "http://localhost:8070")
        self._pdf_path: str = pdf_path

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

    def get_metadata(self) -> dict:
        """Extract metadata from the PDF.

        Returns:
            Dictionary containing PDF metadata

        """
        pypdf_metadata = self._extract_metadata_pypdf()

        metadata_is_empty = pypdf_metadata.get("title") in (
            "Unknown",
            "",
            None,
        ) or pypdf_metadata.get("author") in ("Unknown", "", None)

        logger.info("PDF metadata is empty, attempting GROBID extraction...")
        grobid_metadata = self._extract_metadata_grobid()
        if grobid_metadata:
            pypdf_metadata.update(grobid_metadata)
            logger.info("Successfully extracted metadata using GROBID")

        return pypdf_metadata

    def _extract_metadata_pypdf(self) -> dict:
        """Extract metadata using pypdf.

        Returns:
            Dictionary containing PDF metadata from pypdf

        """
        with Path(self._pdf_path).open("rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            metadata = pdf_reader.metadata

            return {
                "title": metadata.get("/Title", "Unknown") if metadata else "Unknown",
                "author": metadata.get("/Author", "Unknown") if metadata else "Unknown",
                "subject": metadata.get("/Subject", "Unknown") if metadata else "Unknown",
                "creator": metadata.get("/Creator", "Unknown") if metadata else "Unknown",
                "producer": metadata.get("/Producer", "Unknown") if metadata else "Unknown",
                "num_pages": len(pdf_reader.pages),
            }

    def _extract_metadata_grobid(self) -> dict | None:
        """Extract metadata using GROBID service.

        Returns:
            Dictionary containing PDF metadata from GROBID, or None if extraction fails

        """
        url = f"{self._grobid_url}/api/processHeaderDocument"

        with Path(self._pdf_path).open("rb") as pdf_file:
            files = {"input": pdf_file}
            headers = {"Accept": "application/x-bibtex"}
            response = requests.post(url, files=files, headers=headers, timeout=30)

        logger.debug(f"GROBID response status: {response.status_code} - {response.text[:200]}")
        if response.status_code == 200 and response.text:
            return self._parse_grobid_bibtex(response.text)
        raise Exception(f"GROBID request failed with status {response.status_code}: {response.text}")

        return None

    def _parse_grobid_bibtex(self, bibtex: str) -> dict | None:
        """Parse a BibTeX string returned by GROBID to extract basic metadata.

        This is a lightweight parser that extracts `title`, `author`, and
        optionally `abstract` from a single BibTeX entry. It intentionally
        avoids adding an external dependency.
        """
        max_bibtex_size = 200 * 1024
        if len(bibtex) > max_bibtex_size:
            logger.warning(f"GROBID BibTeX response too large: {len(bibtex)} bytes")
            return None

        def _extract(field: str) -> str | None:
            pattern = rf"{field}\s*=\s*(?:\{{(.*?)\}}|\"(.*?)\")\s*,"
            m = re.search(pattern, bibtex, re.IGNORECASE | re.DOTALL)
            if not m:
                return None
            return (m.group(1) or m.group(2) or "").strip()

        title = _extract("title") or "Unknown"
        author = _extract("author") or "Unknown"
        abstract = _extract("abstract")

        metadata = {"title": title, "author": author}
        if abstract:
            metadata["abstract"] = abstract

        return metadata
