"""Tests for the storage module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sibyl.schemas.llm_reply import LLMReply, Recommendation
from sibyl.schemas.related_work import RelatedPaper
from sibyl.schemas.review_config import ReviewConfig, ReviewDetail, ReviewMode
from sibyl.services.reviewer import PaperReview
from sibyl.storage.engine import Engine
from sibyl.storage.review import Review

MOCK_EMBEDDING = [0.1, 0.2, 0.3]


def _make_llm_reply(score: int = 4, recommendation: Recommendation = Recommendation.ACCEPT, **kwargs) -> LLMReply:
    """Helper to create a valid LLMReply."""
    defaults = {
        "novelty": "High novelty and originality",
        "methodology": "Strong methodology with clear design",
        "results": "Significant and well-presented results",
        "clarity": "Clear and well-written",
        "impact": "High potential impact",
        "limitations": "Minor limitations identified",
        "strengths": "Multiple key strengths",
        "score": score,
        "recommendation": recommendation,
        "detailed_feedback": "Excellent work overall with minor suggestions",
    }
    defaults.update(kwargs)
    return LLMReply(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage(temp_storage):
    """Create an Engine instance with a temporary directory and mocked embeddings."""
    engine = Engine(storage_path=temp_storage)
    with patch.object(engine, "_generate_embedding", return_value=MOCK_EMBEDDING):
        yield engine


@pytest.fixture
def sample_review():
    """Create a sample PaperReview for testing."""
    return PaperReview(
        paper_title="Test Paper on Machine Learning",
        reviewer_model="TestModel v1.0",
        criteria=_make_llm_reply(score=4, recommendation=Recommendation.ACCEPT),
        raw_response="Test raw response",
    )


def test_storage_initialization(temp_storage):
    """Test that storage initializes correctly."""
    engine = Engine(storage_path=temp_storage)
    assert Path(temp_storage).exists()
    assert engine.count_reviews() == 0


def test_save_review(storage, sample_review):
    """Test saving a review to storage."""
    review_id = storage.save_review(
        review=sample_review,
        pdf_filename="test_paper.pdf",
        pdf_path=None,
        paper_text="This is the full text of the paper for searching",
    )

    assert review_id is not None
    assert len(review_id) > 0
    assert storage.count_reviews() == 1


def test_get_review(storage, sample_review):
    """Test retrieving a specific review."""
    review_id = storage.save_review(
        review=sample_review,
        pdf_filename="test_paper.pdf",
    )

    retrieved = storage.get_review(review_id)
    assert retrieved is not None
    assert retrieved["id"] == review_id
    assert retrieved["paper_title"] == "Test Paper on Machine Learning"
    assert retrieved["pdf_filename"] == "test_paper.pdf"
    assert retrieved["reviewer_model"] == "TestModel v1.0"
    assert retrieved["score"] == 4
    assert retrieved["recommendation"] == "Accept"


def test_get_review_keeps_related_work(storage, sample_review):
    """Related papers found for a review are stored with it; reviews without them load with an empty list."""
    paper = RelatedPaper(ref="R1", title="Prior Work", authors=["A. Author"], year=2023, url="https://arxiv.org/abs/2301.00001", abstract="abs", relation="Same task")
    with_related = sample_review.model_copy(update={"related_work": [paper]})

    retrieved = storage.get_review(storage.save_review(review=with_related, pdf_filename="p.pdf"))
    assert retrieved is not None
    assert [RelatedPaper.model_validate(p) for p in retrieved["related_work"]] == [paper]

    plain = storage.get_review(storage.save_review(review=sample_review, pdf_filename="p.pdf"))
    assert plain is not None
    assert plain["related_work"] == []


def test_get_nonexistent_review(storage):
    """Test retrieving a review that doesn't exist."""
    retrieved = storage.get_review("nonexistent_id_12345")
    assert retrieved is None


def test_list_reviews(storage, sample_review):
    """Test listing all reviews."""
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
    assert all(isinstance(r, Review) for r in reviews)


