"""
Example script demonstrating how to use Sibyl programmatically with local LLMs.
"""

from sibyl.config import SibylConfig, LLMConfig
from sibyl.pdf_parser import PDFParser
from sibyl.llm_client import create_client
from sibyl.reviewer import ReviewSystem
from sibyl.comparison import ReviewComparison


def main():
    """Example of using Sibyl programmatically."""

    # 1. Load configuration
    print("Loading configuration...")
    config = SibylConfig.from_env()
    active_providers = config.get_active_providers()
    print(f"Active providers: {active_providers}\n")

    # 2. Parse PDF
    print("Parsing PDF...")
    pdf_path = "path/to/your/paper.pdf"  # Replace with actual path
    parser = PDFParser(pdf_path)

    # Get metadata
    metadata = parser.get_metadata()
    print(f"Title: {metadata['title']}")
    print(f"Author: {metadata['author']}")
    print(f"Pages: {metadata['num_pages']}\n")

    # Extract text
    paper_text = parser.extract_text(max_pages=10)  # Limit to first 10 pages
    print(f"Extracted {len(paper_text)} characters\n")

    # 3. Generate reviews
    print("Generating reviews...")
    reviews = []

    for provider in active_providers:
        print(f"  Reviewing with {provider}...")
        provider_config = getattr(config, provider)

        # Create client and reviewer
        client = create_client(provider, provider_config)
        reviewer = ReviewSystem(client)

        # Generate review
        review = reviewer.review_paper(paper_text, metadata['title'])
        reviews.append(review)

        print(
            f"    Score: {review.criteria.overall_score}/10, "
            f"Recommendation: {review.criteria.recommendation}"
        )

    print()

    # 4. Compare reviews (if you have any)
    if reviews:
        print("Comparing reviews...")
        comparison = ReviewComparison(reviews)

        # Get statistics
        stats = comparison.get_score_statistics()
        print(f"  Mean score: {stats['mean']:.2f}")
        print(f"  Score range: {stats['min']} - {stats['max']}")
        print(f"  Standard deviation: {stats['std']:.2f}")

        # Get consensus
        consensus = comparison.get_consensus_recommendation()
        print(f"  Consensus: {consensus}\n")

        # 5. Get detailed comparison
        print("Generating detailed comparison...")
        summary = comparison.generate_summary()

        # Save to file
        with open("review_comparison.txt", "w") as f:
            f.write(summary)

        print("✓ Comparison saved to review_comparison.txt")

        # 6. Get structured analysis for further processing
        analysis = comparison.get_comparative_analysis()
        print(f"\nTotal reviews: {analysis['total_reviews']}")
        print(f"Individual scores: {analysis['individual_scores']}")
        print(f"Recommendation distribution: {analysis['recommendation_distribution']}")


def compare_multiple_models():
    """Example: Compare multiple local models by running them sequentially."""
    import os
    
    models_to_test = ["llama3.2", "mistral", "phi3"]
    pdf_path = "path/to/your/paper.pdf"
    
    # Parse PDF once before the loop
    parser = PDFParser(pdf_path)
    paper_text = parser.extract_text(max_pages=10)
    metadata = parser.get_metadata()
    
    all_reviews = []
    
    for model_name in models_to_test:
        print(f"\n{'='*60}")
        print(f"Testing model: {model_name}")
        print('='*60)
        
        # Set environment variable for this model
        os.environ['OLLAMA_MODEL'] = model_name
        
        # Reload config with new model
        config = SibylConfig.from_env()
        
        if not config.ollama:
            print(f"Skipping {model_name} - not configured")
            continue
        
        # Create client and review
        client = create_client("ollama", config.ollama)
        reviewer = ReviewSystem(client)
        review = reviewer.review_paper(paper_text, metadata['title'])
        all_reviews.append(review)
        
        print(f"  Score: {review.criteria.overall_score}/10")
        print(f"  Recommendation: {review.criteria.recommendation}")
    
    # Compare all reviews
    if len(all_reviews) > 1:
        print(f"\n{'='*60}")
        print("Comparison Across Models")
        print('='*60)
        
        comparison = ReviewComparison(all_reviews)
        summary = comparison.generate_summary()
        print(summary)


if __name__ == "__main__":
    main()
    
    # Uncomment to test multiple models
    # compare_multiple_models()
