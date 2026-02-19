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


def test_parse_review_response_score_five_on_next_line():
    """Test parsing when score is legitimately 5 and appears on next line."""
    mock_client = Mock()
    reviewer = ReviewSystem(mock_client)
    
    response = """NOVELTY:
Average novelty, builds on existing work.

METHODOLOGY:
Standard methodology used.

RESULTS:
Results are adequate but not exceptional.

CLARITY:
Writing is acceptable.

IMPACT:
Moderate impact expected.

LIMITATIONS:
Several notable limitations.

STRENGTHS:
Some strengths present.

SCORE:
5

RECOMMENDATION:
Revise

DETAILED FEEDBACK:
The paper needs significant revisions before acceptance."""
    
    criteria = reviewer._parse_review_response(response)
    
    # Ensure score of 5 on next line is parsed correctly
    assert criteria.overall_score == 5
    assert criteria.recommendation == "Revise"
    assert "significant revisions" in criteria.detailed_feedback.lower()


def test_parse_review_response_revise_recommendation_on_next_line():
    """Test parsing when recommendation is legitimately 'Revise' and appears on next line."""
    mock_client = Mock()
    reviewer = ReviewSystem(mock_client)
    
    response = """NOVELTY:
Some novelty but limited.

METHODOLOGY:
Methodology is adequate.

RESULTS:
Results need strengthening.

CLARITY:
Clarity could be improved.

IMPACT:
Moderate impact.

LIMITATIONS:
Multiple limitations identified.

STRENGTHS:
Has some merit.

SCORE:
6

RECOMMENDATION:
Revise

DETAILED FEEDBACK:
The paper shows promise but requires substantial revisions to address the identified issues."""
    
    criteria = reviewer._parse_review_response(response)
    
    # Ensure "Revise" recommendation on next line is parsed correctly
    assert criteria.recommendation == "Revise"
    assert criteria.overall_score == 6
    assert "substantial revisions" in criteria.detailed_feedback.lower()


def test_parse_review_response_with_bold_headers():
    """Test parsing LLM response with bold markdown headers like **NOVELTY:**."""
    mock_client = Mock()
    reviewer = ReviewSystem(mock_client)
    
    response = """**NOVELTY:** The paper introduces **HowkGPT**, a novel approach to detecting AI-generated academic assignments using **context-aware perplexity analysis**. While perplexity as a metric for text generation detection is not entirely new, the application of metadata-driven categorization (knowledge and cognitive dimensions) to refine detection thresholds represents a significant contribution. The work bridges the gap between general AI detection tools and domain-specific academic integrity tools. However, the novelty is somewhat limited by the reliance on existing techniques (perplexity) and the use of GPT-2 instead of ChatGPT itself, which may affect direct comparability. The inclusion of a public web application adds practical value, making this a step forward in accessible AI detection tools.

**METHODOLOGY:** The methodology is **well-documented and systematic**, with a clear algorithm for calculating perplexity (Algorithm 1) and a structured experimental design. The use of a pretrained GPT-2 model is justified due to access constraints, though this introduces a limitation in direct comparison with ChatGPT. The dataset construction is robust, leveraging faculty input and metadata annotations. However, the methodology could be strengthened by addressing the use of GPT-2 for ChatGPT detection and clarifying the rationale for choosing specific perplexity calculation parameters. The inclusion of ROC curves and F1 scores for threshold optimization is appropriate, but the reliance on a single model (GPT-2) limits the generalizability of the findings.

**RESULTS:** The results demonstrate that **category-specific thresholds** (based on knowledge and cognitive dimensions) significantly improve detection accuracy compared to a single threshold. The findings are statistically sound, with clear visualizations (Figures 4-8) supporting the conclusions. The paper highlights the unique challenges posed by math and code-related responses, which behave differently from other text types. However, the results are constrained by the dataset size and the use of GPT-2. The identification of procedural and metacognitive categories as high-value detection areas is insightful, but further exploration of these findings would strengthen the discussion.

**CLARITY:** The paper is **well-written and clearly structured**, with a logical flow from introduction to methodology to results. The technical details are adequately explained, though some sections (e.g., the perplexity calculation algorithm) could be simplified for broader accessibility. The figures and tables are informative and well-integrated. The writing is precise, but some jargon-heavy sections may require further refinement for non-expert readers.

**IMPACT:** The paper makes a **meaningful contribution** to the growing field of AI detection tools in education. The development of HowkGPT as an open-source tool is particularly valuable for educators and researchers. The focus on academic integrity aligns with urgent educational needs, and the findings could inform future tools. However, the impact is somewhat limited by the dataset size and the use of GPT-2 instead of ChatGPT, which may restrict immediate applicability in real-world scenarios.

**LIMITATIONS:** 1. **Methodological Limitations:** The use of GPT-2 instead of ChatGPT limits direct comparisons. The reliance on a single perplexity metric may overlook other linguistic cues. 2. **Dataset Constraints:** The dataset, while comprehensive, is limited in size and scope, focusing primarily on NYUAD courses. Generalizability to other domains or institutions may be questionable. 3. **Analysis Depth:** The discussion of F1 vs. AUC trade-offs could be expanded to address the broader implications for detection accuracy. 4. **Future Work:** The paper acknowledges limitations but does not fully explore how combining multiple metrics could enhance detection accuracy.

**STRENGTHS:** 1. **Novel Integration:** The combination of perplexity analysis with metadata-driven categorization is innovative. 2. **Practical Tool:** The development of HowkGPT as a web application provides immediate utility for educators. 3. **Robust Experimentation:** Extensive experiments with multiple dataset flavors and threshold methods demonstrate thorough evaluation. 4. **Ethical Focus:** The study directly addresses a critical issue in education (academic integrity) with AI-generated content.

**SCORE:** **7.5/10**

**RECOMMENDATION:** **Revise**

**DETAILED FEEDBACK:** 1. **Methodology:** Clarify the rationale for using GPT-2 instead of ChatGPT and explore if newer models (e.g., GPT-3.5/4) could yield better results. 2. **Results:** Include a sensitivity analysis to test the robustness of the findings with different models or datasets. 3. **Discussion:** Expand the analysis of procedural and metacognitive categories, particularly their unique detection challenges. 4. **Clarity:** Simplify technical sections (e.g., Algorithm 1) for readability. 5. **Future Work:** Propose concrete steps for combining multiple linguistic metrics to improve detection accuracy. 6. **Ethical Considerations:** Discuss potential biases in the dataset and implications for fairness in academic grading."""
    
    criteria = reviewer._parse_review_response(response)
    
    assert "HowkGPT" in criteria.novelty
    assert "well-documented and systematic" in criteria.methodology
    assert "category-specific thresholds" in criteria.results
    assert "well-written and clearly structured" in criteria.clarity
    assert "meaningful contribution" in criteria.impact
    assert "Methodological Limitations" in criteria.limitations
    assert "Novel Integration" in criteria.strengths
    assert criteria.overall_score == 7  # Should extract 7 from 7.5/10
    assert criteria.recommendation == "Revise"
    assert "Methodology:" in criteria.detailed_feedback
