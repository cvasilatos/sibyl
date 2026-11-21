"""Ollama model catalog retrieval and parsing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable

    from ollama import ListResponse

_LIBRARY_URL = "https://ollama.com/library"
_MODEL_LINK_PATTERN = re.compile(r'href="/library/([^\"]+)')
_SIZE_TAG_PATTERN = re.compile(r"\d+(?:\.\d+)?[bBmMkK]")


class ModelCatalog:
    """Retrieve available models and combine them with local install state."""

    def __init__(self, client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient) -> None:
        """Create a catalog using the supplied HTTP client factory."""
        self._client_factory = client_factory

    async def list_available(self, installed: ListResponse) -> list[dict[str, object]]:
        """Return Ollama library models annotated with locally installed variants."""
        html = await self._fetch_html(_LIBRARY_URL)
        installed_variants = self._installed_variants(installed)

        return [
            {
                "name": name,
                "description": "Available from Ollama library",
                "size": "Unknown",
                # A library entry is a family, not a specific installed variant.
                "installed": False,
                "installed_variants": installed_variants.get(name, []),
            }
            for name in self.parse_model_names(html)
        ]

    async def list_tags(self, model_name: str) -> list[str]:
        """Return numerical size tags for an Ollama library model."""
        html = await self._fetch_html(f"{_LIBRARY_URL}/{model_name}")
        return self.parse_size_tags(html, model_name)

    async def _fetch_html(self, url: str) -> str:
        async with self._client_factory(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    @staticmethod
    def parse_model_names(html: str) -> list[str]:
        """Extract sorted, unique model names from a library page."""
        return sorted(set(_MODEL_LINK_PATTERN.findall(html)))

    @staticmethod
    def parse_size_tags(html: str, model_name: str) -> list[str]:
        """Extract sorted, unique numerical size tags from a model page."""
        link_pattern = re.compile(rf'href="/library/{re.escape(model_name)}:([^\"]+)"')
        return sorted({tag for tag in link_pattern.findall(html) if _SIZE_TAG_PATTERN.fullmatch(tag)})

    @staticmethod
    def _installed_variants(response: ListResponse) -> dict[str, list[str]]:
        variants: dict[str, list[str]] = {}
        for model in response.models:
            full_name = model.model or ""
            base_name, _, tag = full_name.partition(":")
            if base_name:
                variants.setdefault(base_name, []).append(tag or "latest")
        return variants
