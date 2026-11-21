"""Research paper review framework."""

from __future__ import annotations

import importlib.resources as pkg_resources
import json
import logging
import os
import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from sibyl.config import MAX_SCORE
from sibyl.inference.base import AUTO_SLOT, GenerationRequest, InferenceEngine, env_int
from sibyl.schemas.llm_reply import NARRATIVE_FIELDS, SIBYL_FILLED_FIELDS, FormAwareLLMReply, LLMReply

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sibyl.services.conferences import ConferenceTemplate

TEMPERATURE: float = float(os.getenv("SIBYL_TEMPERATURE", os.getenv("OLLAMA_TEMPERATURE", "0.7")))
FORM_TEMPERATURE: float = float(os.getenv("SIBYL_FORM_TEMPERATURE", os.getenv("OLLAMA_FORM_TEMPERATURE", "0.2")))
MAX_TOKENS: int = env_int("SIBYL_MAX_OUTPUT_TOKENS", env_int("OLLAMA_MAX_TOKENS", 8192))

CHARS_PER_TOKEN = 3.0
"""Conservative estimate for English scientific text with Markdown/LaTeX (real ratio is ~3.5-4)."""
MIN_CONTEXT = 8192
CONTEXT_STEP = 2048

_THINK_BLOCK = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)


class ReviewCriteria(BaseModel):
    """Criteria for reviewing research papers."""

    novelty: str = Field(description="Assessment of the novelty and originality of the research")
    methodology: str = Field(description="Evaluation of the research methodology and experimental design")
    results: str = Field(description="Analysis of the results and their significance")
    clarity: str = Field(description="Assessment of writing quality and presentation clarity")
    impact: str = Field(description="Potential impact and contribution to the field")
    limitations: str = Field(description="Identified limitations and weaknesses")
    strengths: str = Field(description="Key strengths of the paper")
    score: int = Field(description=f"Overall score from 1-{MAX_SCORE}", ge=1, le=MAX_SCORE)
    recommendation: str = Field(description="Final recommendation (Accept/Revise/Reject)")
    detailed_feedback: str = Field(description="Detailed feedback and suggestions")


class PaperReview(BaseModel):
    """Complete review of a research paper."""

    paper_title: str
    reviewer_model: str
    criteria: LLMReply
    raw_response: str


def estimate_tokens(text: str) -> int:
    """Rough token count used for context budgeting."""
    return int(len(text) / CHARS_PER_TOKEN) + 1


