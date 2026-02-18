# Practical Example: Reviewing a Research Paper

This guide walks through a complete example of using Sibyl to review a research paper with local open-source LLMs.

## Scenario

You have a research paper PDF called `machine_learning_paper.pdf` and want to get a comprehensive review using local AI models to help evaluate its quality.

## Step-by-Step Walkthrough

### Step 1: Initial Setup (One-time)

```bash
# Install Ollama from https://ollama.ai
# Follow the installation instructions for your OS

# Pull a model (we'll use Llama 3.2)
ollama pull llama3.2

# Verify the model is available
ollama list

# Clone and install Sibyl
cd sibyl
pip install -e .

# Set up your configuration
cp .env.example .env

# Edit .env and configure:
# OLLAMA_MODEL=llama3.2
# OLLAMA_BASE_URL=http://localhost:11434
```

### Step 2: Verify Configuration

```bash
sibyl check-config
```

**Expected output:**
```
Sibyl Configuration Check

┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Provider   ┃ Model                     ┃ Status        ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Ollama     │ llama3.2                 │ ✓ Configured  │
└────────────┴──────────────────────────┴───────────────┘

Total active providers: 1
```

### Step 3: Run Your First Review

```bash
sibyl review machine_learning_paper.pdf
```

**What happens:**

1. **PDF Parsing** (5-10 seconds)
   ```
   Step 1: Extracting text from PDF...
     Title: Novel Approaches to Deep Learning
     Author: Dr. Jane Smith
     Pages: 12
     Extracted: 32,451 characters
   ```

2. **Review Generation** (1-5 minutes depending on model size and hardware)
   ```
   Step 2: Generating reviews...
   
   ⠋ Reviewing with ollama...
     ✓ ollama: Score 8/10, Recommendation: Accept
   ```

3. **Results Display** (instant)
   ```
   Step 3: Comparing reviews...
   
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┓
   ┃ Reviewer                 ┃ Score ┃ Recommendation ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━┩
   │ Ollama (llama3.2)       │  8/10 │     Accept     │
   └──────────────────────────┴───────┴────────────────┘
   
   Score Statistics:
     Mean: 8.00
     Std Dev: 0.00
     Range: 8 - 8
   
   Consensus: Accept
   ```

### Step 4: Save Results for Later

```bash
sibyl review machine_learning_paper.pdf -o ml_paper_review.txt
```

This saves a detailed report including:
- All individual reviews
- Detailed feedback from each model
- Comparative statistics
- Recommendations

### Step 5: Compare Different Models

To compare different models, run reviews sequentially with different models:

```bash
# Review with Llama 3.2
OLLAMA_MODEL=llama3.2 sibyl review machine_learning_paper.pdf -o review_llama.txt

# Review with Mistral
OLLAMA_MODEL=mistral sibyl review machine_learning_paper.pdf -o review_mistral.txt

# Review with Phi-3
OLLAMA_MODEL=phi3 sibyl review machine_learning_paper.pdf -o review_phi.txt
```

### Step 6: Handle Long Papers

For papers with many pages (e.g., 50+ pages), limit extraction to save processing time:

```bash
# Review only the first 20 pages
sibyl review long_paper.pdf --max-pages 20
```

**Tip:** For very long papers, consider reviewing:
- First 20 pages (intro, related work, methodology)
- Or extract abstract, intro, and conclusions manually

## Understanding Your Results

### Example Review Output

Let's say Llama 3.2 provided this review:

```
NOVELTY:
The paper introduces a hybrid architecture combining CNNs and Transformers 
in a novel way. While individual components are well-known, their integration 
for this specific task is original. Score: 8/10

METHODOLOGY:
The experimental design is solid with appropriate baselines and ablation studies. 
Dataset selection is appropriate, though sample size could be larger. 
Statistical analysis is rigorous. Score: 7/10

RESULTS:
Results show significant improvement over baselines (15% on average). 
Results are well-presented with appropriate visualizations. 
Some edge cases need more discussion. Score: 8/10

CLARITY:
Paper is well-written with clear structure. Some technical sections could 
benefit from more explanation. Figures are clear and informative. Score: 8/10

IMPACT:
Moderate to high impact. The technique is applicable to various domains 
and results are reproducible. Code availability is a plus. Score: 7/10

LIMITATIONS:
Authors acknowledge computational cost and limited dataset scope. 
More discussion on failure cases would strengthen the paper.

STRENGTHS:
- Novel architectural approach
- Rigorous experimental design
- Strong empirical results
- Reproducible with code release
- Well-written and clear

SCORE: 8

RECOMMENDATION: Accept

DETAILED FEEDBACK:
This is a strong paper that makes a solid contribution to the field. 
The hybrid architecture is novel and results are convincing...
[continues]
```

