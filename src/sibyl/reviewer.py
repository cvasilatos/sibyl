"""Research paper review framework."""

import importlib.resources as pkg_resources
import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decimalog.logger import CustomLogger
from pydantic import BaseModel, Field

from sibyl.llm.client.ollama import OllamaClient


class ReviewCriteria(BaseModel):
    """Criteria for reviewing research papers."""

    novelty: str = Field(description="Assessment of the novelty and originality of the research")
    methodology: str = Field(description="Evaluation of the research methodology and experimental design")
    results: str = Field(description="Analysis of the results and their significance")
    clarity: str = Field(description="Assessment of writing quality and presentation clarity")
    impact: str = Field(description="Potential impact and contribution to the field")
    limitations: str = Field(description="Identified limitations and weaknesses")
    strengths: str = Field(description="Key strengths of the paper")
    overall_score: int = Field(description="Overall score from 1-10", ge=1, le=10)
    recommendation: str = Field(description="Final recommendation (Accept/Revise/Reject)")
    detailed_feedback: str = Field(description="Detailed feedback and suggestions")


class PaperReview(BaseModel):
    """Complete review of a research paper."""

    paper_title: str
    reviewer_model: str
    criteria: ReviewCriteria
    raw_response: str


class ReviewSystem:
    """System for reviewing research papers using LLMs."""

    REVIEW_PROMPT_TEMPLATE: str = ""

    SYSTEM_PROMPT = """You are a senior researcher and expert peer reviewer with extensive experience in evaluating academic papers. You provide thorough, constructive, and balanced reviews that help authors improve their work."""

    def __init__(self, llm_client: OllamaClient) -> None:
        """Initialize the review system.

        Args:
            llm_client: LLM client to use for generating reviews

        """
        self._llm_client: OllamaClient = llm_client
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        # Load review prompt template from package resources
        try:
            self.REVIEW_PROMPT_TEMPLATE = pkg_resources.read_text("sibyl.resources", "review_prompt.md")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.logger.warning("Could not load review prompt resource: %s", exc)
            self.REVIEW_PROMPT_TEMPLATE = ""

    def review_paper(self, paper_text: str, paper_title: str, model_name: str) -> PaperReview:
        """Generate a review for a research paper.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper
            model_name: Name of the LLM model to use

        Returns:
            Structured review of the paper

        """
        self.logger.info(f"Starting synchronous review for paper: '{paper_title}'")
        prompt = self.REVIEW_PROMPT_TEMPLATE.format(paper_text=paper_text)
        self.logger.debug(f"Sending review prompt to LLM client: {self._llm_client.get_name()}")
        response: str = self._llm_client.generate(prompt, self.SYSTEM_PROMPT, model_name)
        self.logger.debug(f"Received response from LLM ({len(response)} chars), parsing...")
        criteria: ReviewCriteria = self._parse_review_response(response)
        self.logger.info(f"Review complete for '{paper_title}': score={criteria.overall_score}, recommendation={criteria.recommendation}")

        return PaperReview(
            paper_title=paper_title,
            reviewer_model=model_name,
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
        prompt: str = self.REVIEW_PROMPT_TEMPLATE.format(paper_text=paper_text)
        self.logger.debug(f"Sending async review prompt to LLM client: {model}")
        response: str = await self._llm_client.agenerate(prompt, model, system_prompt=self.SYSTEM_PROMPT)
        self.logger.debug(f"Received async response from LLM\n{response}")
        criteria: ReviewCriteria = self._parse_review_response(response)
        self.logger.info(f"Async review complete for '{paper_title}': score={criteria.overall_score}, recommendation={criteria.recommendation}")

        return PaperReview(
            paper_title=paper_title,
            reviewer_model=model,
            criteria=criteria,
            raw_response=response,
        )

    def _parse_review_response(self, response: str) -> ReviewCriteria:
        """Parse the LLM response into structured criteria.

        Args:
            response: Raw LLM response

        Returns:
            Structured review criteria

        """
        self.logger.debug(f"Parsing LLM review response ({len(response)} chars)")
        sections = {
            "novelty": "",
            "methodology": "",
            "results": "",
            "clarity": "",
            "impact": "",
            "limitations": "",
            "strengths": "",
            "overall_score": 5,
            "recommendation": "Revise",
            "detailed_feedback": "",
        }

        section_headers = [
            ("novelty", ["**NOVELTY:**", "NOVELTY:"]),
            ("methodology", ["**METHODOLOGY:**", "METHODOLOGY:"]),
            ("results", ["**RESULTS:**", "RESULTS:"]),
            ("clarity", ["**CLARITY:**", "CLARITY:"]),
            ("impact", ["**IMPACT:**", "IMPACT:"]),
            ("limitations", ["**LIMITATIONS:**", "LIMITATIONS:"]),
            ("strengths", ["**STRENGTHS:**", "STRENGTHS:"]),
            ("overall_score", ["**SCORE:**", "SCORE:"]),
            ("recommendation", ["**RECOMMENDATION:**", "RECOMMENDATION:"]),
            ("detailed_feedback", ["**DETAILED FEEDBACK:**", "DETAILED FEEDBACK:"]),
        ]

        lines: list[str] = response.split("\n")
        current_section = None
        score_parsed_from_header = False
        recommendation_parsed_from_header = False

        for line in lines:
            line_upper = line.strip().upper()
            header_found = False

            for section_key, headers in section_headers:
                for header in headers:
                    if line_upper.startswith(header.upper()):
                        current_section = section_key
                        content = line.replace(header, "").strip()

                        if section_key == "recommendation":
                            content = content.removeprefix("**").removesuffix("**").strip()

                        if content:
                            sections[current_section] = content

                        if section_key == "overall_score":
                            sections[current_section] = content
                        elif section_key == "recommendation":
                            recommendation_parsed_from_header = True

                        header_found = True
                        break
                if header_found:
                    break

            if not header_found and current_section and line.strip():
                if current_section == "recommendation":
                    if not recommendation_parsed_from_header:
                        sections[current_section] = line.strip()
                        recommendation_parsed_from_header = True
                    continue

                if sections[current_section]:
                    sections[current_section] += "\n" + line.strip()
                else:
                    sections[current_section] = line.strip()

        return ReviewCriteria(**sections)
