"""Research paper review framework."""

import logging
import re
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

    REVIEW_PROMPT_TEMPLATE = """You are an expert research paper reviewer. Please provide a comprehensive review in the following format for the following research paper:

Research Paper:
{paper_text}

Your review should cover:
1. Novelty and originality of the research
2. Methodology and experimental design
3. Results and their significance
4. Writing clarity and presentation
5. Potential impact and contribution to the field
6. Limitations and weaknesses
7. Key strengths

Please provide:
- An overall score from 1-10 (where 10 is excellent)
- A recommendation: Accept, Revise, or Reject
- Detailed feedback and suggestions for improvement

Format your response as follows:

NOVELTY:
[Your assessment of novelty and originality]

METHODOLOGY:
[Your evaluation of methodology]

RESULTS:
[Your analysis of results]

CLARITY:
[Your assessment of writing quality]

IMPACT:
[Your evaluation of potential impact]

LIMITATIONS:
[Identified limitations and weaknesses]

STRENGTHS:
[Key strengths of the paper]

SCORE:
[Overall score from 1-10]

RECOMMENDATION:
[Accept/Revise/Reject]

DETAILED FEEDBACK:
[Your detailed feedback and suggestions]

---

"""

    SYSTEM_PROMPT = """You are a senior researcher and expert peer reviewer with extensive experience in evaluating academic papers. You provide thorough, constructive, and balanced reviews that help authors improve their work."""

    def __init__(self, llm_client: OllamaClient) -> None:
        """Initialize the review system.

        Args:
            llm_client: LLM client to use for generating reviews

        """
        self._llm_client: OllamaClient = llm_client
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

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

    async def areview_paper(self, paper_text: str, paper_title: str, model_name: str) -> PaperReview:
        """Generate a review for a research paper asynchronously.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper

        Returns:
            Structured review of the paper

        """
        self.logger.info(f"Starting async review for paper: '{paper_title}'")
        prompt = self.REVIEW_PROMPT_TEMPLATE.format(paper_text=paper_text)
        self.logger.debug(f"Sending async review prompt to LLM client: {model_name}")
        response = await self._llm_client.agenerate(prompt, system_prompt=self.SYSTEM_PROMPT, model_name=model_name)
        self.logger.debug(f"Received async response from LLM ({len(response)} chars), parsing...")
        criteria = self._parse_review_response(response)
        self.logger.info(f"Async review complete for '{paper_title}': score={criteria.overall_score}, recommendation={criteria.recommendation}")

        return PaperReview(
            paper_title=paper_title,
            reviewer_model=model_name,
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
                            match = re.search(r"(\d+(?:\.\d+)?)", content)
                            if match:
                                try:
                                    score = float(match.group(1))
                                    sections[current_section] = int(score)
                                    score_parsed_from_header = True
                                except (ValueError, IndexError):
                                    sections[current_section] = 5
                                    score_parsed_from_header = True
                        elif section_key == "recommendation":
                            recommendation_parsed_from_header = True

                        header_found = True
                        break
                if header_found:
                    break

            if not header_found and current_section and line.strip():
                if current_section == "overall_score":
                    if not score_parsed_from_header:
                        try:
                            sections[current_section] = int("".join(c for c in line.strip() if c.isdigit())[:2])
                            score_parsed_from_header = True
                        except (ValueError, IndexError):
                            pass
                    continue

                if current_section == "recommendation":
                    if not recommendation_parsed_from_header:
                        sections[current_section] = line.strip()
                        recommendation_parsed_from_header = True
                    continue

                if sections[current_section]:
                    sections[current_section] += "\n" + line.strip()
                else:
                    sections[current_section] = line.strip()

        if sections["overall_score"] < 1:
            sections["overall_score"] = 1
        elif sections["overall_score"] > 10:
            sections["overall_score"] = 10

        if not sections["recommendation"]:
            sections["recommendation"] = "Revise"

        return ReviewCriteria(**sections)
