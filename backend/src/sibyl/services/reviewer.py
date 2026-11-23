"""Research paper review framework."""

from __future__ import annotations

import importlib.resources as pkg_resources
import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from sibyl.config import MAX_SCORE
from sibyl.inference.base import AUTO_SLOT, CHARS_PER_TOKEN, GenerationRequest, InferenceEngine, estimate_tokens
from sibyl.schemas.llm_reply import NARRATIVE_FIELDS, SIBYL_FILLED_FIELDS, FormAwareLLMReply, LLMReply
from sibyl.schemas.related_work import RelatedPaper  # noqa: TC001  # pydantic resolves PaperReview.related_work at runtime
from sibyl.schemas.review_config import ReviewConfig, ReviewDetail, ReviewMode
from sibyl.services.related_work import render_related_work

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sibyl.services.conferences import ConferenceTemplate

TEMPERATURE: float = float(os.getenv("SIBYL_TEMPERATURE", os.getenv("OLLAMA_TEMPERATURE", "0.7")))
FORM_TEMPERATURE: float = float(os.getenv("SIBYL_FORM_TEMPERATURE", os.getenv("OLLAMA_FORM_TEMPERATURE", "0.2")))


def _env_choice[E: StrEnum](name: str, enum: type[E], default: E) -> E:
    value = os.getenv(name, "").strip().lower()
    try:
        return enum(value) if value else default
    except ValueError:
        logging.getLogger(__name__).warning(f"Ignoring {name}={value!r}; expected one of {[e.value for e in enum]}")
        return default


DEFAULT_DETAIL: ReviewDetail = _env_choice("SIBYL_REVIEW_DETAIL", ReviewDetail, ReviewDetail.AUTO)
DEFAULT_MODE: ReviewMode = _env_choice("SIBYL_REVIEW_MODE", ReviewMode, ReviewMode.SINGLE)

OUTPUT_RESERVE: dict[ReviewDetail, int] = {ReviewDetail.AUTO: 6144, ReviewDetail.CONCISE: 3072, ReviewDetail.STANDARD: 6144, ReviewDetail.DETAILED: 12288}
"""Tokens kept free for the review when a long paper must be trimmed. Only a budget for trimming: the model may write
until the context window is full."""

_LENGTH: dict[ReviewDetail, tuple[str, int]] = {
    ReviewDetail.CONCISE: ("one focused paragraph (roughly 80-150 words) with only the most important points", 3),
    ReviewDetail.STANDARD: ("two or three developed paragraphs (roughly 200-400 words)", 5),
    ReviewDetail.DETAILED: ("four or more in-depth paragraphs (roughly 400-800 words)", 10),
}

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
    related_work: list[RelatedPaper] = Field(default_factory=list)
    config: ReviewConfig | None = None


def length_guidance(detail: ReviewDetail, unit: str | None = None, *, numbered_feedback: bool = True) -> str:
    """Tell the model how long to write, without a token limit.

    ``unit`` names the one section or answer of a section-by-section call; ``numbered_feedback`` asks for the detailed
    feedback (or, with ``unit``, this section) as a numbered list. ``auto`` returns nothing: the model decides.
    """
    if detail is ReviewDetail.AUTO:
        return ""
    size, points = _LENGTH[detail]
    grounding = "grounded in specific sections, equations, tables, figures, or experiments"
    if unit and numbered_feedback:
        text = f"Length: {detail.value}. Write this {unit} as a numbered list of at least {points} specific, actionable suggestions, each explained and {grounding}."
    else:
        target = f"Write this {unit}" if unit else "Write each review section, and each open-ended answer of a review form,"
        text = f"Length: {detail.value}. {target} as {size}, {grounding}."
        if numbered_feedback:
            text += f" Write detailed feedback as a numbered list of at least {points} specific, actionable suggestions."
    if detail is ReviewDetail.DETAILED:
        text += " Be exhaustive: cover every substantive issue, and do not summarize or stop early."
    return text


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


