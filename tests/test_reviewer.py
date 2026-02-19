"""Tests for the reviewer module."""

import pytest
from unittest.mock import Mock

from sibyl.reviewer import PaperReview, ReviewCriteria, ReviewSystem


def test_review_criteria_creation():
    """Test creating review criteria."""
    criteria = ReviewCriteria(
        novelty="High novelty",
        methodology="Strong methodology",
        results="Significant results",
        clarity="Clear writing",
        impact="High impact",
        limitations="Minor limitations",
        strengths="Multiple strengths",
        overall_score=8,
        recommendation="Accept",
        detailed_feedback="Well done",
    )

    assert criteria.novelty == "High novelty"
    assert criteria.overall_score == 8
    assert criteria.recommendation == "Accept"


def test_review_criteria_score_validation():
    """Test score validation in review criteria."""
    with pytest.raises(ValueError):
        ReviewCriteria(
            novelty="Test",
            methodology="Test",
            results="Test",
            clarity="Test",
            impact="Test",
            limitations="Test",
            strengths="Test",
            overall_score=11,  # Invalid: > 10
            recommendation="Accept",
            detailed_feedback="Test",
        )


def test_paper_review_creation():
    """Test creating a paper review."""
    criteria = ReviewCriteria(
        novelty="High",
        methodology="Strong",
        results="Good",
        clarity="Clear",
        impact="High",
        limitations="Minor",
        strengths="Many",
        overall_score=8,
        recommendation="Accept",
        detailed_feedback="Good work",
    )

    review = PaperReview(
        paper_title="Test Paper",
        reviewer_model="TestModel",
        criteria=criteria,
        raw_response="Test response",
    )

    assert review.paper_title == "Test Paper"
    assert review.reviewer_model == "TestModel"
    assert review.criteria.overall_score == 8


def test_parse_review_response_with_content_on_same_line():
    """Test parsing LLM response when content is on the same line as headers."""
    mock_client = Mock()
    reviewer = ReviewSystem(mock_client)
    
    response = """NOVELTY: High novelty and originality
METHODOLOGY: Strong methodology
RESULTS: Significant results
CLARITY: Clear writing
IMPACT: High impact potential
LIMITATIONS: Minor limitations noted
STRENGTHS: Multiple key strengths
SCORE: 8
RECOMMENDATION: Accept
DETAILED FEEDBACK: Well-written paper with solid contributions"""
    
    criteria = reviewer._parse_review_response(response)
    
    assert criteria.novelty == "High novelty and originality"
    assert criteria.methodology == "Strong methodology"
    assert criteria.results == "Significant results"
    assert criteria.clarity == "Clear writing"
    assert criteria.impact == "High impact potential"
    assert criteria.limitations == "Minor limitations noted"
    assert criteria.strengths == "Multiple key strengths"
    assert criteria.overall_score == 8
    assert criteria.recommendation == "Accept"
    assert criteria.detailed_feedback == "Well-written paper with solid contributions"


def test_parse_review_response_with_content_on_next_lines():
    """Test parsing LLM response when content is on the next lines after headers."""
    mock_client = Mock()
    reviewer = ReviewSystem(mock_client)
    
    response = """NOVELTY:
The paper demonstrates high novelty by introducing a new approach.
The methodology is original and well-conceived.

METHODOLOGY:
Strong experimental design with appropriate controls.
The statistical analysis is rigorous.

RESULTS:
Significant findings that advance the field.
Results are reproducible and well-documented.

CLARITY:
Well-written and easy to follow.
Figures and tables are clear.

IMPACT:
High potential impact on the field.
Could influence future research directions.

LIMITATIONS:
Some edge cases not fully addressed.
Sample size could be larger.

STRENGTHS:
Novel approach to the problem.
Rigorous methodology.
Clear presentation.

SCORE:
8

RECOMMENDATION:
Accept

DETAILED FEEDBACK:
This is an excellent paper that makes significant contributions to the field.
The authors should address the minor limitations mentioned above.
Overall, this work deserves publication."""
    
    criteria = reviewer._parse_review_response(response)
    
    # Check that multi-line content was properly accumulated
    assert "high novelty" in criteria.novelty.lower()
    assert "original" in criteria.novelty.lower()
    
    assert "experimental design" in criteria.methodology.lower()
    assert "statistical analysis" in criteria.methodology.lower()
    
    assert "significant findings" in criteria.results.lower()
    assert "reproducible" in criteria.results.lower()
    
    assert "well-written" in criteria.clarity.lower()
    assert "figures" in criteria.clarity.lower()
    
    assert "high potential" in criteria.impact.lower()
    assert "future research" in criteria.impact.lower()
    
    assert "edge cases" in criteria.limitations.lower()
    assert "sample size" in criteria.limitations.lower()
    
    assert "novel approach" in criteria.strengths.lower()
    assert "rigorous" in criteria.strengths.lower()
    
    assert criteria.overall_score == 8
    assert criteria.recommendation == "Accept"
    
    assert "excellent paper" in criteria.detailed_feedback.lower()
    assert "minor limitations" in criteria.detailed_feedback.lower()


def test_parse_review_response_mixed_format():
    """Test parsing LLM response with mixed format (some inline, some multi-line)."""
    mock_client = Mock()
    reviewer = ReviewSystem(mock_client)
    
    response = """NOVELTY: Novel approach with fresh perspective
on classical problems in the domain.

METHODOLOGY:
Rigorous experimental setup.
Appropriate statistical tests applied.

RESULTS: Strong empirical validation
showing significant improvements.

CLARITY:
Well-organized paper.
Clear writing throughout.

IMPACT: High potential impact

LIMITATIONS:
Limited to specific domain.
Could benefit from broader evaluation.

STRENGTHS: Innovative solution, clear presentation

SCORE: 7

RECOMMENDATION: Revise

DETAILED FEEDBACK:
Good paper overall but needs minor revisions.
Address the limitations and expand evaluation."""
    
    criteria = reviewer._parse_review_response(response)
    
    # Check mixed format parsing
    assert "novel approach" in criteria.novelty.lower()
    assert "classical problems" in criteria.novelty.lower()
    
    assert "rigorous" in criteria.methodology.lower()
    assert "statistical tests" in criteria.methodology.lower()
    
    assert "strong empirical" in criteria.results.lower()
    assert "improvements" in criteria.results.lower()
    
    assert "well-organized" in criteria.clarity.lower()
    
    assert "high potential" in criteria.impact.lower()
    
    assert "limited to specific" in criteria.limitations.lower()
    assert "broader evaluation" in criteria.limitations.lower()
    
    assert "innovative" in criteria.strengths.lower()
    
    assert criteria.overall_score == 7
    assert criteria.recommendation == "Revise"
    
    assert "minor revisions" in criteria.detailed_feedback.lower()
