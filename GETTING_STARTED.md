# Getting Started with Sibyl

## Quick Start in 5 Minutes

### 1. Prerequisites

Ensure you have:
- Python 3.9 or higher
- pip (Python package installer)
- At least one API key from OpenAI, Anthropic, or Google

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/cvasilatos/sibyl.git
cd sibyl

# Install Sibyl
pip install -e .
```

### 3. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add at least one API key:

```bash
# You need at least one of these:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
```

**Where to get API keys:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/
- Google: https://makersuite.google.com/app/apikey

### 4. Verify Setup

Check that everything is configured correctly:

```bash
sibyl check-config
```

You should see a table showing which providers are configured.

### 5. Review Your First Paper

```bash
sibyl review path/to/your/paper.pdf
```

That's it! Sibyl will:
1. Extract text from the PDF
2. Generate reviews from all configured LLM providers
3. Compare the reviews and show you a summary

## What Happens During a Review?

When you run `sibyl review paper.pdf`, here's what happens:

1. **PDF Parsing**: Sibyl extracts text and metadata from your PDF
2. **Review Generation**: Each configured LLM reads the paper and provides:
   - Assessment of novelty, methodology, results, clarity, and impact
   - Identification of limitations and strengths
   - Overall score (1-10)
   - Recommendation (Accept/Revise/Reject)
   - Detailed feedback
3. **Comparison**: Sibyl analyzes all reviews to show:
   - Score statistics (mean, std dev, range)
   - Recommendation distribution
   - Consensus or disagreements

## Common Use Cases

### Compare Multiple Models

```bash
# Use all configured providers
sibyl review paper.pdf

# Use only specific providers
sibyl review paper.pdf -p openai -p anthropic
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
# Limit to first 20 pages (to save costs)
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

- **Strong consensus**: All models agree (±1 point) - High confidence
- **Moderate consensus**: 2/3 models agree - Normal variation
- **Mixed/No consensus**: Significant disagreement - Needs human judgment

## Tips for Best Results

1. **Use multiple models**: Different perspectives increase confidence
2. **Start small**: Test with one model first, then use all three
3. **Check consensus**: Agreement across models strengthens the assessment
4. **Read the details**: Scores are just summaries; the detailed feedback is most valuable
5. **Save your results**: Keep records for comparison over time

## Troubleshooting

### "No API keys configured"

Make sure:
- `.env` file exists in the project root
- API keys are correct and not wrapped in quotes
- API keys have the correct format

### "Error extracting PDF"

- Ensure the PDF is not encrypted or password-protected
- Try using `--max-pages` to limit extraction
- Check that the file path is correct

### Rate Limiting

If you hit API rate limits:
- Wait a few minutes before retrying
- Use fewer providers
- Reduce the number of pages with `--max-pages`

## Next Steps

- Read [USAGE.md](USAGE.md) for detailed usage examples
- Check [docs/MODEL_COMPARISON.md](docs/MODEL_COMPARISON.md) to understand model differences
- See [examples/example_usage.py](examples/example_usage.py) for programmatic usage
- Read [CONTRIBUTING.md](CONTRIBUTING.md) if you want to contribute

## Getting Help

- Check the [README.md](README.md) for comprehensive documentation
- Open an issue on GitHub for bugs or feature requests
- Review existing issues for similar problems

## Cost Considerations

Using LLM APIs incurs costs. Approximate costs per review (varies by paper length):

- **OpenAI GPT-4**: $0.10 - $0.50 per review
- **Anthropic Claude**: $0.05 - $0.30 per review
- **Google Gemini**: $0.01 - $0.10 per review

Tips to manage costs:
- Use `--max-pages` to limit paper length
- Start with Gemini for quick/cheap reviews
- Use all three models only for important papers
- Monitor your API usage dashboards

Enjoy using Sibyl! 🔮
