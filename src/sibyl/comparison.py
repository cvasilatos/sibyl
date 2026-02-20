"""Comparison and evaluation of multiple LLM reviews."""

from typing import Any

from sibyl.config import MAX_SCORE
from sibyl.reviewer import PaperReview


class ReviewComparison:
    """Compare and analyze reviews from multiple LLMs."""

    def __init__(self, reviews: list[PaperReview]) -> None:
        """Initialize the comparison system.

        Args:
            reviews: List of reviews to compare

        """
        self.reviews = reviews

    def get_recommendation_distribution(self) -> dict[str, int]:
        """Get distribution of recommendations.

        Returns:
            Dictionary mapping recommendation to count

        """
        distribution = {}
        for review in self.reviews:
            rec = review.criteria.recommendation
            distribution[rec] = distribution.get(rec, 0) + 1
        return distribution

    def get_consensus_recommendation(self) -> str:
        """Determine consensus recommendation across all reviews.

        Returns:
            Consensus recommendation

        """
        distribution = self.get_recommendation_distribution()
        if not distribution:
            return "No consensus"

        max_count = max(distribution.values())
        consensus = [rec for rec, count in distribution.items() if count == max_count]

        if len(consensus) == 1:
            return consensus[0]
        return "Mixed (" + "/".join(consensus) + ")"

    def generate_summary(self) -> str:
        """Generate a summary comparing all reviews.

        Returns:
            Formatted summary text

        """
        lines = ["=" * 80]
        lines.append("REVIEW COMPARISON SUMMARY")
        lines.append("=" * 80)
        lines.append(f"\nTotal Reviews: {len(self.reviews)}")
        lines.append(f"Reviewers: {', '.join([r.reviewer_model for r in self.reviews])}")

        lines.append("\nRecommendation Distribution:")
        for rec, count in self.get_recommendation_distribution().items():
            lines.append(f"  {rec}: {count}")

        lines.append(f"\nConsensus: {self.get_consensus_recommendation()}")

        lines.append("\n" + "=" * 80)
        lines.append("INDIVIDUAL REVIEWS")
        lines.append("=" * 80)

        for i, review in enumerate(self.reviews, 1):
            lines.append(f"\n--- Review {i}: {review.reviewer_model} ---")
            lines.append(f"Score: {review.criteria.score}/{MAX_SCORE}")
            lines.append(f"Recommendation: {review.criteria.recommendation}")
            lines.append(f"\nNovelty:\n{review.criteria.novelty}")
            lines.append(f"\nMethodology:\n{review.criteria.methodology}")
            lines.append(f"\nResults:\n{review.criteria.results}")
            lines.append(f"\nClarity:\n{review.criteria.clarity}")
            lines.append(f"\nImpact:\n{review.criteria.impact}")
            lines.append(f"\nLimitations:\n{review.criteria.limitations}")
            lines.append(f"\nStrengths:\n{review.criteria.strengths}")
            lines.append(f"\nDetailed Feedback:\n{review.criteria.detailed_feedback}")

        return "\n".join(lines)

    def get_comparative_analysis(self) -> dict[str, Any]:
        """Get a structured comparative analysis.

        Returns:
            Dictionary containing comparative metrics

        """
        return {
            "total_reviews": len(self.reviews),
            "reviewers": [r.reviewer_model for r in self.reviews],
            "recommendation_distribution": self.get_recommendation_distribution(),
            "consensus": self.get_consensus_recommendation(),
            "individual_scores": [r.criteria.score for r in self.reviews],
            "individual_recommendations": [r.criteria.recommendation for r in self.reviews],
        }
