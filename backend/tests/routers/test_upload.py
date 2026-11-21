"""Tests for custom review-form uploads."""

import pytest
from fastapi import HTTPException

from sibyl.routers.upload import MAX_REVIEW_FORM_BYTES, _decode_review_form


@pytest.mark.parametrize("filename", ["review.txt", "review.md", "review.markdown", "REVIEW.MD"])
def test_decode_review_form(filename: str) -> None:
    """Decode every supported review-form extension as UTF-8 text."""
    form_content = "# Conference Review\n\n## Significance\n[Your answer]"

    assert _decode_review_form(filename, form_content.encode()) == form_content


def test_decode_review_form_strips_utf8_bom() -> None:
    """Allow common UTF-8 files that include a byte-order mark."""
    assert _decode_review_form("review.txt", b"\xef\xbb\xbfQuestion") == "Question"


@pytest.mark.parametrize("filename", ["review.pdf", "review.docx", "review"])
def test_upload_rejects_unsupported_review_form(filename: str) -> None:
    """Reject review forms that are not plain-text or Markdown files."""
    with pytest.raises(HTTPException, match="Review form must be") as error:
        _decode_review_form(filename, b"Questions")

    assert error.value.status_code == 400


def test_upload_rejects_empty_review_form() -> None:
    """Reject a review form that contains no usable text."""
    with pytest.raises(HTTPException, match="cannot be empty") as error:
        _decode_review_form("review.txt", b"  \n")

    assert error.value.status_code == 400


def test_upload_rejects_oversized_review_form() -> None:
    """Reject forms large enough to crowd the paper out of model context."""
    with pytest.raises(HTTPException, match="64 KiB or smaller") as error:
        _decode_review_form("review.txt", b"x" * (MAX_REVIEW_FORM_BYTES + 1))

    assert error.value.status_code == 413


def test_upload_rejects_non_utf8_review_form() -> None:
    """Reject binary content even when it has an allowed filename."""
    with pytest.raises(HTTPException, match="valid UTF-8") as error:
        _decode_review_form("review.md", b"\xff\xfe")

    assert error.value.status_code == 400
