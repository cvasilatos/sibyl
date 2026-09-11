"""Research paper review framework."""

import importlib.resources as pkg_resources
import json
import logging
import os
from typing import TYPE_CHECKING, cast

from ollama import AsyncClient, GenerateResponse

if TYPE_CHECKING:
    from decima.logger import CustomLogger
from pydantic import BaseModel, Field

from sibyl.config import MAX_SCORE
from sibyl.web.model.llm_reply import FormAwareLLMReply, LLMReply

TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
FORM_TEMPERATURE: float = float(os.getenv("OLLAMA_FORM_TEMPERATURE", "0.2"))
MAX_TOKENS: int = int(os.getenv("OLLAMA_MAX_TOKENS", "30000"))


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


class ReviewSystem:
    """System for reviewing research papers using LLMs."""

    def __init__(self, client: AsyncClient, model: str) -> None:
        """Initialize the review system.

        Args:
            client: LLM client to use for generating reviews
            model: The default model name to use for reviews

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self._client: AsyncClient = client
        self._model: str = model
        self._system_prompt: str = pkg_resources.read_text("sibyl.resources", "review_prompt.md")

    async def review_paper(self, paper_text: str, paper_title: str, model: str, review_form: str | None = None) -> PaperReview:
        """Generate a review for a research paper.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper
            model: Name of the LLM model to use
            review_form: Optional plain-text or Markdown review form to complete

        Returns:
            Structured review of the paper

        """
        self.logger.info(f"Starting synchronous review for paper: '{paper_title}'")
        response_model: type[LLMReply] = FormAwareLLMReply if review_form else LLMReply
        response_schema = response_model.model_json_schema()
        form_section = ""
        if review_form:
            form_section = f"""
<review_form>
{review_form}
</review_form>

Complete the supplied review form in the review_form_response field.
"""

        prompt = f"""Review the research paper below.{form_section}
<research_paper>
{paper_text}
</research_paper>

Output JSON schema:
{json.dumps(response_schema, ensure_ascii=False)}
"""

        response: GenerateResponse = await self._client.generate(
            model=self._model,
            system=self._system_prompt,
            prompt=prompt,
            stream=False,
            options={"temperature": FORM_TEMPERATURE if review_form else TEMPERATURE, "num_predict": MAX_TOKENS},
            format=response_schema,
            keep_alive=0,
        )

        self.logger.warning(f"Received raw response from LLM for paper '{paper_title}': {response}\n\n\n\n")

        if not response.response:
            raise ValueError("Received empty response from LLM")

        self.logger.debug(f"Received response from LLM ({len(response.response)} chars), parsing...")
        criteria: LLMReply = response_model.model_validate_json(response.response)
        self.logger.info(f"Review complete for '{paper_title}': score={criteria.score}, recommendation={criteria.recommendation}")

        return PaperReview(
            paper_title=paper_title,
            reviewer_model=model,
            criteria=criteria,
            raw_response=response.response,
        )
