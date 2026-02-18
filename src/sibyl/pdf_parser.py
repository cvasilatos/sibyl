"""PDF parsing utilities for extracting text from research papers."""

import pypdf
from typing import Optional
from pathlib import Path


class PDFParser:
    """Extract text content from PDF research papers."""

    def __init__(self, pdf_path: str):
        """Initialize the PDF parser.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    def extract_text(self, max_pages: Optional[int] = None) -> str:
        """Extract text from the PDF.

        Args:
            max_pages: Maximum number of pages to extract (None for all pages)

        Returns:
            Extracted text content
        """
        text_content = []

        with open(self.pdf_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages

            for page_num in range(pages_to_process):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_content.append(f"--- Page {page_num + 1} ---\n{text}")

        return "\n\n".join(text_content)

    def get_metadata(self) -> dict:
        """Extract metadata from the PDF.

        Returns:
            Dictionary containing PDF metadata
        """
        with open(self.pdf_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            metadata = pdf_reader.metadata

            return {
                "title": metadata.get("/Title", "Unknown"),
                "author": metadata.get("/Author", "Unknown"),
                "subject": metadata.get("/Subject", "Unknown"),
                "creator": metadata.get("/Creator", "Unknown"),
                "producer": metadata.get("/Producer", "Unknown"),
                "num_pages": len(pdf_reader.pages),
            }
