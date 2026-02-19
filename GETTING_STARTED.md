# Getting Started with Sibyl

## Quick Start in 5 Minutes

### 1. Prerequisites

Ensure you have:
- **Python 3.9 or higher** (Python 3.12+ recommended for best compatibility)
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package installer and resolver
- **[Ollama](https://ollama.ai)** installed and running locally
- **Node.js 18+** and npm (only if you want to use the web interface)

### 2. Install Ollama

Visit [https://ollama.ai](https://ollama.ai) and download Ollama for your operating system.

**Verify installation:**
```bash
ollama --version
```

### 3. Pull a Model

Download a local LLM model:

```bash
# Recommended: Llama 3.2 (good balance of speed and quality)
ollama pull llama3.2

# Or try other models:
ollama pull mistral         # Excellent reasoning
ollama pull phi3            # Small but powerful
ollama pull gemma2          # Google's efficient model
ollama pull qwen2.5         # Strong multilingual
ollama pull deepseek-coder  # Best for technical papers
```

**Verify the model:**
```bash
ollama list
```

### 4. Installation

```bash
# Clone the repository
git clone https://github.com/cvasilatos/sibyl.git
cd sibyl

# Install uv if not already installed
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install Sibyl
uv pip install -e .

# If you want the web interface, install with web dependencies:
uv pip install -e ".[web]"
```

### 5. Configure Sibyl

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` and set your model:

```bash
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

**Optional: Enable GROBID for Better Metadata Extraction**

If your PDFs don't have embedded metadata (title, authors), you can enable GROBID for automatic extraction:

```bash
# Start GROBID service using Docker
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0

# In your .env file, add:
GROBID_ENABLED=true
GROBID_URL=http://localhost:8070
```

This is optional but recommended for academic papers without proper metadata.

### 6. Verify Setup

Check that everything is configured correctly:

```bash
sibyl check-config
```

You should see a table showing your configured model.

### 7. Review Your First Paper

```bash
sibyl review path/to/your/paper.pdf
```

That's it! Sibyl will:
1. Extract text from the PDF
2. Generate a review using your local LLM
3. Display structured feedback and scoring

## What Happens During a Review?

When you run `sibyl review paper.pdf`, here's what happens:

1. **PDF Parsing**: Sibyl extracts text and metadata from your PDF
2. **Review Generation**: Your configured local LLM reads the paper and provides:
   - Assessment of novelty, methodology, results, clarity, and impact
   - Identification of limitations and strengths
   - Overall score (1-10)
   - Recommendation (Accept/Revise/Reject)
   - Detailed feedback
3. **Results Display**: Sibyl displays the structured review with formatting

## Common Use Cases

### Single Model Review

```bash
# Review with your configured model
sibyl review paper.pdf
```

### Compare Multiple Models

To compare different models, you can run reviews sequentially:

```bash
# Review with Llama
sibyl review paper.pdf -o review_llama.json

# Change model in .env to mistral, then:
sibyl review paper.pdf -o review_mistral.json

# For technical papers, try DeepSeek:
# Change model in .env to deepseek-coder, then:
sibyl review paper.pdf -o review_deepseek.json

# Compare the results manually
```

### Save Results for Later

```bash
# Save as formatted text
sibyl review paper.pdf -o review.txt

# Save as JSON for processing
sibyl review paper.pdf -o review.json
```

### Review Long Papers

```bash
# Limit to first 20 pages (to save processing time)
sibyl review paper.pdf --max-pages 20
```

## Understanding the Output

### Review Scores

- **9-10**: Exceptional - Major contribution to the field
- **7-8**: Strong - Accept with minor revisions
- **5-6**: Average - Major revisions needed
- **3-4**: Weak - Likely reject
- **1-2**: Poor - Reject

### Consensus

When comparing reviews from different models (run sequentially):

- **Strong consensus**: Models agree (±1 point) - High confidence
- **Moderate consensus**: Most models agree - Normal variation
- **Mixed/No consensus**: Significant disagreement - Needs human judgment

## Tips for Best Results

1. **Choose the right model**: Larger models generally provide better quality
2. **Ensure sufficient resources**: Models need adequate RAM/VRAM
3. **Start with smaller papers**: Test with shorter papers first
4. **Save your results**: Keep records for comparison over time
5. **Read the details**: Scores are just summaries; the detailed feedback is most valuable

## Troubleshooting

### "No local LLM configured"

Make sure:
- `.env` file exists in the project root
- `OLLAMA_MODEL` is set in the `.env` file
- Ollama is installed and running (`ollama list` should work)
- You have pulled the model (`ollama pull <model-name>`)

### "Failed to connect to Ollama"

- Ensure Ollama is running: `ollama serve` (usually runs automatically)
- Check the base URL in `.env` matches your Ollama setup
- Default is `http://localhost:11434`

### "Error extracting PDF"

- Ensure the PDF is not encrypted or password-protected
- Try using `--max-pages` to limit extraction
- Check that the file path is correct
- If PDF metadata is empty, consider enabling GROBID (see configuration section above)

### Slow Performance

If reviews are taking too long:
- Use a smaller model (e.g., `llama3.2:1b` instead of `llama3.2:3b`)
- Reduce the number of pages with `--max-pages`
- Ensure you have sufficient RAM for the model
- Consider using GPU acceleration if available

## Next Steps

- Read [USAGE.md](USAGE.md) for detailed usage examples
- Check [docs/MODEL_COMPARISON.md](docs/MODEL_COMPARISON.md) to understand different local models
- See [examples/example_usage.py](examples/example_usage.py) for programmatic usage
- Read [CONTRIBUTING.md](CONTRIBUTING.md) if you want to contribute

## Getting Help

- Check the [README.md](README.md) for comprehensive documentation
- Open an issue on GitHub for bugs or feature requests
- Review existing issues for similar problems

## Hardware Requirements

### Minimum Requirements
- **CPU**: Modern multi-core processor
- **RAM**: 8GB (for small models like llama3.2:1b, phi3:mini)
- **Storage**: 5GB+ for models
- **OS**: Linux, macOS, or Windows

### Recommended Requirements
- **RAM**: 16GB+ (for models like llama3.2:3b, mistral)
- **GPU**: NVIDIA GPU with 8GB+ VRAM (optional, but significantly faster)
- **Storage**: 20GB+ for multiple models

### Model Size Guide
- **1-3B parameters**: 8GB RAM minimum
- **7B parameters**: 16GB RAM recommended
- **13B+ parameters**: 32GB RAM recommended

Enjoy using Sibyl! 🔮
