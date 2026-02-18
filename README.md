# Sibyl 🔮

An LLM-powered research paper review system that leverages local open-source AI models to provide comprehensive, comparative reviews of academic papers.

## Overview

Sibyl is a Python-based tool that uses Local Large Language Models (LLMs) running via Ollama to automatically review research papers. It extracts text from PDF files, generates structured reviews using different local AI models, and provides comparative analysis to help identify consensus and differences in assessment.

### Key Features

- 📄 **PDF Parsing**: Automatically extract text from research paper PDFs
- 🤖 **Local Model Support**: Run open-source models locally via Ollama (Llama, Mistral, Phi, Gemma, Qwen, DeepSeek, etc.)
- 🔒 **Privacy First**: All processing happens locally - no data sent to external APIs
- 💰 **Zero Cost**: No API fees or subscription costs
- 📊 **Structured Reviews**: Get consistent, structured feedback across multiple dimensions
- 📈 **Comparative Analysis**: View statistics, consensus, and differences across reviewers
- 💻 **CLI Interface**: Easy-to-use command-line interface with rich formatting
- 🌐 **Web Interface**: Modern web application with drag-and-drop upload and real-time progress
- 🎯 **Flexible Configuration**: Use any Ollama-compatible models

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
- [Ollama](https://ollama.ai) installed and running

### Setup

1. **Install Ollama**:
   
   Visit [https://ollama.ai](https://ollama.ai) and follow the installation instructions for your operating system.

2. **Pull a model**:
   ```bash
   # Pull a recommended model (Llama 3.2 is a good starting point)
   ollama pull llama3.2
   
   # Or choose from other models:
   # ollama pull mistral
   # ollama pull phi3
   # ollama pull gemma2
   # ollama pull qwen2.5
   ```

3. **Clone the repository**:
   ```bash
   git clone https://github.com/cvasilatos/sibyl.git
   cd sibyl
   ```

4. **Install the package**:
   ```bash
   # For CLI only
   pip install -e .
   
   # For CLI + Web Interface
   pip install -e ".[web]"
   ```

5. **Configure Sibyl**:

   Create a `.env` file in the project root:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set your model:
   ```
   OLLAMA_MODEL=llama3.2
   OLLAMA_BASE_URL=http://localhost:11434
   ```

### Recommended Models

- **llama3.2** (3B/1B): Fast, efficient, good quality
- **mistral** (7B): Excellent reasoning capabilities
- **phi3** (3.8B): Small but powerful from Microsoft
- **gemma2** (2B/9B): Google's efficient models
- **qwen2.5** (various sizes): Strong performance across tasks
- **deepseek-coder** (1.3B-33B): Specialized for code and technical content

Choose a model based on your hardware:
- **8GB RAM**: llama3.2:1b, phi3:mini, deepseek-coder:1.3b
- **16GB RAM**: llama3.2:3b, mistral:7b, gemma2:2b, deepseek-coder:6.7b
- **32GB+ RAM**: Any model, including larger variants

## Usage

### Web Interface (Recommended)

The easiest way to use Sibyl is through the web interface:

```bash
# Start the web server
sibyl web

# Open your browser to http://localhost:8000
# Drag and drop a PDF, click "Start Review", and watch the progress!
```

For more details, see the [Web App Documentation](docs/WEB_APP.md).

### Check Configuration

First, verify your Ollama setup:

```bash
sibyl check-config
```

### Review a Paper

Review a research paper PDF using your configured model:

```bash
sibyl review path/to/paper.pdf
```

### Use Specific Models

If you want to compare multiple models, configure multiple Ollama instances or run reviews sequentially:

```bash
# Review with default model
sibyl review paper.pdf

# You can also specify -p ollama explicitly
sibyl review paper.pdf -p ollama
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
Providers: ollama

Step 1: Extracting text from PDF...
  Title: Novel Approaches to Machine Learning
  Author: John Doe
  Pages: 15
  Extracted: 45231 characters

Step 2: Generating reviews...
  ✓ ollama: Score 8/10, Recommendation: Accept

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
2. **LLM Client**: Interface for Ollama local LLM runner
3. **Review System**: Generates structured reviews using LLMs with consistent prompts
4. **Comparison Engine**: Analyzes multiple reviews to identify patterns and consensus
5. **CLI Interface**: User-friendly command-line tool with rich formatting

### Design Principles

- **Privacy First**: All data stays local - no external API calls
- **Cost Effective**: Zero API costs - completely free to use
- **Open Source**: Built on open-source models and tools
- **Extensible**: Simple to customize review criteria and prompts
- **Hardware Flexible**: Works on consumer hardware

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

While Sibyl now focuses on local models, you can still benefit from using different models sequentially:

1. **Diverse Perspectives**: Different model architectures may focus on different aspects
2. **Consensus Building**: Agreement across models strengthens confidence
3. **Bias Detection**: Inconsistencies may reveal model-specific biases
4. **Performance Evaluation**: Compare quality and speed of different models

### Recommended Local Models

- **Llama 3.2** (Meta): Excellent general capabilities, multiple sizes
- **Mistral** (Mistral AI): Strong reasoning and coding abilities
- **Phi-3** (Microsoft): Efficient small model with good performance
- **Gemma 2** (Google): Well-balanced open model
- **Qwen 2.5** (Alibaba): Strong multilingual and reasoning capabilities
- **DeepSeek Coder** (DeepSeek): Specialized for technical and code-heavy papers

## Limitations

- Requires Ollama to be installed and running locally
- Performance depends on your hardware (CPU/GPU, RAM)
- PDF text extraction may not work perfectly for all paper formats
- Review quality depends on the underlying LLM capabilities
- Long papers may require significant processing time
- Does not review figures, tables, or mathematical equations in detail

## Future Enhancements

- [ ] Support for multiple concurrent model comparisons
- [ ] Batch processing of multiple papers
- [x] Interactive web interface
- [ ] Custom review criteria and prompts
- [ ] Citation analysis integration
- [ ] Support for LaTeX and other document formats
- [ ] GPU acceleration optimization
- [ ] Model quantization support

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [Ollama](https://ollama.ai) - Local LLM runner
- [pypdf](https://github.com/py-pdf/pypdf) - PDF parsing
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- Open-source models: Llama, Mistral, Phi, Gemma, Qwen, DeepSeek, and others

## Contact

For questions, issues, or suggestions, please open an issue on GitHub.