def test_list_reviews_with_pagination(storage, sample_review):
    """Test listing reviews with pagination."""
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

    page1 = storage.list_reviews(limit=2, offset=0)
    assert len(page1) == 2

    page2 = storage.list_reviews(limit=2, offset=2)
    assert len(page2) == 2

    assert page1[0].id != page2[0].id


def test_search_reviews_semantic(storage, sample_review):
    """Test semantic search of reviews."""
    storage.save_review(
        review=sample_review,
        pdf_filename="ml_paper.pdf",
        paper_text="Machine learning algorithms and neural networks for image classification",
    )

    other_review = PaperReview(
        paper_title="Paper on Quantum Computing",
        reviewer_model="TestModel v1.0",
        criteria=_make_llm_reply(score=3, recommendation=Recommendation.MINOR_REVISION, detailed_feedback="Good work on quantum computing research"),
        raw_response="Test",
    )
    storage.save_review(
        review=other_review,
        pdf_filename="quantum_paper.pdf",
        paper_text="Quantum computing and quantum algorithms for cryptography",
    )

    results = storage.search_reviews("machine learning")
    assert len(results) >= 1

    for result in results:
        assert result.similarity_score is not None
        assert isinstance(result.similarity_score, float)


def test_delete_review(storage, sample_review):
    """Test deleting a review."""
    review_id = storage.save_review(
        review=sample_review,
        pdf_filename="test.pdf",
    )

    assert storage.count_reviews() == 1

    assert storage.delete_review(review_id) is True
    assert storage.count_reviews() == 0

    assert storage.delete_review(review_id) is False


def test_delete_all_reviews(storage, sample_review):
    """Test deleting all reviews."""
    for i in range(3):
        modified_review = PaperReview(
            paper_title=f"Paper {i}",
            reviewer_model=sample_review.reviewer_model,
            criteria=sample_review.criteria,
            raw_response=sample_review.raw_response,
        )
        storage.save_review(review=modified_review, pdf_filename=f"paper_{i}.pdf")

    assert storage.count_reviews() == 3

    count = storage.delete_all_reviews()
    assert count == 3
    assert storage.count_reviews() == 0


def test_delete_all_reviews_empty(storage):
    """Test deleting all reviews when none exist."""
    count = storage.delete_all_reviews()
    assert count == 0
    assert storage.count_reviews() == 0


def test_count_reviews(storage, sample_review):
    """Test counting reviews."""
    assert storage.count_reviews() == 0

    storage.save_review(review=sample_review, pdf_filename="test1.pdf")
    assert storage.count_reviews() == 1

    storage.save_review(review=sample_review, pdf_filename="test2.pdf")
    assert storage.count_reviews() == 2


def test_get_statistics(storage, sample_review):
    """Test getting statistics about stored reviews."""
    stats = storage.get_statistics()
    assert stats["total_reviews"] == 0

    storage.save_review(review=sample_review, pdf_filename="test1.pdf")

    review2 = PaperReview(
        paper_title="Another Paper",
        reviewer_model="TestModel v2.0",
        criteria=_make_llm_reply(score=3, recommendation=Recommendation.MINOR_REVISION),
        raw_response="Test",
    )
    storage.save_review(review=review2, pdf_filename="test2.pdf")

    stats = storage.get_statistics()
    assert stats["total_reviews"] == 2
    assert stats["unique_papers"] == 2
    assert stats["unique_models"] == 2
    assert "Accept" in stats["recommendations"]
    assert "Minor Revision" in stats["recommendations"]