def context_window(prompt_tokens: int, max_output_tokens: int, limit: int) -> int:
    """Smallest context (rounded up to ``CONTEXT_STEP``) that fits prompt and output, capped at ``limit``."""
    needed = prompt_tokens + max_output_tokens
    rounded = -(-needed // CONTEXT_STEP) * CONTEXT_STEP
    return max(min(rounded, limit), min(MIN_CONTEXT, limit))


def fit_paper(paper_text: str, max_tokens: int) -> tuple[str, bool]:
    """Trim the end of the paper (references/appendices) so it fits in ``max_tokens``."""
    max_chars = int(max_tokens * CHARS_PER_TOKEN)
    if len(paper_text) <= max_chars:
        return paper_text, False
    return paper_text[:max_chars] + "\n\n[... remainder of the paper truncated to fit the model context ...]", True


def strip_reasoning(text: str) -> str:
    """Remove a leading ``<think>`` block emitted by reasoning models before the JSON."""
    return _THINK_BLOCK.sub("", text, count=1).strip()


def default_schema() -> dict[str, Any]:
    """Build the schema for a review without a form: Sibyl's narrative sections plus score and recommendation."""
    schema = LLMReply.model_json_schema()
    for name in (*SIBYL_FILLED_FIELDS, "review_form_response"):
        schema["properties"].pop(name, None)
    schema["required"] = [*NARRATIVE_FIELDS, "score", "recommendation"]
    return schema


def form_schema(form_field: str, form_property: dict[str, Any]) -> dict[str, Any]:
    """Build the schema for a form review: only the completed form, then the overall score and recommendation.

    The narrative sections are left out on purpose so the model writes the review in the form's format only.
    """
    full = LLMReply.model_json_schema()
    properties = {form_field: form_property, "score": full["properties"]["score"], "recommendation": full["properties"]["recommendation"]}
    schema: dict[str, Any] = {"type": "object", "properties": properties, "required": list(properties)}
    if "$defs" in full:
        schema["$defs"] = full["$defs"]
    return schema


def custom_form_schema() -> dict[str, Any]:
    """Build the schema for a user-supplied review form."""
    return form_schema("review_form_response", FormAwareLLMReply.model_json_schema()["properties"]["review_form_response"])


def conference_schema(conference: ConferenceTemplate) -> dict[str, Any]:
    """Build the schema for a conference review: the conference form (generated first), then score and recommendation."""
    return form_schema("conference_review", conference.json_schema())


class ReviewSystem:
    """System for reviewing research papers using LLMs."""

    def __init__(self, engine: InferenceEngine, model: str) -> None:
        """Initialize the review system.

        Args:
            engine: Inference engine used to run the model
            model: The model name to use for reviews

        """
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._engine = engine
        self._model = model
        self._system_prompt: str = pkg_resources.files("sibyl.resources").joinpath("review_prompt.md").read_text(encoding="utf-8")

    async def review_paper(  # noqa: PLR0913
        self,
        paper_text: str,
        paper_title: str,
        model: str | None = None,
        review_form: str | None = None,
        conference: ConferenceTemplate | None = None,
        slot: int = AUTO_SLOT,
        on_status: Callable[[str], Awaitable[None]] | None = None,
    ) -> PaperReview:
        """Generate a review for a research paper.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper
            model: Name of the LLM model to use (defaults to the one given at construction)
            review_form: Optional plain-text or Markdown review form to complete
            conference: Optional conference template whose official form must be answered
            slot: GPU slot (0 = auto, n = GPU n-1)
            on_status: Optional async callback for progress messages

        Returns:
            Structured review of the paper

        """
        if review_form and conference:
            raise ValueError("Use either a custom review form or a conference template, not both")
        model = model or self._model
        self.logger.info(f"Starting review for paper '{paper_title}' with {model} (conference={conference.id if conference else None})")

        if conference:
            schema = conference_schema(conference)
            instructions = (
                f"\n<conference_review_form>\n{conference.prompt_text()}\n</conference_review_form>\n\n"
                f"Write the review exactly as a {conference.name} reviewer would, following the reviewer guidelines above. "
                "Answer every question of the form in the conference_review object, using the conference's own scales, "
                "then give the overall score and recommendation. Write the review only in this form's format.\n"
            )
        elif review_form:
            schema = custom_form_schema()
            instructions = (
                f"\n<review_form>\n{review_form}\n</review_form>\n\n"
                "Complete the supplied review form in the review_form_response field, then give the overall score and "
                "recommendation. Write the review only in this form's format.\n"
            )
        else:
            schema = default_schema()
            instructions = ""

        schema_text = json.dumps(schema, ensure_ascii=False)
        limit = self._engine.context_length(model)
        overhead = estimate_tokens(self._system_prompt + instructions + schema_text) + 200
        paper_budget = max(limit - MAX_TOKENS - overhead, 1024)
        paper_text, truncated = fit_paper(paper_text, paper_budget)
        if truncated:
            self.logger.warning(f"Paper '{paper_title}' exceeds the {limit}-token context; trimmed to ~{paper_budget} tokens")
            if on_status:
                await on_status(f"Paper is longer than the {limit}-token context; the end (references/appendix) was trimmed")

        prompt = f"Review the research paper below.{instructions}\n<research_paper>\n{paper_text}\n</research_paper>\n\nOutput JSON schema:\n{schema_text}\n"
        request = GenerationRequest(
            model=model,
            system=self._system_prompt,
            prompt=prompt,
            schema=schema,
            temperature=FORM_TEMPERATURE if (review_form or conference) else TEMPERATURE,
            max_tokens=MAX_TOKENS,
            context_length=context_window(estimate_tokens(self._system_prompt + prompt), MAX_TOKENS, limit),
            slot=slot,
            on_status=on_status,
        )
        raw = await self._engine.generate_json(request)
        self.logger.debug(f"Raw response from {model} for '{paper_title}': {raw}")

        if not raw or not raw.strip():
            raise ValueError("Received empty response from LLM")

        criteria = self._parse(strip_reasoning(raw), review_form=review_form, conference=conference)
        self.logger.info(f"Review complete for '{paper_title}': score={criteria.score}, recommendation={criteria.recommendation}")
        return PaperReview(paper_title=paper_title, reviewer_model=model, criteria=criteria, raw_response=raw)

    @staticmethod
    def _parse(raw: str, review_form: str | None, conference: ConferenceTemplate | None) -> LLMReply:
        if conference is None:
            response_model: type[LLMReply] = FormAwareLLMReply if review_form else LLMReply
            return response_model.model_validate_json(raw)

        data = json.loads(raw)
        answers = conference.normalize_answers(data.pop("conference_review", None) or {})
        return LLMReply.model_validate(
            {
                **data,
                "review_form_response": conference.render_markdown(answers),
                "conference": conference.id,
                "review_form_answers": answers,
            }
        )