### Comparing Different Models

If you run reviews with different models and get different scores (e.g., 6, 8, 9):

**Check why:**
1. Read detailed feedback from each model
2. Look for patterns in what they emphasize
3. Consider which perspective aligns with your goals

**Common patterns:**
- **Llama** provides balanced, comprehensive reviews
- **Mistral** focuses on technical rigor and methodology
- **Phi-3** gives concise, focused feedback
- **Gemma** emphasizes practical implications

## Real-World Usage Patterns

### Pattern 1: Self-Review Before Submission

```bash
# Review your own paper
sibyl review my_draft.pdf -o draft_review_v1.txt

# After revisions
sibyl review my_revised_draft.pdf -o draft_review_v2.txt

# Compare the two reviews manually
```

### Pattern 2: Conference Paper Screening

```bash
# Quick screen with a fast model (Phi-3 or small Llama)
OLLAMA_MODEL=phi3 sibyl review submission.pdf -o quick_screen.txt

# Full review with larger model for promising papers
OLLAMA_MODEL=mistral sibyl review submission.pdf -o full_review.txt
```

### Pattern 3: Literature Review

```bash
# Review multiple papers from your field
for paper in papers/*.pdf; do
    name=$(basename "$paper" .pdf)
    sibyl review "$paper" -o "reviews/${name}_review.json"
done
```

### Pattern 4: Model Comparison

```bash
# Try different models for comparison
for model in llama3.2 mistral phi3; do
    OLLAMA_MODEL=$model sibyl review paper.pdf -o "review_${model}.txt"
done
```

## Tips from Experience

### Score Interpretation

**Score 8-10:**
- High-quality paper, likely accept
- Check detailed feedback for minor improvements
- Consider submitting to top-tier venues

**Score 6-7:**
- Solid but not exceptional
- Focus on identified issues
- Consider major revisions

**Score below 6:**
- Significant issues present
- May need fundamental rework
- Consider feedback carefully before resubmitting

### When Using Multiple Models

**Scores differ by 1-2 points:**
- Normal variation in perspective
- Look for common themes in feedback
- Generally safe to follow the trend

**Scores differ by 3+ points:**
- Paper has polarizing elements
- Read detailed feedback carefully
- May indicate novel/controversial approach
- Human expert review recommended

## Troubleshooting Common Issues

### Issue: "Failed to connect to Ollama"

**Solution:**
```bash
# Make sure Ollama is running
ollama serve

# Verify it's accessible
curl http://localhost:11434/api/tags

# Then retry
sibyl review paper.pdf
```

### Issue: "PDF extraction failed"

**Solution:**
```bash
# Try limiting pages
sibyl review paper.pdf --max-pages 20

# Check if PDF is password-protected
# (Sibyl cannot process encrypted PDFs)
```

### Issue: "Slow performance"

**Solution:**
```bash
# Use a smaller, faster model
OLLAMA_MODEL=phi3 sibyl review paper.pdf

# Or limit paper length
sibyl review paper.pdf --max-pages 15

# Or use quantized versions for speed
OLLAMA_MODEL=llama3.2:1b sibyl review paper.pdf
```

## Performance Considerations

### Processing Time

For a 15-page paper:

- **Llama 3.2:1b**: 1-2 minutes (8GB RAM)
- **Llama 3.2:3b**: 2-3 minutes (16GB RAM)
- **Mistral 7B**: 3-5 minutes (16GB RAM)
- **Phi-3 Mini**: 1-2 minutes (8GB RAM)

*Times vary based on hardware (CPU/GPU) and system load*

### Hardware Requirements

- **Minimum**: 8GB RAM for small models (1-3B params)
- **Recommended**: 16GB RAM for better models (3-7B params)
- **Optimal**: 32GB+ RAM with GPU for larger models

## Benefits of Local LLMs

✅ **Privacy**: All data stays on your machine
✅ **Cost**: Zero API fees - completely free
✅ **Control**: Choose and customize any model
✅ **Availability**: Works offline
✅ **Speed**: No network latency (with good hardware)

## Next Steps

After getting comfortable with basic usage:

1. **Try programmatic usage** - See `examples/example_usage.py`
2. **Customize for your field** - Modify review criteria
3. **Build workflows** - Integrate into your research process
4. **Share feedback** - Help improve Sibyl

## Questions?

- Check [README.md](README.md) for comprehensive documentation
- See [USAGE.md](USAGE.md) for more examples
- Open an issue on GitHub for support

Happy reviewing! 🔮
