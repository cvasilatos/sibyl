"""Tests for the storage module."""

import json
import tempfile
from pathlib import Path

import pytest

from sibyl.reviewer import PaperReview, ReviewCriteria
from sibyl.storage import ReviewStorage, StoredReview


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def storage(temp_db):
    """Create a ReviewStorage instance with a temporary database."""
    return ReviewStorage(db_path=temp_db)


@pytest.fixture
def sample_review():
    """Create a sample PaperReview for testing."""
    criteria = ReviewCriteria(
        novelty="High novelty and originality",
        methodology="Strong methodology with clear design",
        results="Significant and well-presented results",
        clarity="Clear and well-written",
        impact="High potential impact",
        limitations="Minor limitations identified",
        strengths="Multiple key strengths",
        overall_score=8,
        recommendation="Accept",
        detailed_feedback="Excellent work overall with minor suggestions",
    )
    return PaperReview(
        paper_title="Test Paper on Machine Learning",
        reviewer_model="TestModel v1.0",
        criteria=criteria,
        raw_response="Test raw response",
    )


def test_storage_initialization(temp_db):
    """Test that storage initializes correctly."""
    storage = ReviewStorage(db_path=temp_db)
    assert Path(temp_db).exists()
    assert storage.count_reviews() == 0


def test_save_review(storage, sample_review):
    """Test saving a review to storage."""
    review_id = storage.save_review(
        review=sample_review,
        pdf_filename="test_paper.pdf",
        pdf_path="/path/to/test_paper.pdf",
        paper_text="This is the full text of the paper for searching",
    )

    assert review_id > 0
    assert storage.count_reviews() == 1


def test_get_review(storage, sample_review):
    """Test retrieving a specific review."""
    review_id = storage.save_review(
        review=sample_review,
        pdf_filename="test_paper.pdf",
    )

    retrieved = storage.get_review(review_id)
    assert retrieved is not None
    assert retrieved.id == review_id
    assert retrieved.paper_title == "Test Paper on Machine Learning"
    assert retrieved.pdf_filename == "test_paper.pdf"
    assert retrieved.reviewer_model == "TestModel v1.0"
    assert retrieved.overall_score == 8
    assert retrieved.recommendation == "Accept"


def test_get_nonexistent_review(storage):
    """Test retrieving a review that doesn't exist."""
    retrieved = storage.get_review(99999)
    assert retrieved is None


def test_list_reviews(storage, sample_review):
    """Test listing all reviews."""
    # Save multiple reviews
    for i in range(3):
        modified_review = PaperReview(
            paper_title=f"Paper {i}",
            reviewer_model=sample_review.reviewer_model,
            criteria=sample_review.criteria,
            raw_response=sample_review.raw_response,
        )
        storage.save_review(
            review=modified_review,
            pdf_filename=f"paper_{i}.pdf",
        )

    reviews = storage.list_reviews()
    assert len(reviews) == 3
    assert all(isinstance(r, StoredReview) for r in reviews)


def test_list_reviews_with_pagination(storage, sample_review):
    """Test listing reviews with pagination."""
    # Save 5 reviews
    for i in range(5):
        modified_review = PaperReview(
            paper_title=f"Paper {i}",
            reviewer_model=sample_review.reviewer_model,
            criteria=sample_review.criteria,
            raw_response=sample_review.raw_response,
        )
        storage.save_review(
            review=modified_review,
            pdf_filename=f"paper_{i}.pdf",
        )

    # Get first 2
    page1 = storage.list_reviews(limit=2, offset=0)
    assert len(page1) == 2

    # Get next 2
    page2 = storage.list_reviews(limit=2, offset=2)
    assert len(page2) == 2

    # Ensure no overlap
    assert page1[0].id != page2[0].id


def test_search_reviews_by_title(storage, sample_review):
    """Test searching reviews by paper title."""
    storage.save_review(
        review=sample_review,
        pdf_filename="ml_paper.pdf",
        paper_text="Machine learning algorithms and neural networks",
    )

    # Create another review with different title
    other_criteria = ReviewCriteria(
        novelty="Good",
        methodology="Good",
        results="Good",
        clarity="Good",
        impact="Good",
        limitations="Some",
        strengths="Several",
        overall_score=7,
        recommendation="Revise",
        detailed_feedback="Good work",
    )
    other_review = PaperReview(
        paper_title="Paper on Quantum Computing",
        reviewer_model="TestModel v1.0",
        criteria=other_criteria,
        raw_response="Test",
    )
    storage.save_review(
        review=other_review,
        pdf_filename="quantum_paper.pdf",
        paper_text="Quantum computing and quantum algorithms",
    )

    # Search for machine learning
    results = storage.search_reviews("machine learning")
    assert len(results) >= 1
    assert any("Machine Learning" in r.paper_title for r in results)


def test_search_reviews_by_content(storage, sample_review):
    """Test searching reviews by paper content."""
    storage.save_review(
        review=sample_review,
        pdf_filename="test.pdf",
        paper_text="This paper discusses neural networks and deep learning architectures",
    )

    results = storage.search_reviews("neural networks")
    assert len(results) >= 1


def test_delete_review(storage, sample_review):
    """Test deleting a review."""
    review_id = storage.save_review(
        review=sample_review,
        pdf_filename="test.pdf",
    )

    assert storage.count_reviews() == 1

    deleted = storage.delete_review(review_id)
    assert deleted is True
    assert storage.count_reviews() == 0

    # Try to delete again
    deleted_again = storage.delete_review(review_id)
    assert deleted_again is False


def test_count_reviews(storage, sample_review):
    """Test counting reviews."""
    assert storage.count_reviews() == 0

    storage.save_review(review=sample_review, pdf_filename="test1.pdf")
    assert storage.count_reviews() == 1

    storage.save_review(review=sample_review, pdf_filename="test2.pdf")
    assert storage.count_reviews() == 2


def test_get_statistics(storage, sample_review):
    """Test getting statistics about stored reviews."""
    # Initially empty
    stats = storage.get_statistics()
    assert stats["total_reviews"] == 0

    # Add some reviews
    storage.save_review(review=sample_review, pdf_filename="test1.pdf")

    # Create review with different score
    criteria2 = ReviewCriteria(
        novelty="Good",
        methodology="Good",
        results="Good",
        clarity="Good",
        impact="Good",
        limitations="Some",
        strengths="Several",
        overall_score=6,
        recommendation="Revise",
        detailed_feedback="Good",
    )
    review2 = PaperReview(
        paper_title="Another Paper",
        reviewer_model="TestModel v2.0",
        criteria=criteria2,
        raw_response="Test",
    )
    storage.save_review(review=review2, pdf_filename="test2.pdf")

    stats = storage.get_statistics()
    assert stats["total_reviews"] == 2
    assert stats["avg_score"] == 7.0
    assert stats["min_score"] == 6
    assert stats["max_score"] == 8
    assert stats["unique_papers"] == 2
    assert stats["unique_models"] == 2
    assert "Accept" in stats["recommendations"]
    assert "Revise" in stats["recommendations"]


def test_review_data_json_structure(storage, sample_review):
    """Test that review data is properly stored as JSON."""
    review_id = storage.save_review(
        review=sample_review,
        pdf_filename="test.pdf",
    )

    retrieved = storage.get_review(review_id)
    review_data = json.loads(retrieved.review_data)

    assert "paper_title" in review_data
    assert "reviewer_model" in review_data
    assert "criteria" in review_data
    assert "raw_response" in review_data
    assert review_data["criteria"]["overall_score"] == 8
    assert review_data["criteria"]["recommendation"] == "Accept"
