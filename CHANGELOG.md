# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Modern Web Interface (Next.js)**:
  - Next.js 16 frontend with React 19
  - TypeScript for type safety
  - Tailwind CSS 4 for styling
  - shadcn/ui component library
  - Real-time WebSocket progress updates
  - Drag-and-drop PDF upload
  - Responsive design with dark mode support
  - FastAPI backend with CORS support

- **Web Application**: Fully-fledged web interface for reviewing research papers
  - Modern, responsive UI with drag-and-drop PDF upload
  - Real-time progress tracking via WebSocket
  - Comprehensive display of review results with statistics
  - REST API endpoints for programmatic access
  - Health check and session management
  - Mobile-friendly responsive design
  
- **CLI Command**: New `sibyl web` command to start the web server
  - Configurable host and port options
  - Integrated with existing configuration system
  
- **Security Enhancements**:
  - Multi-layer file validation (extension, content type, magic bytes)
  - XSS prevention with proper HTML escaping
  - Automatic cleanup of temporary files
  - Improved error handling and validation
  
- **Documentation**:
  - Migrated all documentation to use uv as primary build tool
  - Added uv installation instructions to all setup guides
  - Comprehensive web app documentation (WEB_APP.md, WEB_APP_NEXTJS.md)
  - Example usage guide (WEB_APP_EXAMPLE.md)
  - Troubleshooting and performance tips
  - API endpoint documentation
  - Clarified Python 3.9+ requirement (3.12+ recommended)
  - Documented Node.js 18+ requirement for web interface
  
- **Testing**:
  - 9 new tests for web application functionality
  - Security validation tests
  - Integration tests for all major endpoints
  - Total test count: 24 tests (all passing)

### Changed
- **Build System**: Migrated from pip to uv for faster, more reliable dependency management
- Updated README.md to highlight web interface and uv installation
- Enhanced pyproject.toml with web dependencies
- Updated all documentation files to use uv commands
- Updated Future Enhancements section (web interface now complete)

### Security
- Implemented comprehensive PDF file validation
- Added magic byte verification to prevent malicious uploads
- Enhanced error messages for security-related failures
- Passed CodeQL security analysis (0 alerts)

## [0.1.0] - Previous Release

### Added
- Core review system using local LLM models via Ollama
- PDF parsing and text extraction
- Structured review generation with multiple criteria
- Comparative analysis across reviews
- CLI interface with rich formatting
- Configuration management via environment variables
- Support for multiple Ollama models
- Comprehensive test suite
- Documentation and examples

[Unreleased]: https://github.com/cvasilatos/sibyl/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/cvasilatos/sibyl/releases/tag/v0.1.0
