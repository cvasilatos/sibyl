"""PDF parsing utilities for extracting text from research papers."""

import logging
import os
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import pypdf
import requests

logger = logging.getLogger(__name__)


class PDFParser:
    """Extract text content from PDF research papers."""

    def __init__(
        self,
        pdf_path: str,
        grobid_url: Optional[str] = None,
        *,
        use_grobid: Optional[bool] = None,
    ):
        """Initialize the PDF parser.

        Args:
            pdf_path: Path to the PDF file
            grobid_url: URL of GROBID service (e.g., "http://localhost:8070")
            use_grobid: Whether to use GROBID for metadata extraction.
                       If None, will be determined by GROBID_ENABLED env var.
                       Defaults to True if grobid_url is provided.

        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Configure GROBID
        self.grobid_url = grobid_url or os.getenv("GROBID_URL", "http://localhost:8070")

        # Determine if GROBID should be used
        if use_grobid is None:
            # Default: use GROBID if enabled in env or if URL is explicitly provided
            env_enabled = os.getenv("GROBID_ENABLED", "false").lower() in ("true", "1", "yes")
            self.use_grobid = env_enabled or (grobid_url is not None)
        else:
            self.use_grobid = use_grobid

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
        # First, try pypdf to get basic metadata
        pypdf_metadata = self._extract_metadata_pypdf()

        # Check if metadata is empty/unknown
        metadata_is_empty = (
            pypdf_metadata.get("title") in ("Unknown", "", None)
            or pypdf_metadata.get("author") in ("Unknown", "", None)
        )

        # If metadata is empty and GROBID is enabled, try GROBID
        if metadata_is_empty and self.use_grobid:
            logger.info("PDF metadata is empty, attempting GROBID extraction...")
            grobid_metadata = self._extract_metadata_grobid()
            if grobid_metadata:
                # Merge GROBID metadata with pypdf metadata
                # GROBID takes precedence for title and author
                pypdf_metadata.update(grobid_metadata)
                logger.info("Successfully extracted metadata using GROBID")
            else:
                logger.warning("GROBID extraction failed, using pypdf metadata")

        return pypdf_metadata

    def _extract_metadata_pypdf(self) -> dict:
        """Extract metadata using pypdf.

        Returns:
            Dictionary containing PDF metadata from pypdf

        """
        with open(self.pdf_path, "rb") as file:
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

    def _extract_metadata_grobid(self) -> Optional[dict]:
        """Extract metadata using GROBID service.

        Returns:
            Dictionary containing PDF metadata from GROBID, or None if extraction fails

        """
        try:
            # Use processHeaderDocument endpoint for metadata-only extraction
            url = f"{self.grobid_url}/api/processHeaderDocument"

            with open(self.pdf_path, "rb") as pdf_file:
                files = {"input": pdf_file}
                # Set a reasonable timeout
                response = requests.post(url, files=files, timeout=30)

            if response.status_code == 200:
                # Parse the TEI XML response
                return self._parse_grobid_tei(response.text)

            logger.warning(
                f"GROBID request failed with status {response.status_code}: {response.text}"
            )

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to connect to GROBID service at {self.grobid_url}: {e}")
        except Exception as e:
            logger.warning(f"Error during GROBID metadata extraction: {e}")

        return None

    def _parse_grobid_tei(self, tei_xml: str) -> Optional[dict]:
        """Parse GROBID TEI XML response to extract metadata.

        Args:
            tei_xml: TEI XML string from GROBID

        Returns:
            Dictionary containing extracted metadata

        Note:
            The XML is from GROBID service (configured by user) and is trusted.

        """
        try:
            root = ET.fromstring(tei_xml)  # noqa: S314

            # Define TEI namespace
            ns = {"tei": "http://www.tei-c.org/ns/1.0"}

            # Extract title
            title_elem = root.find(".//tei:titleStmt/tei:title[@type='main']", ns)
            if title_elem is None:
                title_elem = root.find(".//tei:titleStmt/tei:title", ns)
            title = title_elem.text if title_elem is not None and title_elem.text else "Unknown"

            # Extract authors
            authors = []
            author_elems = root.findall(".//tei:sourceDesc//tei:author", ns)
            for author_elem in author_elems:
                # Try to get forename and surname
                forename = author_elem.find(".//tei:forename", ns)
                surname = author_elem.find(".//tei:surname", ns)

                if forename is not None and surname is not None:
                    full_name = f"{forename.text} {surname.text}"
                    authors.append(full_name)
                elif surname is not None:
                    authors.append(surname.text)
                elif forename is not None:
                    authors.append(forename.text)

            author_str = ", ".join(authors) if authors else "Unknown"

            # Extract abstract (optional, for potential future use)
            abstract_elem = root.find(".//tei:profileDesc//tei:abstract/tei:div/tei:p", ns)
            abstract = (
                abstract_elem.text if abstract_elem is not None and abstract_elem.text else None
            )

            metadata = {
                "title": title,
                "author": author_str,
            }

            if abstract:
                metadata["abstract"] = abstract

        except ET.ParseError as e:
            logger.warning(f"Failed to parse GROBID TEI XML: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing GROBID response: {e}")
            return None
        else:
            return metadata
