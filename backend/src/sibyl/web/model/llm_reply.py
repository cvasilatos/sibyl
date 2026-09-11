from enum import StrEnum

from pydantic import BaseModel, Field

from sibyl.config import MAX_SCORE


class Recommendation(StrEnum):
    """Enumeration of possible review recommendations."""

    ACCEPT = "Accept"
    MINOR_REVISION = "Minor Revision"
    MAJOR_REVISION = "Major Revision"
    REJECT = "Reject"


class LLMReply(BaseModel):
    """Structured reply from an LLM for a paper review."""

    novelty: str = Field(..., description="Assessment of novelty and originality")
    methodology: str = Field(..., description="Evaluation of methodology and experimental design")
    results: str = Field(..., description="Analysis of results and their significance")
    clarity: str = Field(..., description="Assessment of writing quality, clarity and presentation")
    impact: str = Field(..., description="Evaluation of potential impact and contribution to the field")
    limitations: str = Field(..., description="Identified limitations and weaknesses")
    strengths: str = Field(..., description="Key strengths")
    score: int = Field(..., ge=1, le=MAX_SCORE, description=f"Overall score from 1-{MAX_SCORE}")
    recommendation: Recommendation = Field(..., description="Accept/Minor Revision/Major Revision/Reject")
    detailed_feedback: str = Field(..., description="Detailed feedback and suggestions for improvement")
    review_form_response: str | None = Field(
        default=None,
        description="Completed response matching the user-supplied review form, or null when no form was supplied",
    )


class FormAwareLLMReply(LLMReply):
    """Structured reply used when a custom review form must be completed."""

    review_form_response: str = Field(
        ...,
        min_length=1,
        description="Completed response matching every applicable section of the user-supplied review form",
    )
