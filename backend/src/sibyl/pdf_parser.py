"""PDF parsing utilities for extracting text from research papers."""

import io
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

from decima.logger import CustomLogger
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

if TYPE_CHECKING:
    from pypdf._page import PageObject

import pypdf

logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


class PDFParser:
    """Extract text content from PDF research papers."""

    def __init__(self, pdf_path: str) -> None:
        """Initialize the PDF parser.

        Args:
            pdf_path: Path to the PDF file

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
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

    def get_metadata(self, ollama_host: int) -> dict:
        """Extract metadata from the PDF.

        Args:
            ollama_host: The Ollama host number to use for GPU device assignment

        Returns:
            Dictionary containing PDF metadata

        """
        return self._extract_metadata_grobid(ollama_host)

    def _extract_metadata_grobid(self, ollama_host: int) -> dict:
        """Extract metadata using GROBID service.

        Returns:
            Dictionary containing PDF metadata from GROBID, or None if extraction fails

        """
        artifact_dict = create_model_dict(device=f"cuda:{ollama_host - 1}")
        converter = PdfConverter(
            artifact_dict=artifact_dict,
        )
        rendered = converter(io.BytesIO(Path(self._pdf_path).read_bytes()))
        self.logger.error("PDF rendered successfully, extracting text and images for metadata analysis...")
        text, _, images = text_from_rendered(rendered)

        self.logger.critical(f"Images: {images}")

        self.logger.error(f"Extracted text from PDF: {text}...")  # Log first 200 characters of extracted text
        self.logger.error(f"Extracted images from PDF: {len(images)} images found")

        return {"title": self.get_marker_title(text), "author": "author", "text": text}

        # url = f"{self._grobid_url}/api/processHeaderDocument"

        # with Path(self._pdf_path).open("rb") as pdf_file:
        #     files = {"input": pdf_file}
        #     # headers = {"Accept": "application/json"}
        #     response = requests.post(url, files=files, data={"json_output": "true"}, timeout=30)
        # self.logger.debug(f"GROBID response status: {response.status_code} - {response.text[:200]}...")

        # import grobid_tei_xml

        # doc: GrobidDocument = grobid_tei_xml.parse_document_xml(response.text)
        # logger.warning(f"GROBID document body: {doc.body}")
        # logger.warning(f"GROBID document body: {doc.grobid_timestamp}")
        # logger.debug(f"GROBID TEI XML document: {doc.to_dict()}")

        # raise Exception(f"GROBID request failed with status {response.status_code}: {response.text}")

    def get_marker_title(self, markdown_text: str) -> str:
        # Search for the first Level 1 or Level 2 header
        match = re.search(r"^#\s+(.*)", markdown_text, re.MULTILINE)
        if not match:
            match = re.search(r"^##\s+(.*)", markdown_text, re.MULTILINE)

        if match:
            return match.group(1).strip()
        return "Title Not Found"
