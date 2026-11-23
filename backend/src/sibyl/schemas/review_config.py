"""How a review was produced: the settings recorded with every review so the library can show them."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ReviewDetail(StrEnum):
    """How long and thorough the review should be. Steers the model through the prompt; never a token limit.

    ``auto`` gives no length guidance at all: the model decides.
    """

    AUTO = "auto"
    CONCISE = "concise"
    STANDARD = "standard"
    DETAILED = "detailed"


class ReviewMode(StrEnum):
    """``single``: the whole review in one generation. ``sections``: one generation per section, then the scores."""

    SINGLE = "single"
    SECTIONS = "sections"


class ReviewConfig(BaseModel):
    """Settings used to produce a review. Reviews saved by older versions have none."""

    engine: str = Field(description="Inference engine (ollama, vllm, openai)")
    model: str = Field(description="Model that wrote the review")
    detail: ReviewDetail
    mode: ReviewMode = Field(description="Mode actually used; a custom form is always reviewed in a single pass")
    temperature: float
    context_length: int = Field(description="Context window in tokens; the review could use all of it left after the prompt")
    paper_truncated: bool = Field(default=False, description="The end of the paper was trimmed to fit the context")
    generation_calls: int = Field(default=1, description="Number of model calls that wrote the review")
    form: Literal["default", "conference", "custom"] = "default"
    conference: str | None = Field(default=None, description="Conference form, e.g. 'NeurIPS 2025'")
    review_form_name: str | None = Field(default=None, description="Name of the custom review form")
    vlm_model: str | None = Field(default=None, description="Vision model chosen to describe figures, or null when the step was off")
    figures_described: int = 0
    related_work: bool = Field(default=False, description="arXiv related-work search was enabled")
    gpu: int | None = Field(default=None, description="GPU index the review was requested on, or null for automatic")
    duration_seconds: float | None = Field(default=None, description="Time from PDF parsing to the finished review")
