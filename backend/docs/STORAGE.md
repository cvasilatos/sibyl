# Sibyl Storage and Search

Sibyl now includes a powerful vector database storage system that allows you to save, organize, and semantically search through your research paper reviews.

## Overview

The storage system uses **ChromaDB**, a vector database optimized for semantic search. Unlike traditional keyword search, vector search understands the *meaning* of your queries, enabling you to find papers based on concepts rather than exact word matches.

## Features

### 🔍 Semantic Search
Search for papers by meaning, not just keywords:
- **Query**: "papers about machine learning"
- **Finds**: Papers about "neural networks", "deep learning", "ML algorithms", etc.

### 📊 Statistics Dashboard
Track your review library with:
- Total number of reviews
- Average review scores
- Number of unique papers reviewed
- Recommendation distribution (Accept/Revise/Reject)

### 💾 Persistent Storage
- Reviews automatically saved after completion
- PDFs stored alongside review metadata
- Full review criteria and feedback preserved
- Searchable by paper content and review details

### 🎯 Similarity Scoring
Search results include similarity scores showing how closely each result matches your query.

## Quick Start

### 1. Install Dependencies

```bash
# Install uv if not already installed
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install Sibyl with web dependencies
uv pip install -e ".[web]"
```

### 2. (Optional) Install Ollama Embedding Model

For production-quality semantic search, install the embedding model:

```bash
ollama pull nomic-embed-text
```

> **Note**: Sibyl will work without this, using a fallback embedding method for testing.

### 3. Start the Backend and Frontend

**Terminal 1 - Backend**:
```bash
sibyl web
```

**Terminal 2 - Frontend**:
```bash
cd web
npm install  # First time only
npm run dev
```

### 4. Access the Interface

Open http://localhost:3000 in your browser.

## Using the Web Interface

### Review Paper Tab

1. Upload a PDF research paper
2. Click "Start Review" to analyze the paper
3. View the generated review
4. **Review is automatically saved to your library**

### Search Library Tab

1. View statistics about your review collection
2. Enter a search query (e.g., "quantum computing", "neural networks")
3. Click "Search Reviews" to find relevant papers
4. Click on any result to view the full review

## API Usage

You can also use the storage system programmatically:

```python
from sibyl.storage import ReviewStorage
from sibyl.reviewer import ReviewSystem, PaperReview
from sibyl.llm_client import create_client
from sibyl.config import SibylConfig

# Initialize storage
storage = ReviewStorage(storage_path="./sibyl_storage")

# After generating a review...
review_id = storage.save_review(
    review=paper_review,
    pdf_filename="my_paper.pdf",
    pdf_path="/path/to/my_paper.pdf",
    paper_text=extracted_paper_text
)

# Search for papers
results = storage.search_reviews("neural networks", limit=10)
for review in results:
    print(f"{review.paper_title}: {review.similarity_score:.2%} match")
    print(f"Score: {review.overall_score}/10")
    print(f"Recommendation: {review.recommendation}")
    print()

# Get a specific review
review_details = storage.get_review(review_id)
print(review_details["criteria"]["detailed_feedback"])

# List all reviews
all_reviews = storage.list_reviews(limit=50, offset=0)

# Get statistics
stats = storage.get_statistics()
print(f"Total reviews: {stats['total_reviews']}")
print(f"Average score: {stats['avg_score']:.1f}")
print(f"Unique papers: {stats['unique_papers']}")

# Delete a review
storage.delete_review(review_id)
```

## REST API Endpoints

The web server provides these endpoints:

### Search Reviews
```http
POST /api/search
Content-Type: application/json

{
  "query": "machine learning in healthcare",
  "limit": 10
}
```

Returns reviews ranked by semantic similarity.

### List All Reviews
```http
GET /api/reviews?limit=50&offset=0
```

Returns paginated list of all reviews.

### Get Review Details
```http
GET /api/reviews/{review_id}
```

Returns complete review with all criteria.

### Delete Review
```http
DELETE /api/reviews/{review_id}
```

Deletes a review and its associated PDF.

### Get Statistics
```http
GET /api/statistics
```

Returns statistics about the review library.

## How Semantic Search Works

### 1. Embedding Generation

When you save a review, Sibyl creates a **vector embedding** - a numerical representation that captures the semantic meaning of:
- Paper title
- Review criteria (novelty, methodology, results, etc.)
- Paper content (if provided)

### 2. Similarity Matching

When you search, Sibyl:
1. Generates an embedding for your query
2. Compares it to all stored review embeddings
3. Ranks results by similarity (cosine distance)
4. Returns the most relevant matches

