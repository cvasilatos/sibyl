"""PDF parsing utilities for extracting text from research papers."""

import contextlib
import functools
import gc
import io
import logging
import os
import re
import threading
from collections import defaultdict
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from decima.logger import CustomLogger
from marker.builders.layout import LayoutBuilder
from marker.builders.line import LineBuilder
from marker.builders.ocr import OcrBuilder
from marker.builders.structure import StructureBuilder
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.renderers import BaseRenderer

from sibyl.services.hardware import torch_device

if TYPE_CHECKING:
    from pypdf._page import PageObject

import pypdf

logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


_device_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

type StageReport = Callable[[str, float], None]
"""Called (from the parsing thread) as each stage of the PDF conversion starts: ``(message, fraction of parsing done)``."""

_BUILDER_STAGES: tuple[tuple[type, str, float], ...] = (
    (LayoutBuilder, "Recognizing the page layout", 0.20),
    (LineBuilder, "Detecting text lines", 0.45),
    (OcrBuilder, "Recognizing text (OCR)", 0.60),
    (StructureBuilder, "Building the document structure", 0.75),
    (BaseRenderer, "Writing Markdown and exporting figure images", 0.95),
)
"""Marker's pipeline stages, in the order it runs them, with where each starts within parsing (rough share of time).
Model loading takes 0-15%, rendering the pages to images 15-20%, and the post-processors 77-95%."""
_PROCESSORS_START, _PROCESSORS_END = 0.77, 0.95


def _stage_name(stage: object) -> str:
    """Return a readable name for a Marker processor: ``SectionHeaderProcessor`` -> ``section header``."""
    name = type(stage).__name__.removesuffix("Processor")
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", name).lower()


class _Stage:
    """A Marker pipeline stage that reports before it runs; anything else is passed through to the stage."""

    def __init__(self, stage: Any, message: str, done: float, report: StageReport) -> None:  # noqa: ANN401
        self._stage = stage
        self._message = message
        self._done = done
        self._report = report

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        self._report(self._message, self._done)
        return self._stage(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        return getattr(self._stage, name)


class _ReportingConverter(PdfConverter):
    """Marker's PDF converter, reporting each stage (layout, lines, OCR, structure, post-processors, rendering)."""

    def __init__(self, artifact_dict: dict, report: StageReport) -> None:
        self._report = report
        super().__init__(artifact_dict=artifact_dict)
        processors: list[Any] = list(self.processor_list or [])  # Marker types the attribute loosely; it is a list here
        count = len(processors)
        width = _PROCESSORS_END - _PROCESSORS_START
        self.processor_list = [
            _Stage(processor, f"Post-processing ({index}/{count}): {_stage_name(processor)}", _PROCESSORS_START + width * (index - 1) / count, report)
            for index, processor in enumerate(processors, start=1)
        ]

    def resolve_dependencies(self, cls: type) -> Any:  # noqa: ANN401
        """Build a pipeline object as Marker does; the builders and the renderer are wrapped to report when they run."""
        resolved = super().resolve_dependencies(cls)
        for stage_cls, message, done in _BUILDER_STAGES:
            if isinstance(resolved, stage_cls):
                return _Stage(resolved, message, done, self._report)
        return resolved


def _ignore_stage(_message: str, _done: float) -> None:
    """Stage report used when the caller gave none."""


@functools.cache
def _marker_models(device: str) -> dict:
    """Load Marker's layout/OCR models once per device instead of on every review."""
    logger.info(f"Loading Marker models on {device}")
    return create_model_dict(device=device)


def release_models() -> None:
    """Drop the cached Marker models and return their GPU memory to the driver; the next review loads them again."""
    if _marker_models.cache_info().currsize == 0:
        return
    logger.info("Unloading Marker models")
    _marker_models.cache_clear()
    gc.collect()
    import torch  # noqa: PLC0415

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


@contextlib.contextmanager
def _default_cuda_device(device: str) -> Iterator[None]:
    """Make ``device`` (``cuda:N``) the current thread's default CUDA device; no-op for CPU and MPS."""
    if not device.startswith("cuda:"):
        yield
        return
    import torch  # noqa: PLC0415

    with torch.cuda.device(int(device.split(":", 1)[1])):
        yield


class PDFParser:
    """Extract text content from PDF research papers."""

    def __init__(self, pdf_path: str | Path) -> None:
        """Initialize the PDF parser.

        Args:
            pdf_path: Path to the PDF file

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._pdf_path: Path = Path(pdf_path)
        self._grobid_url: str = os.getenv("GROBID_URL", "http://localhost:8070")

    def extract_text(self, max_pages: int | None = None) -> str:
        """Extract text from the PDF.

        Args:
            max_pages: Maximum number of pages to extract (None for all pages)

        Returns:
            Extracted text content

        """
        text_content = []

        with self._pdf_path.open("rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            total_pages: int = len(pdf_reader.pages)
            pages_to_process: int = min(total_pages, max_pages) if max_pages else total_pages

            for page_num in range(pages_to_process):
                page: PageObject = pdf_reader.pages[page_num]
                text: str = page.extract_text()
                if text:
                    text_content.append(f"--- Page {page_num + 1} ---\n{text}")

        return "\n\n".join(text_content)

    def get_metadata(self, ollama_host: int, on_stage: StageReport | None = None) -> dict:
        """Extract metadata from the PDF.

        Args:
            ollama_host: Review slot (0 = auto, n = GPU n-1); selects CUDA, Apple MPS, or CPU
            on_stage: Optional callback, called from this thread as each conversion stage starts

        Returns:
            Dictionary containing PDF metadata

        """
        return self._extract_metadata_grobid(ollama_host, on_stage or _ignore_stage)

    def _extract_metadata_grobid(self, ollama_host: int, report: StageReport) -> dict:
        """Extract metadata using GROBID service.

        Returns:
            Dictionary containing PDF metadata from GROBID, or None if extraction fails

        """
        device = torch_device(ollama_host)
        # Cached models are shared, so convert one PDF per device at a time. Making the device the thread's default CUDA
        # device keeps anything Marker allocates on a bare "cuda" on the selected GPU instead of GPU 0.
        with _device_locks[device], _default_cuda_device(device):
            report(f"Loading the PDF models on {device}", 0.0)
            converter = _ReportingConverter(_marker_models(device), report)
            report("Rendering the pages", 0.15)
            rendered = converter(io.BytesIO(self._pdf_path.read_bytes()))
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
