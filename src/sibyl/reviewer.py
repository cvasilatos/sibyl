"""Research paper review framework."""

import importlib.resources as pkg_resources
import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decimalog.logger import CustomLogger
from pydantic import BaseModel, Field

from sibyl.llm.client.ollama import OllamaClient
from sibyl.web.model.llm_reply import LLMReply


class ReviewCriteria(BaseModel):
    """Criteria for reviewing research papers."""

    novelty: str = Field(description="Assessment of the novelty and originality of the research")
    methodology: str = Field(description="Evaluation of the research methodology and experimental design")
    results: str = Field(description="Analysis of the results and their significance")
    clarity: str = Field(description="Assessment of writing quality and presentation clarity")
    impact: str = Field(description="Potential impact and contribution to the field")
    limitations: str = Field(description="Identified limitations and weaknesses")
    strengths: str = Field(description="Key strengths of the paper")
    score: int = Field(description="Overall score from 1-10", ge=1, le=10)
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

    def __init__(self, llm_client: OllamaClient) -> None:
        """Initialize the review system.

        Args:
            llm_client: LLM client to use for generating reviews

        """
        self._llm_client: OllamaClient = llm_client
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self.prompt: str = pkg_resources.read_text("sibyl.resources", "review_prompt.md")

    def review_paper(self, paper_text: str, paper_title: str, model: str) -> PaperReview:
        """Generate a review for a research paper.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper
            model: Name of the LLM model to use

        Returns:
            Structured review of the paper

        """
        self.logger.info(f"Starting synchronous review for paper: '{paper_title}'")
        self.logger.debug(f"Sending review prompt to LLM client: {self._llm_client.get_name()}")
        response: str = self._llm_client.generate(self.prompt.format(paper_text=paper_text), model)
        self.logger.debug(f"Received response from LLM ({len(response)} chars), parsing...")
        criteria: LLMReply = LLMReply.model_validate_json(response)
        self.logger.info(f"Review complete for '{paper_title}': score={criteria.score}, recommendation={criteria.recommendation}")

        return PaperReview(
            paper_title=paper_title,
            reviewer_model=model,
            criteria=criteria,
            raw_response=response,
        )

    async def areview_paper(self, paper_text: str, paper_title: str, model: str) -> PaperReview:
        """Generate a review for a research paper asynchronously.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper
            model: Name of the LLM model to use
        Returns:
            Structured review of the paper

        """
        self.logger.info(f"Starting async review for paper: '{paper_title}'")
        prompt: str = self.prompt.format(paper_text=paper_text)
        self.logger.debug(f"Sending async review prompt to LLM client: {model}")
        response: str = await self._llm_client.agenerate(prompt, model)
        self.logger.debug(f"Received async response from LLM\n{response}")

        criteria: LLMReply = LLMReply.model_validate_json(response)
        self.logger.info(f"Async review complete for '{paper_title}': score={criteria.score}, recommendation={criteria.recommendation}")

        return PaperReview(
            paper_title=paper_title,
            reviewer_model=model,
            criteria=criteria,
            raw_response=response,
        )
