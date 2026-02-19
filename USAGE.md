# Sibyl Usage Guide

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/cvasilatos/sibyl.git
cd sibyl

# Install the package
# Using pip (standard)
pip install -e .

# Or using uv (faster alternative)
uv pip install -e .

# For web interface support, use:
pip install -e ".[web]"
# or with uv:
uv pip install -e ".[web]"
```

### 2. Install and Configure Ollama

```bash
# Install Ollama from https://ollama.ai

# Pull a model
ollama pull llama3.2
```

### 3. Configure Sibyl

Create a `.env` file:

```bash
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

### 4. Verify Configuration

```bash
sibyl check-config
```

### 5. Review a Paper

```bash
sibyl review path/to/paper.pdf
```

## Advanced Usage

### Selecting Different Models

To use different models, update your `.env` file:

```bash
# Use Mistral
OLLAMA_MODEL=mistral

# Use Phi-3
OLLAMA_MODEL=phi3

# Use DeepSeek Coder
OLLAMA_MODEL=deepseek-coder

# Use a specific variant
OLLAMA_MODEL=llama3.2:3b
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

1. **Choose appropriate models**: Larger models provide more detailed analysis
2. **Optimize hardware**: Ensure sufficient RAM for your chosen model
3. **Review incrementally**: Start with abstracts/introductions before full papers
4. **Read detailed feedback**: The most valuable insights are in the details
5. **Save results**: Keep records for later comparison

### Performance Optimization

1. **Use appropriate model sizes**: Match model to your hardware
2. **Limit pages for long papers**: Use `--max-pages` for efficiency
3. **Consider quantized models**: Use smaller quantizations (e.g., Q4) for speed
4. **Monitor resource usage**: Keep an eye on RAM/CPU usage

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

### Comparing Different Models

```bash
# Review with Llama
OLLAMA_MODEL=llama3.2 sibyl review paper.pdf -o review_llama.txt

# Review with Mistral
OLLAMA_MODEL=mistral sibyl review paper.pdf -o review_mistral.txt

# Review with Phi
OLLAMA_MODEL=phi3 sibyl review paper.pdf -o review_phi.txt

# Review with DeepSeek Coder (good for technical papers)
OLLAMA_MODEL=deepseek-coder sibyl review paper.pdf -o review_deepseek.txt

# Review with Qwen (good for multilingual papers)
OLLAMA_MODEL=qwen2.5 sibyl review paper.pdf -o review_qwen.txt
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

### Configuration Issues

```
Error: No local LLM configured
```
- Check that `.env` file exists
- Verify `OLLAMA_MODEL` is set
- Ensure Ollama is installed: `ollama --version`
- Make sure you've pulled the model: `ollama list`

### Connection Issues

```
Failed to connect to Ollama
```
- Verify Ollama is running: `ollama serve`
- Check base URL matches your setup (default: http://localhost:11434)
- Test with: `curl http://localhost:11434/api/tags`

### PDF Extraction Issues

```
Error extracting PDF
```
- Ensure the PDF is not encrypted
- Try `--max-pages` to limit extraction
- Check that the file path is correct

### Performance Issues

```
Review is taking too long
```
- Use a smaller model (llama3.2:1b, phi3:mini)
- Limit pages with `--max-pages`
- Ensure adequate RAM is available
- Close other applications to free resources

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation
- Review existing issues for similar problems
