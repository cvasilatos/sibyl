"""Command-line interface for Sibyl."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime
import json

from .config import SibylConfig
from .pdf_parser import PDFParser
from .llm_client import create_client
from .reviewer import ReviewSystem
from .comparison import ReviewComparison

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Sibyl - An LLM-powered research paper review system."""
    pass


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "--providers",
    "-p",
    multiple=True,
    type=click.Choice(["openai", "anthropic", "google"], case_sensitive=False),
    help="LLM providers to use (can specify multiple)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path for the review results",
)
@click.option(
    "--max-pages",
    type=int,
    default=None,
    help="Maximum number of pages to extract from PDF",
)
def review(pdf_path: str, providers: tuple, output: str, max_pages: int):
    """Review a research paper PDF using LLMs.

    PDF_PATH: Path to the research paper PDF file
    """
    console.print("\n[bold blue]Sibyl Research Paper Review System[/bold blue]\n")

    # Load configuration
    config = SibylConfig.from_env()
    active_providers = config.get_active_providers()

    if not active_providers:
        console.print(
            "[bold red]Error:[/bold red] No API keys configured. "
            "Please set up your API keys in .env file."
        )
        return

    # Determine which providers to use
    if providers:
        providers_to_use = [p.lower() for p in providers]
        # Validate that requested providers are configured
        for provider in providers_to_use:
            if provider not in active_providers:
                console.print(
                    f"[bold yellow]Warning:[/bold yellow] {provider} requested but not configured. Skipping."
                )
        providers_to_use = [p for p in providers_to_use if p in active_providers]
    else:
        providers_to_use = active_providers

    if not providers_to_use:
        console.print(
            "[bold red]Error:[/bold red] No valid providers available for review."
        )
        return

    console.print(f"[bold]Paper:[/bold] {pdf_path}")
    console.print(f"[bold]Providers:[/bold] {', '.join(providers_to_use)}\n")

    # Extract text from PDF
    console.print("[bold]Step 1:[/bold] Extracting text from PDF...")
    try:
        parser = PDFParser(pdf_path)
        metadata = parser.get_metadata()
        paper_text = parser.extract_text(max_pages=max_pages)

        console.print(f"  Title: {metadata.get('title', 'Unknown')}")
        console.print(f"  Author: {metadata.get('author', 'Unknown')}")
        console.print(f"  Pages: {metadata['num_pages']}")
        console.print(f"  Extracted: {len(paper_text)} characters\n")
    except Exception as e:
        console.print(f"[bold red]Error extracting PDF:[/bold red] {e}")
        return

    # Generate reviews
    console.print("[bold]Step 2:[/bold] Generating reviews...\n")
    reviews = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for provider in providers_to_use:
            task = progress.add_task(f"Reviewing with {provider}...", total=None)

            try:
                # Get provider config
                provider_config = getattr(config, provider)
                if not provider_config:
                    continue

                # Create client and review
                client = create_client(provider, provider_config)
                reviewer = ReviewSystem(client)
                review = reviewer.review_paper(
                    paper_text, paper_title=metadata.get("title", "Unknown")
                )
                reviews.append(review)

                progress.update(task, completed=True)
                console.print(
                    f"  ✓ {provider}: Score {review.criteria.overall_score}/10, "
                    f"Recommendation: {review.criteria.recommendation}"
                )
            except Exception as e:
                console.print(f"  ✗ {provider}: [red]Error - {str(e)}[/red]")

    if not reviews:
        console.print("\n[bold red]Error:[/bold red] No reviews were generated.")
        return

    # Generate comparison
    console.print("\n[bold]Step 3:[/bold] Comparing reviews...\n")
    comparison = ReviewComparison(reviews)

    # Display results
    _display_results(reviews, comparison)

    # Save to file if requested
    if output:
        _save_results(output, reviews, comparison, metadata)
        console.print(f"\n[bold green]Results saved to:[/bold green] {output}")


def _display_results(reviews, comparison):
    """Display review results in a formatted table."""
    # Summary table
    table = Table(title="Review Summary", show_header=True, header_style="bold magenta")
    table.add_column("Reviewer", style="cyan")
    table.add_column("Score", justify="center")
    table.add_column("Recommendation", justify="center")

    for review in reviews:
        table.add_row(
            review.reviewer_model,
            f"{review.criteria.overall_score}/10",
            review.criteria.recommendation,
        )

    console.print(table)

    # Statistics
    stats = comparison.get_score_statistics()
    console.print(f"\n[bold]Score Statistics:[/bold]")
    console.print(f"  Mean: {stats['mean']:.2f}")
    console.print(f"  Std Dev: {stats['std']:.2f}")
    console.print(f"  Range: {stats['min']} - {stats['max']}")

    console.print(f"\n[bold]Consensus:[/bold] {comparison.get_consensus_recommendation()}")


def _save_results(output_path: str, reviews, comparison, metadata):
    """Save review results to a file."""
    output_path = Path(output_path)

    if output_path.suffix == ".json":
        # Save as JSON
        data = {
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
            "comparison": comparison.get_comparative_analysis(),
            "reviews": [
                {
                    "reviewer": r.reviewer_model,
                    "score": r.criteria.overall_score,
                    "recommendation": r.criteria.recommendation,
                    "criteria": r.criteria.model_dump(),
                }
                for r in reviews
            ],
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
    else:
        # Save as text
        summary = comparison.generate_summary()
        with open(output_path, "w") as f:
            f.write(f"Research Paper Review\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Paper: {metadata.get('title', 'Unknown')}\n")
            f.write(f"Author: {metadata.get('author', 'Unknown')}\n")
            f.write("\n" + summary)


@main.command()
def check_config():
    """Check API configuration and available providers."""
    console.print("\n[bold blue]Sibyl Configuration Check[/bold blue]\n")

    config = SibylConfig.from_env()
    providers = config.get_active_providers()

    if not providers:
        console.print(
            "[bold red]No API keys configured![/bold red]\n"
            "Please create a .env file with your API keys.\n"
            "See .env.example for the required format."
        )
        return

    table = Table(title="Configured Providers", show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Status", justify="center")

    for provider in ["openai", "anthropic", "google"]:
        provider_config = getattr(config, provider)
        if provider_config:
            table.add_row(
                provider_config.name, provider_config.model, "[green]✓ Configured[/green]"
            )
        else:
            table.add_row(provider.title(), "N/A", "[red]✗ Not configured[/red]")

    console.print(table)
    console.print(f"\n[bold]Total active providers:[/bold] {len(providers)}")


if __name__ == "__main__":
    main()
