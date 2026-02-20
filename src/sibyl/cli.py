"""Command-line interface for Sibyl."""

import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from sibyl.comparison import ReviewComparison
from sibyl.config import SibylConfig
from sibyl.llm.client.ollama import OllamaClient
from sibyl.pdf_parser import PDFParser
from sibyl.reviewer import ReviewSystem
from sibyl.storage.engine import Engine

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Sibyl - An LLM-powered research paper review system."""


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "--providers",
    "-p",
    multiple=True,
    type=click.Choice(["ollama"], case_sensitive=False),
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
def review(pdf_path: str, providers: tuple, output: str, max_pages: int) -> None:
    """Review a research paper PDF using LLMs.

    PDF_PATH: Path to the research paper PDF file
    """
    console.print("\n[bold blue]Sibyl Research Paper Review System[/bold blue]\n")

    config = SibylConfig.from_env()
    active_providers = config.get_active_providers()

    if not active_providers:
        console.print("[bold red]Error:[/bold red] No local LLM configured. Please set OLLAMA_MODEL in your .env file and ensure Ollama is running.")
        return

    if providers:
        providers_to_use = [p.lower() for p in providers]

        for provider in providers_to_use:
            if provider not in active_providers:
                console.print(f"[bold yellow]Warning:[/bold yellow] {provider} requested but not configured. Skipping.")
        providers_to_use = [p for p in providers_to_use if p in active_providers]
    else:
        providers_to_use = active_providers

    if not providers_to_use:
        console.print("[bold red]Error:[/bold red] No valid providers available for review.")
        return

    console.print(f"[bold]Paper:[/bold] {pdf_path}")
    console.print(f"[bold]Providers:[/bold] {', '.join(providers_to_use)}\n")

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
                provider_config = getattr(config, provider)
                if not provider_config:
                    continue

                client = OllamaClient(provider_config)
                reviewer = ReviewSystem(client)
                review = reviewer.review_paper(paper_text, paper_title=metadata.get("title", "Unknown"))
                reviews.append(review)

                progress.update(task, completed=True)
                console.print(f"  ✓ {provider}: Score {review.criteria.score}/5, Recommendation: {review.criteria.recommendation}")
            except Exception as e:
                console.print(f"  ✗ {provider}: [red]Error - {e!s}[/red]")

    if not reviews:
        console.print("\n[bold red]Error:[/bold red] No reviews were generated.")
        return

    console.print("\n[bold]Step 3:[/bold] Saving reviews to storage...\n")
    storage = Engine()
    for review in reviews:
        try:
            storage.save_review(
                review=review,
                pdf_filename=str(Path(pdf_path).name),
                pdf_path=pdf_path,
                paper_text=paper_text,
            )
        except Exception as e:
            console.print(f"  [yellow]Warning: Could not save review for {review.reviewer_model} to storage: {e}[/yellow]")

    console.print("[bold]Step 4:[/bold] Comparing reviews...\n")
    comparison = ReviewComparison(reviews)

    _display_results(reviews, comparison)

    if output:
        _save_results(output, reviews, comparison, metadata)
        console.print(f"\n[bold green]Results saved to:[/bold green] {output}")


def _display_results(reviews, comparison):
    """Display review results in a formatted table."""
    table = Table(title="Review Summary", show_header=True, header_style="bold magenta")
    table.add_column("Reviewer", style="cyan")
    table.add_column("Score", justify="center")
    table.add_column("Recommendation", justify="center")

    for review in reviews:
        table.add_row(
            review.reviewer_model,
            f"{review.criteria.score}/5",
            review.criteria.recommendation,
        )

    console.print(table)

    stats = comparison.get_score_statistics()
    console.print("\n[bold]Score Statistics:[/bold]")
    console.print(f"  Mean: {stats['mean']:.2f}")
    console.print(f"  Std Dev: {stats['std']:.2f}")
    console.print(f"  Range: {stats['min']} - {stats['max']}")

    console.print(f"\n[bold]Consensus:[/bold] {comparison.get_consensus_recommendation()}")


def _save_results(output_path: str, reviews, comparison, metadata):
    """Save review results to a file."""
    output_path = Path(output_path)

    if output_path.suffix == ".json":
        data = {
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
            "comparison": comparison.get_comparative_analysis(),
            "reviews": [
                {
                    "reviewer": r.reviewer_model,
                    "score": r.criteria.score,
                    "recommendation": r.criteria.recommendation,
                    "criteria": r.criteria.model_dump(),
                }
                for r in reviews
            ],
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
    else:
        summary = comparison.generate_summary()
        with open(output_path, "w") as f:
            f.write("Research Paper Review\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Paper: {metadata.get('title', 'Unknown')}\n")
            f.write(f"Author: {metadata.get('author', 'Unknown')}\n")
            f.write("\n" + summary)


@main.command()
def check_config():
    """Check configuration and available providers."""
    console.print("\n[bold blue]Sibyl Configuration Check[/bold blue]\n")

    config = SibylConfig.from_env()
    providers = config.get_active_providers()

    if not providers:
        console.print(
            "[bold red]No local LLM configured![/bold red]\n"
            "Please create a .env file with your Ollama configuration.\n"
            "See .env.example for the required format.\n"
            "Make sure Ollama is installed and running."
        )
        return

    table = Table(title="Configured Providers", show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Status", justify="center")

    for provider in ["ollama"]:
        provider_config = getattr(config, provider)
        if provider_config:
            table.add_row(provider_config.name, provider_config.model, "[green]✓ Configured[/green]")
        else:
            table.add_row(provider.title(), "N/A", "[red]✗ Not configured[/red]")

    console.print(table)
    console.print(f"\n[bold]Total active providers:[/bold] {len(providers)}")


@main.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
@click.option("--port", default=8000, type=int, help="Port to bind to (default: 8000)")
@click.option("--ssl", is_flag=True, help="Enable SSL with self-signed certificate")
def web(host: str, port: int, ssl: bool):
    """Start the web interface for Sibyl.

    This launches a web server that provides a user-friendly interface
    for uploading and reviewing research papers.
    """
    console.print("\n[bold blue]Starting Sibyl Web Interface[/bold blue]\n")

    ssl_certfile = None
    ssl_keyfile = None

    if ssl:
        import subprocess
        import tempfile
        from pathlib import Path

        cert_dir = Path(tempfile.gettempdir()) / "sibyl_certs"
        cert_dir.mkdir(exist_ok=True)
        cert_file = cert_dir / "cert.pem"
        key_file = cert_dir / "key.pem"

        if not cert_file.exists() or not key_file.exists():
            console.print("[bold]Generating self-signed SSL certificate...[/bold]")
            try:
                subprocess.run(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:4096",
                        "-keyout",
                        str(key_file),
                        "-out",
                        str(cert_file),
                        "-days",
                        "365",
                        "-nodes",
                        "-subj",
                        "/C=US/ST=State/L=City/O=Organization/CN=localhost",
                    ],
                    check=True,
                    capture_output=True,
                )
                console.print("[green]SSL certificate generated successfully.[/green]")
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]Error generating SSL certificate:[/bold red] {e}")
                return
            except FileNotFoundError:
                console.print("[bold red]Error: openssl not found. Please install openssl to use SSL.[/bold red]")
                return

        ssl_certfile = str(cert_file)
        ssl_keyfile = str(key_file)
        protocol = "https"
    else:
        protocol = "http"

    console.print(f"[bold]Server:[/bold] {protocol}://{host}:{port}")
    console.print("[bold]Press Ctrl+C to stop[/bold]\n")

    try:
        from sibyl.web_app import run_server

        run_server(host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)
    except ImportError:
        console.print("[bold red]Error:[/bold red] FastAPI and uvicorn are required for the web interface.\nInstall them with: pip install 'sibyl[web]'")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Server stopped.[/bold yellow]")


if __name__ == "__main__":
    main()
