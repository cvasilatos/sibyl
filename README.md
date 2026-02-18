# Sibyl 🔮

An LLM-powered research paper review system that leverages multiple AI models to provide comprehensive, comparative reviews of academic papers.

## Overview

Sibyl is a Python-based tool that uses Large Language Models (LLMs) from multiple providers to automatically review research papers. It extracts text from PDF files, generates structured reviews using different AI models, and provides comparative analysis to help identify consensus and differences in assessment.

### Key Features

- 📄 **PDF Parsing**: Automatically extract text from research paper PDFs
- 🤖 **Multi-Model Support**: Compare reviews from OpenAI GPT-4, Anthropic Claude, and Google Gemini
- 📊 **Structured Reviews**: Get consistent, structured feedback across multiple dimensions
- 📈 **Comparative Analysis**: View statistics, consensus, and differences across reviewers
- 💻 **CLI Interface**: Easy-to-use command-line interface with rich formatting
- 🎯 **Flexible Configuration**: Use any combination of available LLM providers

## Review Criteria

Each review includes assessment of:

1. **Novelty**: Originality and innovation of the research
2. **Methodology**: Quality of research methods and experimental design
3. **Results**: Significance and validity of findings
4. **Clarity**: Writing quality and presentation
5. **Impact**: Potential contribution to the field
6. **Limitations**: Weaknesses and constraints
7. **Strengths**: Key positive aspects
8. **Overall Score**: Numerical rating (1-10)
9. **Recommendation**: Accept, Revise, or Reject
10. **Detailed Feedback**: Comprehensive suggestions for improvement

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/cvasilatos/sibyl.git
cd sibyl
```

2. **Install the package**:
```bash
pip install -e .
```

3. **Configure API keys**:

Create a `.env` file in the project root with your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

You can use one, two, or all three providers. Sibyl will work with any configured providers.

### Getting API Keys

- **OpenAI**: Get your API key at https://platform.openai.com/api-keys
- **Anthropic**: Get your API key at https://console.anthropic.com/
- **Google**: Get your API key at https://makersuite.google.com/app/apikey

## Usage

### Check Configuration

First, verify your API keys are configured correctly:

```bash
sibyl check-config
```

### Review a Paper

Review a research paper PDF using all configured providers:

```bash
sibyl review path/to/paper.pdf
```

### Use Specific Providers

Review using only specific providers:

```bash
# Use only OpenAI
sibyl review paper.pdf -p openai

# Use OpenAI and Anthropic
sibyl review paper.pdf -p openai -p anthropic

# Use all three providers
sibyl review paper.pdf -p openai -p anthropic -p google
```

### Save Results

Save the review results to a file:

```bash
# Save as text
sibyl review paper.pdf -o review_results.txt

# Save as JSON
sibyl review paper.pdf -o review_results.json
```

### Limit Pages

For long papers, you can limit the number of pages to review:

```bash
sibyl review paper.pdf --max-pages 20
```

## Example Output

```
Sibyl Research Paper Review System

Paper: research_paper.pdf
Providers: openai, anthropic, google

Step 1: Extracting text from PDF...
  Title: Novel Approaches to Machine Learning
  Author: John Doe
  Pages: 15
  Extracted: 45231 characters

Step 2: Generating reviews...
  ✓ openai: Score 8/10, Recommendation: Accept
  ✓ anthropic: Score 7/10, Recommendation: Revise
  ✓ google: Score 8/10, Recommendation: Accept

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

## Project Structure

```
sibyl/
├── src/sibyl/
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── pdf_parser.py       # PDF text extraction
│   ├── llm_client.py       # LLM provider clients
│   ├── reviewer.py         # Review generation system
│   └── comparison.py       # Multi-review comparison
├── tests/                  # Test suite
├── examples/               # Example papers and outputs
├── pyproject.toml         # Project configuration
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Architecture

### Components

1. **PDF Parser**: Extracts text and metadata from research paper PDFs using `pypdf`
2. **LLM Clients**: Abstraction layer for different LLM providers (OpenAI, Anthropic, Google)
3. **Review System**: Generates structured reviews using LLMs with consistent prompts
4. **Comparison Engine**: Analyzes multiple reviews to identify patterns and consensus
5. **CLI Interface**: User-friendly command-line tool with rich formatting

### Design Principles

- **Provider Agnostic**: Easy to add new LLM providers
- **Structured Output**: Consistent review format across all models
- **Minimal Dependencies**: Only essential libraries required
- **Extensible**: Simple to customize review criteria and prompts

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Type Checking

```bash
mypy src/
```

## Model Comparison

### Why Multiple Models?

Using multiple LLM providers offers several advantages:

1. **Diverse Perspectives**: Different models may focus on different aspects
2. **Consensus Building**: Agreement across models strengthens confidence
3. **Bias Detection**: Inconsistencies may reveal model-specific biases
4. **Robustness**: Reduces dependence on a single provider
5. **Performance Evaluation**: Compare quality, speed, and cost

### Recommended Models

- **OpenAI GPT-4**: Excellent reasoning and detailed analysis
- **Anthropic Claude 3**: Strong ethical considerations and balanced reviews
- **Google Gemini Pro**: Fast inference and good value

## Limitations

- Requires API access to at least one LLM provider (costs apply)
- PDF text extraction may not work perfectly for all paper formats
- Review quality depends on the underlying LLM capabilities
- Long papers may hit token limits (use `--max-pages` to limit)
- Does not review figures, tables, or mathematical equations in detail

## Future Enhancements

- [ ] Support for more LLM providers (local models, other cloud providers)
- [ ] Batch processing of multiple papers
- [ ] Interactive web interface
- [ ] Custom review criteria and prompts
- [ ] Citation analysis integration
- [ ] Support for LaTeX and other document formats
- [ ] Fine-tuning on domain-specific papers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [OpenAI API](https://openai.com/api/)
- [Anthropic Claude](https://www.anthropic.com/)
- [Google Gemini](https://deepmind.google/technologies/gemini/)
- [pypdf](https://github.com/py-pdf/pypdf)
- [Click](https://click.palletsprojects.com/)
- [Rich](https://rich.readthedocs.io/)

## Contact

For questions, issues, or suggestions, please open an issue on GitHub.