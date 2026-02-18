# Practical Example: Reviewing a Research Paper

This guide walks through a complete example of using Sibyl to review a research paper.

## Scenario

You have a research paper PDF called `machine_learning_paper.pdf` and want to get comprehensive reviews from multiple AI models to help evaluate its quality.

## Step-by-Step Walkthrough

### Step 1: Initial Setup (One-time)

```bash
# Install Sibyl
cd sibyl
pip install -e .

# Set up your API keys
cp .env.example .env

# Edit .env and add your keys:
# OPENAI_API_KEY=sk-proj-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=AIza...
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
│ OpenAI     │ gpt-4                    │ ✓ Configured  │
│ Anthropic  │ claude-3-sonnet-20240229 │ ✓ Configured  │
│ Google     │ gemini-pro               │ ✓ Configured  │
└────────────┴──────────────────────────┴───────────────┘

Total active providers: 3
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

2. **Review Generation** (30-60 seconds per model)
   ```
   Step 2: Generating reviews...
   
   ⠋ Reviewing with openai...
     ✓ openai: Score 8/10, Recommendation: Accept
   
   ⠋ Reviewing with anthropic...
     ✓ anthropic: Score 7/10, Recommendation: Revise
   
   ⠋ Reviewing with google...
     ✓ google: Score 8/10, Recommendation: Accept
   ```

3. **Comparison** (instant)
   ```
   Step 3: Comparing reviews...
   
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┓
   ┃ Reviewer                 ┃ Score ┃ Recommendation ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━┩
   │ OpenAI (gpt-4)          │  8/10 │     Accept     │
   │ Anthropic (claude-3)    │  7/10 │     Revise     │
   │ Google (gemini-pro)     │  8/10 │     Accept     │
   └──────────────────────────┴───────┴────────────────┘
   
   Score Statistics:
     Mean: 7.67
     Std Dev: 0.58
     Range: 7 - 8
   
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

### Step 5: Review with Specific Models

If you only want reviews from certain providers:

```bash
# Use only OpenAI (fastest single provider)
sibyl review machine_learning_paper.pdf -p openai

# Use OpenAI and Anthropic (best quality)
sibyl review machine_learning_paper.pdf -p openai -p anthropic

# Use Anthropic and Google (cost-effective)
sibyl review machine_learning_paper.pdf -p anthropic -p google
```

### Step 6: Handle Long Papers

For papers with many pages (e.g., 50+ pages), limit extraction to save costs:

```bash
# Review only the first 20 pages
sibyl review long_paper.pdf --max-pages 20
```

**Tip:** For very long papers, consider reviewing:
- First 20 pages (intro, related work, methodology)
- Or extract abstract, intro, and conclusions manually

## Understanding Your Results

### Example Review Output

Let's say OpenAI GPT-4 provided this review:

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

### Interpreting Disagreements

If models give different scores (e.g., 6, 8, 9):

**Check why:**
1. Read detailed feedback from each model
2. Look for patterns in what they emphasize
3. Consider which perspective aligns with your goals

**Common patterns:**
- **GPT-4** often focuses on technical rigor
- **Claude** balances technical and practical aspects
- **Gemini** emphasizes novelty and applications

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
# Quick screen with Google (fast and cheap)
sibyl review submission.pdf -p google -o quick_screen.txt

# Full review for promising papers
sibyl review submission.pdf -o full_review.txt
```

### Pattern 3: Literature Review

```bash
# Review multiple papers from your field
for paper in papers/*.pdf; do
    name=$(basename "$paper" .pdf)
    sibyl review "$paper" -o "reviews/${name}_review.json"
done
```

### Pattern 4: Cost-Conscious Usage

```bash
# Start with cheapest option
sibyl review paper.pdf -p google

# If scores are borderline, get second opinion
sibyl review paper.pdf -p anthropic

# If still unclear, use all three
sibyl review paper.pdf
```

## Tips from Experience

### When Reviews Agree (Strong Consensus)

**All score 8-10:**
- High-quality paper, likely accept
- Check detailed feedback for minor improvements
- Consider submitting to top-tier venues

**All score 6-7:**
- Solid but not exceptional
- Focus on issues all models identified
- Consider major revisions

**All score below 6:**
- Significant issues present
- May need fundamental rework
- Consider feedback carefully before resubmitting

### When Reviews Disagree (No Consensus)

**Scores differ by 3+ points:**
- Paper has polarizing elements (this isn't necessarily bad!)
- Read detailed feedback carefully
- May indicate novel/controversial approach
- Human expert review recommended

**Mixed recommendations (Accept/Revise/Reject):**
- Normal for borderline papers
- Look at common themes in feedback
- Address concerns from all reviewers
- Consider your target venue's standards

## Troubleshooting Common Issues

### Issue: "Rate limit exceeded"

**Solution:**
```bash
# Wait 60 seconds, then retry
sleep 60
sibyl review paper.pdf

# Or use fewer providers
sibyl review paper.pdf -p anthropic
```

### Issue: "PDF extraction failed"

**Solution:**
```bash
# Try limiting pages
sibyl review paper.pdf --max-pages 20

# Check if PDF is password-protected
# (Sibyl cannot process encrypted PDFs)
```

### Issue: "Out of tokens"

**Solution:**
```bash
# Reduce paper length
sibyl review paper.pdf --max-pages 15

# Or check your API account balance
```

## Cost Example

For a 15-page paper reviewed with all three models:

- OpenAI GPT-4: ~$0.30
- Anthropic Claude: ~$0.15
- Google Gemini: ~$0.05
- **Total: ~$0.50**

Monthly budget planning:
- 10 papers/month: ~$5
- 50 papers/month: ~$25
- 100 papers/month: ~$50

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