### 3. Example

**Query**: "papers about transformers"

**Matches**:
- Papers explicitly about "transformers" ✓
- Papers about "attention mechanisms" ✓ (related concept)
- Papers about "BERT" or "GPT" ✓ (transformer-based models)
- Papers about "sequence-to-sequence models" ✓ (related architecture)

Traditional keyword search would miss most of these!

## Storage Location

All data is stored in the `sibyl_storage/` directory:

```
sibyl_storage/
├── chromadb/          # Vector database files
└── pdfs/              # Stored PDF files
```

This directory is excluded from git by default.

## Configuration

### Custom Storage Path

```python
storage = ReviewStorage(storage_path="/path/to/my/storage")
```

### Custom Ollama URL

```python
storage = ReviewStorage(
    storage_path="./sibyl_storage",
    ollama_url="http://192.168.1.100:11434"
)
```

## Best Practices

### 1. Include Paper Text for Better Search

When saving reviews, include the full paper text:

```python
storage.save_review(
    review=review,
    pdf_filename="paper.pdf",
    pdf_path="/path/to/paper.pdf",
    paper_text=full_extracted_text  # Important!
)
```

This significantly improves search quality by including paper content in embeddings.

### 2. Use Descriptive Search Queries

Better queries lead to better results:
- ❌ "ML" → ✓ "machine learning algorithms"
- ❌ "NLP" → ✓ "natural language processing"
- ❌ "papers" → ✓ "papers about sentiment analysis"

### 3. Check Similarity Scores

Results with similarity > 0.7 are usually highly relevant.
Results with similarity < 0.5 may be false positives.

### 4. Regular Cleanup

As your library grows, periodically:
- Delete outdated or superseded reviews
- Merge duplicate reviews of the same paper
- Archive old reviews to a backup location

## Troubleshooting

### "No reviews found" when reviews exist

**Cause**: Embeddings may not have been generated properly.

**Solution**: 
1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
2. Install embedding model: `ollama pull nomic-embed-text`
3. Restart the Sibyl web server

### Slow search performance

**Cause**: Large number of reviews or slow embedding generation.

**Solutions**:
- Limit search results with the `limit` parameter
- Use more specific queries
- Consider running Ollama on GPU for faster embeddings

### Storage directory growing too large

**Cause**: Many PDFs and reviews stored.

**Solutions**:
- Delete old or unnecessary reviews via API
- Use `storage.delete_review(review_id)` to remove specific reviews
- Manually clean up the `sibyl_storage/pdfs/` directory

## Advanced Features

### Pagination

For large libraries, use pagination:

```python
# Get first page (reviews 0-49)
page1 = storage.list_reviews(limit=50, offset=0)

# Get second page (reviews 50-99)
page2 = storage.list_reviews(limit=50, offset=50)
```

### Filtering by Score

```python
# Get all reviews
reviews = storage.list_reviews(limit=1000)

# Filter high-scoring papers
high_quality = [r for r in reviews if r.overall_score >= 8]

# Filter by recommendation
accepted = [r for r in reviews if r.recommendation == "Accept"]
```

### Export Reviews

```python
import json

# Get all reviews
reviews = storage.list_reviews(limit=1000)

# Export to JSON
export_data = [
    {
        "id": r.id,
        "title": r.paper_title,
        "score": r.overall_score,
        "recommendation": r.recommendation,
        "filename": r.pdf_filename,
        "created_at": r.created_at,
    }
    for r in reviews
]

with open("reviews_export.json", "w") as f:
    json.dump(export_data, f, indent=2)
```

## Comparison: Vector vs. Keyword Search

| Feature | Keyword Search (SQLite FTS) | Vector Search (ChromaDB) |
|---------|----------------------------|-------------------------|
| **Matches exact words** | ✓ | ✓ |
| **Understands synonyms** | ✗ | ✓ |
| **Finds related concepts** | ✗ | ✓ |
| **Handles typos** | Limited | ✓ |
| **Multilingual** | Limited | ✓ |
| **Ranks by relevance** | Basic | Advanced |
| **Similarity scores** | ✗ | ✓ |
| **Setup complexity** | Low | Medium |

## Future Enhancements

Planned features for future versions:
- Advanced filters (date range, score range, reviewer model)
- Tags and categories for organization
- Bulk operations (delete multiple, export selection)
- Full-text PDF search within stored documents
- Comparison view (side-by-side review comparison)
- Export to various formats (CSV, Excel, Markdown)

## Support

For issues or questions about the storage system:
1. Check this documentation
2. Review the API examples above
3. Open an issue on GitHub with the "storage" label