def verdict_schema(answers: dict[str, Any]) -> dict[str, Any]:
    """Build a schema with the given answer properties first, then the overall score and recommendation."""
    full = LLMReply.model_json_schema()
    properties = {**answers, "score": full["properties"]["score"], "recommendation": full["properties"]["recommendation"]}
    schema: dict[str, Any] = {"type": "object", "properties": properties, "required": list(properties)}
    if "$defs" in full:
        schema["$defs"] = full["$defs"]
    return schema


def form_schema(form_field: str, form_property: dict[str, Any]) -> dict[str, Any]:
    """Build the schema for a form review: only the completed form, then the overall score and recommendation.

    The narrative sections are left out on purpose so the model writes the review in the form's format only.
    """
    return verdict_schema({form_field: form_property})


def single_answer_schema(name: str, answer: dict[str, Any]) -> dict[str, Any]:
    """Build the schema for one section or form answer of a section-by-section review."""
    return {"type": "object", "properties": {name: answer}, "required": [name], "additionalProperties": False}


def section_label(name: str) -> str:
    """Display name of a default review section, e.g. ``detailed_feedback`` -> ``Detailed feedback``."""
    return name.replace("_", " ").capitalize()


def review_so_far(written: list[tuple[str, str]]) -> str:
    """Render the sections already written, so later calls stay consistent and do not repeat them."""
    if not written:
        return ""
    body = "\n\n".join(f"## {label}\n{text}" for label, text in written)
    return f"\n<your_review_so_far>\n{body}\n</your_review_so_far>\n"


def custom_form_schema() -> dict[str, Any]:
    """Build the schema for a user-supplied review form."""
    return form_schema("review_form_response", FormAwareLLMReply.model_json_schema()["properties"]["review_form_response"])


def conference_schema(conference: ConferenceTemplate) -> dict[str, Any]:
    """Build the schema for a conference review: the conference form (generated first), then score and recommendation."""
    return form_schema("conference_review", conference.json_schema())


