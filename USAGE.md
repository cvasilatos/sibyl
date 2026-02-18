# Sibyl Usage Guide

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/cvasilatos/sibyl.git
cd sibyl

# Install the package
pip install -e .
```

### 2. Configure API Keys

Create a `.env` file with your API keys:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
```

### 3. Verify Configuration

```bash
sibyl check-config
```

### 4. Review a Paper

```bash
sibyl review path/to/paper.pdf
```

## Advanced Usage

### Selecting Specific Models

```bash
# Use only OpenAI GPT-4
sibyl review paper.pdf -p openai

# Compare OpenAI and Anthropic
sibyl review paper.pdf -p openai -p anthropic
```

### Saving Results

```bash
# Save as formatted text
sibyl review paper.pdf -o results.txt

# Save as JSON for further processing
sibyl review paper.pdf -o results.json
```

### Processing Long Papers

For papers with many pages, you can limit the extraction:

```bash
# Only review the first 20 pages
sibyl review paper.pdf --max-pages 20
```

## Understanding the Output

### Review Structure

Each review includes:

1. **Novelty**: Is the research original?
2. **Methodology**: Are the methods sound?
3. **Results**: Are findings significant?
4. **Clarity**: Is it well-written?
5. **Impact**: Will it contribute to the field?
6. **Limitations**: What are the weaknesses?
7. **Strengths**: What are the strong points?
8. **Score**: Numerical rating (1-10)
9. **Recommendation**: Accept, Revise, or Reject
10. **Detailed Feedback**: Specific suggestions

### Interpreting Scores

- **9-10**: Exceptional paper, significant contribution
- **7-8**: Strong paper, accept with minor revisions
- **5-6**: Average paper, major revisions needed
- **3-4**: Weak paper, likely reject
- **1-2**: Poor quality, reject

### Consensus Indicators

- **Strong consensus**: All models agree
- **Moderate consensus**: Majority agreement
- **Mixed**: Significant disagreement

## Best Practices

### For Best Results

1. **Use multiple models**: Get diverse perspectives
2. **Review the full comparison**: Look beyond just scores
3. **Check for consistency**: Agreement increases confidence
4. **Read detailed feedback**: The most valuable insights are in the details
5. **Save results**: Keep records for later comparison

### Cost Optimization

1. **Use `--max-pages`**: Limit review to key sections
2. **Select specific providers**: Don't use all models every time
3. **Test with one model first**: Verify the system works before using all
4. **Batch similar papers**: Plan your reviews to use API calls efficiently

## Integration Examples

### In a Research Workflow

```bash
# Review a draft before submission
sibyl review draft.pdf -o draft_review.json

# Compare with feedback after revisions
sibyl review revised.pdf -o revised_review.json
```

### For Multiple Papers

```bash
# Review all papers in a directory
for paper in papers/*.pdf; do
    sibyl review "$paper" -o "reviews/$(basename "$paper" .pdf)_review.txt"
done
```

### JSON Output Processing

```python
import json

# Load review results
with open('review_results.json', 'r') as f:
    data = json.load(f)

# Extract scores
scores = [review['score'] for review in data['reviews']]
average_score = sum(scores) / len(scores)

print(f"Average score: {average_score}")
```

## Troubleshooting

### API Key Issues

```
Error: No API keys configured
```
- Check that `.env` file exists
- Verify API keys are correct
- Ensure keys are not quoted in the `.env` file

### PDF Extraction Issues

```
Error extracting PDF
```
- Ensure the PDF is not encrypted
- Try `--max-pages` to limit extraction
- Check that the file path is correct

### Rate Limiting

```
Rate limit exceeded
```
- Wait a few minutes before retrying
- Review API usage limits for your provider
- Consider using fewer providers

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation
- Review existing issues for similar problems
