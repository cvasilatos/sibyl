"""Tests for the comparison module."""

from sibyl.comparison import ReviewComparison
from sibyl.reviewer import PaperReview, ReviewCriteria


def create_mock_review(model_name: str, score: int, recommendation: str) -> PaperReview:
    """Helper function to create mock reviews."""
    criteria = ReviewCriteria(
        novelty="Test",
        methodology="Test",
        results="Test",
        clarity="Test",
        impact="Test",
        limitations="Test",
        strengths="Test",
        overall_score=score,
        recommendation=recommendation,
        detailed_feedback="Test",
    )

    return PaperReview(
        paper_title="Test Paper",
        reviewer_model=model_name,
        criteria=criteria,
        raw_response="Test",
    )


def test_review_comparison_score_statistics():
    """Test calculating score statistics."""
    reviews = [
        create_mock_review("Model1", 8, "Accept"),
        create_mock_review("Model2", 7, "Revise"),
        create_mock_review("Model3", 9, "Accept"),
    ]

    comparison = ReviewComparison(reviews)
    stats = comparison.get_score_statistics()

    assert stats["mean"] == 8.0
    assert stats["min"] == 7
    assert stats["max"] == 9
    assert "std" in stats


def test_review_comparison_recommendation_distribution():
    """Test getting recommendation distribution."""
    reviews = [
        create_mock_review("Model1", 8, "Accept"),
        create_mock_review("Model2", 7, "Revise"),
        create_mock_review("Model3", 9, "Accept"),
    ]

    comparison = ReviewComparison(reviews)
    distribution = comparison.get_recommendation_distribution()

    assert distribution["Accept"] == 2
    assert distribution["Revise"] == 1


def test_review_comparison_consensus():
    """Test determining consensus recommendation."""
    reviews = [
        create_mock_review("Model1", 8, "Accept"),
        create_mock_review("Model2", 8, "Accept"),
        create_mock_review("Model3", 9, "Accept"),
    ]

    comparison = ReviewComparison(reviews)
    consensus = comparison.get_consensus_recommendation()

    assert consensus == "Accept"


def test_review_comparison_mixed_consensus():
    """Test mixed consensus scenario."""
    reviews = [
        create_mock_review("Model1", 8, "Accept"),
        create_mock_review("Model2", 7, "Revise"),
    ]

    comparison = ReviewComparison(reviews)
    consensus = comparison.get_consensus_recommendation()

    assert "Mixed" in consensus or consensus in ["Accept", "Revise"]


def test_comparative_analysis():
    """Test getting comparative analysis."""
    reviews = [
        create_mock_review("Model1", 8, "Accept"),
        create_mock_review("Model2", 7, "Revise"),
    ]

    comparison = ReviewComparison(reviews)
    analysis = comparison.get_comparative_analysis()

    assert analysis["total_reviews"] == 2
    assert len(analysis["reviewers"]) == 2
    assert "score_statistics" in analysis
    assert "recommendation_distribution" in analysis