@dataclass(slots=True)
class _Run:
    """Settings shared by the model calls of one review, and their raw outputs."""

    model: str
    temperature: float
    context_length: int
    slot: int
    on_status: Callable[[str], Awaitable[None]] | None
    parts: list[tuple[str, str]] = field(default_factory=list)

    def raw_response(self) -> str:
        """Return the model output: one JSON document, or one per call (labelled) for a section-by-section review."""
        if len(self.parts) == 1:
            return self.parts[0][1]
        return "\n\n".join(f"--- {name} ---\n{raw}" for name, raw in self.parts)


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
        related_work: list[RelatedPaper] | None = None,
        slot: int = AUTO_SLOT,
        on_status: Callable[[str], Awaitable[None]] | None = None,
        detail: ReviewDetail | None = None,
        mode: ReviewMode | None = None,
    ) -> PaperReview:
        """Generate a review for a research paper.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper
            model: Name of the LLM model to use (defaults to the one given at construction)
            review_form: Optional plain-text or Markdown review form to complete
            conference: Optional conference template whose official form must be answered
            related_work: Optional related papers found on arXiv, shown to the model to judge novelty
            slot: GPU slot (0 = auto, n = GPU n-1)
            on_status: Optional async callback for progress messages
            detail: How long the review should be (defaults to ``SIBYL_REVIEW_DETAIL``)
            mode: One generation or one per section (defaults to ``SIBYL_REVIEW_MODE``); custom forms always use one

        Returns:
            Structured review of the paper, with the settings that produced it in ``config``

        """
        if review_form and conference:
            raise ValueError("Use either a custom review form or a conference template, not both")
        model = model or self._model
        detail = detail or DEFAULT_DETAIL
        mode = mode or DEFAULT_MODE
        if mode is ReviewMode.SECTIONS and review_form:
            mode = ReviewMode.SINGLE
            if on_status:
                await on_status("A custom form has no fixed sections, so it is reviewed in one pass")
        self.logger.info(f"Starting review for paper '{paper_title}' with {model} (conference={conference.id if conference else None}, detail={detail}, mode={mode})")

        if conference:
            schema = conference_schema(conference)
            form_text = f"\n<conference_review_form>\n{conference.prompt_text()}\n</conference_review_form>\n"
            task = (
                f"Write the review exactly as a {conference.name} reviewer would, following the reviewer guidelines above. "
                "Answer every question of the form in the conference_review object, using the conference's own scales, "
                "then give the overall score and recommendation. Write the review only in this form's format."
            )
        elif review_form:
            schema = custom_form_schema()
            form_text = f"\n<review_form>\n{review_form}\n</review_form>\n"
            task = (
                "Complete the supplied review form in the review_form_response field, then give the overall score and recommendation. Write the review only in this form's format."
            )
        else:
            schema = default_schema()
            form_text = ""
            task = "Write the review."

        related_work = related_work or []
        related_text = f"\n{render_related_work(related_work)}\n" if related_work else ""

        schema_text = json.dumps(schema, ensure_ascii=False)
        guidance = length_guidance(detail)
        # The model gets the whole context window and may write until it is full; the reserve only decides how much
        # of a long paper to trim so the review has room.
        limit = await self._engine.context_window(model)
        overhead = estimate_tokens(self._system_prompt + form_text + related_text + schema_text + task + guidance) + 200
        paper_budget = max(limit - OUTPUT_RESERVE[detail] - overhead, 1024)
        paper_text, truncated = fit_paper(paper_text, paper_budget)
        if truncated:
            self.logger.warning(f"Paper '{paper_title}' exceeds the {limit}-token context; trimmed to ~{paper_budget} tokens")
            if on_status:
                await on_status(f"Paper is longer than the {limit}-token context; the end (references/appendix) was trimmed")

        # Everything that stays the same across calls comes first, so engines with prefix caching reuse it.
        shared = f"Review the research paper below.{form_text}{related_text}\n<research_paper>\n{paper_text}\n</research_paper>\n"
        temperature = FORM_TEMPERATURE if (review_form or conference) else TEMPERATURE
        run = _Run(model=model, temperature=temperature, context_length=limit, slot=slot, on_status=on_status)

        if mode is ReviewMode.SINGLE:
            raw = await self._generate(run, "review", f"{shared}\n{task}\n{guidance}\n\nOutput JSON schema:\n{schema_text}\n", schema, last=True)
            criteria = self._parse(raw, review_form=review_form, conference=conference)
        elif conference:
            criteria = await self._conference_in_sections(run, shared, conference, detail)
        else:
            criteria = await self._default_in_sections(run, shared, detail)

        self.logger.info(f"Review complete for '{paper_title}': score={criteria.score}, recommendation={criteria.recommendation}, calls={len(run.parts)}")
        config = ReviewConfig(
            engine=self._engine.name,
            model=model,
            detail=detail,
            mode=mode,
            temperature=temperature,
            context_length=limit,
            paper_truncated=truncated,
            generation_calls=len(run.parts),
            form="conference" if conference else "custom" if review_form else "default",
            conference=f"{conference.name} {conference.edition}" if conference else None,
        )
        return PaperReview(paper_title=paper_title, reviewer_model=model, criteria=criteria, raw_response=run.raw_response(), related_work=related_work, config=config)

    async def _generate(self, run: _Run, name: str, prompt: str, schema: dict[str, Any], *, last: bool, step: str | None = None) -> str:  # noqa: PLR0913
        """Run one schema-constrained call and return its JSON text; ``last`` lets the engine unload the model after it."""
        on_status = run.on_status
        if step and run.on_status:
            report = run.on_status
            await report(step)

            async def on_status(message: str) -> None:
                await report(f"{step}: {message}")

        request = GenerationRequest(
            model=run.model,
            system=self._system_prompt,
            prompt=prompt,
            schema=schema,
            temperature=run.temperature,
            context_length=run.context_length,
            slot=run.slot,
            on_status=on_status,
            keep_loaded=not last,
        )
        raw = await self._engine.generate_json(request)
        self.logger.debug(f"Raw response from {run.model} ({name}): {raw}")
        if not raw or not raw.strip():
            raise ValueError("Received empty response from LLM")
        run.parts.append((name, raw))
        return strip_reasoning(raw)

    async def _verdict(self, run: _Run, shared: str, written: list[tuple[str, str]], step: str, ratings: dict[str, Any] | None = None) -> dict[str, Any]:
        """Last call of a section-by-section review: the form's rating questions (if any), then score and recommendation."""
        schema = verdict_schema(ratings or {})
        ask = "answer the rating questions of the form, then give" if ratings else "give"
        prompt = (
            f"{shared}{review_so_far(written)}\nYou have written the review above. Now {ask} the overall score and recommendation, "
            f"consistent with the review.\n\nOutput JSON schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
        )
        return json.loads(await self._generate(run, "scores", prompt, schema, last=True, step=step))

    async def _default_in_sections(self, run: _Run, shared: str, detail: ReviewDetail) -> LLMReply:
        """Write Sibyl's default review one section per call, then score it."""
        written: list[tuple[str, str]] = []
        sections: dict[str, str] = {}
        total = len(NARRATIVE_FIELDS) + 1
        for i, name in enumerate(NARRATIVE_FIELDS, 1):
            label = section_label(name)
            description = LLMReply.model_fields[name].description or label
            schema = single_answer_schema(name, {"type": "string", "minLength": 1, "description": description})
            prompt = (
                f"{shared}{review_so_far(written)}\nYou are writing the review one section at a time. Write only the {label} section now: "
                f"{description}. Do not repeat points made in earlier sections.\n"
                f"{length_guidance(detail, 'section', numbered_feedback=name == 'detailed_feedback')}\n\n"
                f"Output JSON schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
            )
            text = await self._generate(run, name, prompt, schema, last=False, step=f"Section {i}/{total} ({label})")
            sections[name] = str(json.loads(text)[name]).strip()
            written.append((label, sections[name]))
        verdict = await self._verdict(run, shared, written, step=f"Section {total}/{total} (score and recommendation)")
        return LLMReply.model_validate({**sections, **verdict})

    async def _conference_in_sections(self, run: _Run, shared: str, conference: ConferenceTemplate, detail: ReviewDetail) -> LLMReply:
        """Answer each open question of a conference form in its own call, then the rating questions and scores together."""
        properties = conference.json_schema()["properties"]
        text_questions = [q for q in conference.questions if q.type == "text"]
        ratings = {q.id: properties[q.id] for q in conference.questions if q.type == "choice"}
        written: list[tuple[str, str]] = []
        answers: dict[str, Any] = {}
        total = len(text_questions) + 1
        for i, q in enumerate(text_questions, 1):
            schema = single_answer_schema(q.id, properties[q.id])
            prompt = (
                f"{shared}{review_so_far(written)}\nYou are filling in the {conference.name} reviewer form one question at a time, "
                f'following its reviewer guidelines. Answer only the question "{q.label}" (field `{q.id}`) now. '
                f"Do not repeat points made in earlier answers.\n{length_guidance(detail, 'answer', numbered_feedback=False)}\n\n"
                f"Output JSON schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
            )
            text = await self._generate(run, q.id, prompt, schema, last=False, step=f"Question {i}/{total} ({q.label})")
            answers[q.id] = json.loads(text)[q.id]
            written.append((q.label, str(answers[q.id]).strip()))
        verdict = await self._verdict(run, shared, written, step=f"Question {total}/{total} (ratings and recommendation)", ratings=ratings)
        answers |= {qid: verdict.pop(qid) for qid in ratings if qid in verdict}
        return self._conference_reply({**verdict, "conference_review": answers}, conference)

    @classmethod
    def _parse(cls, raw: str, review_form: str | None, conference: ConferenceTemplate | None) -> LLMReply:
        if conference is None:
            response_model: type[LLMReply] = FormAwareLLMReply if review_form else LLMReply
            return response_model.model_validate_json(raw)
        return cls._conference_reply(json.loads(raw), conference)

    @staticmethod
    def _conference_reply(data: dict[str, Any], conference: ConferenceTemplate) -> LLMReply:
        answers = conference.normalize_answers(data.pop("conference_review", None) or {})
        return LLMReply.model_validate(
            {
                **data,
                "review_form_response": conference.render_markdown(answers),
                "conference": conference.id,
                "review_form_answers": answers,
            }
        )
