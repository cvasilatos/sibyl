from enum import Enum

from pydantic import BaseModel, Field


class Recommendation(str, Enum):
    ACCEPT = "Accept"
    MINOR_REVISION = "Minor Revision"
    MAJOR_REVISION = "Major Revision"
    REJECT = "Reject"


class LLMReply(BaseModel):
    novelty: str = Field(..., description="Assessment of novelty and originality")
    methodology: str = Field(..., description="Evaluation of methodology and experimental design")
    results: str = Field(..., description="Analysis of results and their significance")
    clarity: str = Field(..., description="Assessment of writing quality, clarity and presentation")
    impact: str = Field(..., description="Evaluation of potential impact and contribution to the field")
    limitations: str = Field(..., description="Identified limitations and weaknesses")
    strengths: str = Field(..., description="Key strengths")
    score: int = Field(..., ge=1, le=5, description="Overall score from 1-5")
    recommendation: Recommendation = Field(..., description="Accept/Minor Revision/Major Revision/Reject")
    detailed_feedback: str = Field(..., description="Detailed feedback and suggestions for improvement")
