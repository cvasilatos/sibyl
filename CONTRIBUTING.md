# Contributing to Sibyl

Thank you for your interest in contributing to Sibyl! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/sibyl.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/

# Check linting
ruff check src/

# Type checking
mypy src/
```

## Code Style

- Follow PEP 8 guidelines
- Use Black for formatting (line length: 100)
- Add type hints to new functions
- Write docstrings for public APIs

## Testing

- Write tests for new features
- Ensure all tests pass before submitting
- Aim for good test coverage
- Use pytest for testing

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the USAGE.md if you change user-facing features
3. Ensure all tests pass
4. Your PR will be reviewed by maintainers
5. Address any requested changes
6. Once approved, your PR will be merged

## Adding New LLM Providers

To add a new LLM provider:

1. Create a new client class in `llm_client.py` inheriting from `LLMClient`
2. Implement the `generate()` and `get_name()` methods
3. Add the provider to the factory function
4. Update configuration in `config.py`
5. Add tests
6. Update documentation

## Areas for Contribution

- **New LLM Providers**: Add support for more models
- **Improved Parsing**: Better PDF text extraction
- **Additional Criteria**: New review dimensions
- **Visualizations**: Charts and graphs for comparisons
- **Web Interface**: Create a web UI
- **Documentation**: Improve docs and examples
- **Tests**: Increase test coverage
- **Bug Fixes**: Fix reported issues

## Questions?

Feel free to open an issue for:
- Bug reports
- Feature requests
- Questions about usage
- Suggestions for improvement

Thank you for contributing!