def test_list_reviews_with_text_search(storage, sample_review):
    """Test listing reviews with text-based search filtering."""
    storage.save_review(
        review=sample_review,
        pdf_filename="ml_paper.pdf",
    )

    quantum_review = PaperReview(
        paper_title="Paper on Quantum Computing",
        reviewer_model="QuantumModel v1.0",
        criteria=_make_llm_reply(score=3, recommendation=Recommendation.MINOR_REVISION, detailed_feedback="Good quantum work"),
        raw_response="Test",
    )
    storage.save_review(review=quantum_review, pdf_filename="quantum_paper.pdf")

    # Search by title keyword (case-insensitive)
    results = storage.list_reviews(search="machine learning")
    assert len(results) == 1
    assert results[0].paper_title == "Test Paper on Machine Learning"

    # Search by model name
    results = storage.list_reviews(search="QuantumModel")
    assert len(results) == 1
    assert results[0].reviewer_model == "QuantumModel v1.0"

    # Search by recommendation
    results = storage.list_reviews(search="Minor Revision")
    assert len(results) == 1
    assert results[0].recommendation == "Minor Revision"

    # Empty search returns all
    results = storage.list_reviews(search="")
    assert len(results) == 2

    # No-match search returns empty list
    results = storage.list_reviews(search="zzz_no_match_zzz")
    assert len(results) == 0


def test_save_review_recreates_empty_collection_sized_for_another_model(storage, sample_review):
    """An emptied library made with another embedding model (e.g. 384-dim MiniLM) accepts new 768-dim reviews."""
    with patch.object(storage, "_generate_embedding", return_value=[0.1] * 384):
        old_id = storage.save_review(review=sample_review, pdf_filename="old.pdf")
    storage.delete_review(old_id)

    with patch.object(storage, "_generate_embedding", return_value=[0.1] * 768):
        review_id = storage.save_review(review=sample_review, pdf_filename="new.pdf")

    assert storage.count_reviews() == 1
    assert storage.get_review(review_id) is not None


def test_save_review_explains_mismatch_and_keeps_no_pdf(storage, sample_review, tmp_path):
    """A library that still holds reviews from another embedding model is not wiped; the error says what to do."""
    with patch.object(storage, "_generate_embedding", return_value=[0.1] * 384):
        storage.save_review(review=sample_review, pdf_filename="old.pdf")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF")

    with patch.object(storage, "_generate_embedding", return_value=[0.1] * 768), pytest.raises(RuntimeError, match="SIBYL_EMBEDDINGS"):
        storage.save_review(review=sample_review, pdf_filename="paper.pdf", pdf_path=pdf)

    assert storage.count_reviews() == 1
    assert list(storage.pdf_storage.iterdir()) == []


def test_get_review_keeps_its_configuration(storage, sample_review):
    """The settings that produced a review are stored with it; older reviews load without them."""
    config = ReviewConfig(engine="ollama", model="qwen3:8b", detail=ReviewDetail.DETAILED, mode=ReviewMode.SECTIONS, temperature=0.7, context_length=32768, generation_calls=9)
    retrieved = storage.get_review(storage.save_review(review=sample_review.model_copy(update={"config": config}), pdf_filename="p.pdf"))
    assert retrieved is not None
    assert ReviewConfig.model_validate(retrieved["config"]) == config

    plain = storage.get_review(storage.save_review(review=sample_review, pdf_filename="p.pdf"))
    assert plain is not None
    assert plain["config"] is None


def test_reviews_record_their_owner(storage, sample_review):
    """Every view of a review names who ran it; "delete all" can be limited to one owner."""
    alices = storage.save_review(sample_review, "a.pdf", owner="alice")
    bobs = storage.save_review(sample_review, "b.pdf", owner="bob")
    legacy = storage.save_review(sample_review, "c.pdf")

    assert storage.get_review(alices)["owner"] == "alice"
    assert storage.get_review(legacy)["owner"] is None
    assert {r.id: r.owner for r in storage.list_reviews()} == {alices: "alice", bobs: "bob", legacy: None}
    assert [r.id for r in storage.list_reviews(search="bob")] == [bobs]
    assert {r.owner for r in storage.search_reviews("machine learning")} == {"alice", "bob", None}

    assert storage.delete_all_reviews(owner="alice") == 1
    assert {r.id for r in storage.list_reviews()} == {bobs, legacy}
