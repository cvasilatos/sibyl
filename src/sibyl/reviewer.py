"""Research paper review framework."""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from .llm_client import LLMClient


class ReviewCriteria(BaseModel):
    """Criteria for reviewing research papers."""

    novelty: str = Field(description="Assessment of the novelty and originality of the research")
    methodology: str = Field(
        description="Evaluation of the research methodology and experimental design"
    )
    results: str = Field(description="Analysis of the results and their significance")
    clarity: str = Field(
        description="Assessment of writing quality and presentation clarity"
    )
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

    REVIEW_PROMPT_TEMPLATE = """You are an expert research paper reviewer. Please provide a comprehensive review of the following research paper.

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

Research Paper:
{paper_text}
"""

    SYSTEM_PROMPT = """You are a senior researcher and expert peer reviewer with extensive experience in evaluating academic papers. You provide thorough, constructive, and balanced reviews that help authors improve their work."""

    def __init__(self, llm_client: LLMClient):
        """Initialize the review system.

        Args:
            llm_client: LLM client to use for generating reviews
        """
        self.llm_client = llm_client

    def review_paper(self, paper_text: str, paper_title: str = "Unknown") -> PaperReview:
        """Generate a review for a research paper.

        Args:
            paper_text: The full text of the research paper
            paper_title: Title of the paper

        Returns:
            Structured review of the paper
        """
        # Generate the review using the LLM
        prompt = self.REVIEW_PROMPT_TEMPLATE.format(paper_text=paper_text)
        response = self.llm_client.generate(prompt, system_prompt=self.SYSTEM_PROMPT)

        # Parse the response
        criteria = self._parse_review_response(response)

        return PaperReview(
            paper_title=paper_title,
            reviewer_model=self.llm_client.get_name(),
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

        # Parse sections from the response
        lines = response.split("\n")
        current_section = None

        for line in lines:
            line_upper = line.strip().upper()

            if line_upper.startswith("NOVELTY:"):
                current_section = "novelty"
                sections[current_section] = line[8:].strip()
            elif line_upper.startswith("METHODOLOGY:"):
                current_section = "methodology"
                sections[current_section] = line[12:].strip()
            elif line_upper.startswith("RESULTS:"):
                current_section = "results"
                sections[current_section] = line[8:].strip()
            elif line_upper.startswith("CLARITY:"):
                current_section = "clarity"
                sections[current_section] = line[8:].strip()
            elif line_upper.startswith("IMPACT:"):
                current_section = "impact"
                sections[current_section] = line[7:].strip()
            elif line_upper.startswith("LIMITATIONS:"):
                current_section = "limitations"
                sections[current_section] = line[12:].strip()
            elif line_upper.startswith("STRENGTHS:"):
                current_section = "strengths"
                sections[current_section] = line[10:].strip()
            elif line_upper.startswith("SCORE:"):
                current_section = "overall_score"
                score_text = line[6:].strip()
                # Extract number from score text
                try:
                    sections[current_section] = int("".join(c for c in score_text if c.isdigit())[:2])
                except (ValueError, IndexError):
                    sections[current_section] = 5
            elif line_upper.startswith("RECOMMENDATION:"):
                current_section = "recommendation"
                sections[current_section] = line[15:].strip()
            elif line_upper.startswith("DETAILED FEEDBACK:"):
                current_section = "detailed_feedback"
                sections[current_section] = line[18:].strip()
            elif current_section and line.strip():
                # Continue appending to current section
                if sections[current_section] and current_section not in [
                    "overall_score",
                    "recommendation",
                ]:
                    sections[current_section] += "\n" + line.strip()
                elif current_section not in ["overall_score", "recommendation"]:
                    sections[current_section] = line.strip()

        # Ensure score is within valid range
        if sections["overall_score"] < 1:
            sections["overall_score"] = 1
        elif sections["overall_score"] > 10:
            sections["overall_score"] = 10

        return ReviewCriteria(**sections)
