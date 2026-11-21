"""Tests for the comparison module."""

from sibyl.schemas.llm_reply import LLMReply, Recommendation
from sibyl.services.comparison import ReviewComparison
from sibyl.services.reviewer import PaperReview


def create_mock_review(model_name: str, score: int, recommendation: Recommendation) -> PaperReview:
    """Helper function to create mock reviews."""
    criteria = LLMReply(
        novelty="Test novelty",
        methodology="Test methodology",
        results="Test results",
        clarity="Test clarity",
        impact="Test impact",
        limitations="Test limitations",
        strengths="Test strengths",
        score=score,
        recommendation=recommendation,
        detailed_feedback="Test detailed feedback",
    )

    return PaperReview(
        paper_title="Test Paper",
        reviewer_model=model_name,
        criteria=criteria,
        raw_response="Test",
    )


def test_review_comparison_recommendation_distribution():
    """Test getting recommendation distribution."""
    reviews = [
        create_mock_review("Model1", 3, Recommendation.ACCEPT),
        create_mock_review("Model2", 4, Recommendation.MINOR_REVISION),
        create_mock_review("Model3", 5, Recommendation.ACCEPT),
    ]

    comparison = ReviewComparison(reviews)
    distribution = comparison.get_recommendation_distribution()

    assert distribution["Accept"] == 2
    assert distribution["Minor Revision"] == 1


def test_review_comparison_consensus():
    """Test determining consensus recommendation."""
    reviews = [
        create_mock_review("Model1", 3, Recommendation.ACCEPT),
        create_mock_review("Model2", 4, Recommendation.ACCEPT),
        create_mock_review("Model3", 5, Recommendation.ACCEPT),
    ]

    comparison = ReviewComparison(reviews)
    consensus = comparison.get_consensus_recommendation()

    assert consensus == "Accept"


def test_review_comparison_mixed_consensus():
    """Test mixed consensus scenario."""
    reviews = [
        create_mock_review("Model1", 3, Recommendation.ACCEPT),
        create_mock_review("Model2", 4, Recommendation.MINOR_REVISION),
    ]

    comparison = ReviewComparison(reviews)
    consensus = comparison.get_consensus_recommendation()

    assert "Mixed" in consensus or consensus in ["Accept", "Minor Revision"]


def test_comparative_analysis():
    """Test getting comparative analysis."""
    reviews = [
        create_mock_review("Model1", 3, Recommendation.ACCEPT),
        create_mock_review("Model2", 4, Recommendation.MINOR_REVISION),
    ]

    comparison = ReviewComparison(reviews)
    analysis = comparison.get_comparative_analysis()

    assert analysis["total_reviews"] == 2
    assert len(analysis["reviewers"]) == 2
    assert "recommendation_distribution" in analysis


def test_empty_review_comparison():
    """Test comparison with no reviews."""
    comparison = ReviewComparison([])
    assert comparison.get_consensus_recommendation() == "No consensus"
    assert comparison.get_recommendation_distribution() == {}


def test_score_statistics():
    """Test score statistics calculation."""
    reviews = [
        create_mock_review("Model1", 2, Recommendation.REJECT),
        create_mock_review("Model2", 4, Recommendation.ACCEPT),
    ]
    comparison = ReviewComparison(reviews)
    stats = comparison.get_score_statistics()

    assert stats["mean"] == 3.0
    assert stats["min"] == 2.0
    assert stats["max"] == 4.0


def test_generate_summary():
    """Test generating a review summary string."""
    reviews = [
        create_mock_review("ModelA", 4, Recommendation.ACCEPT),
    ]
    comparison = ReviewComparison(reviews)
    summary = comparison.generate_summary()

    assert "ModelA" in summary
    assert "Accept" in summary
