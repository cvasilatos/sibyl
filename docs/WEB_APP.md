# Sibyl Web Application (FastAPI Backend)

## Overview

The Sibyl Web Application provides a FastAPI backend for the web interface. This document covers the backend server. For the Next.js frontend, see [WEB_APP_NEXTJS.md](WEB_APP_NEXTJS.md).

The backend is built with FastAPI and provides:
- REST API endpoints for file uploads, reviews, and health checks
- WebSocket support for real-time progress updates
- CORS enabled for Next.js frontend running on port 3000

## Features

- **📤 Drag & Drop Upload**: Easy PDF file upload with drag-and-drop support
- **⚡ Real-time Updates**: WebSocket-based progress tracking during review
- **🎨 Modern UI**: Clean, responsive design that works on desktop and mobile
- **📊 Comparative Analysis**: View statistics and consensus across reviews
- **🔒 Privacy-First**: All processing happens locally - no data leaves your machine
- **💰 Zero Cost**: Completely free to use with local LLM models

## Installation

### Prerequisites

- Python 3.12 or higher (3.12+ recommended)
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package installer
- [Ollama](https://ollama.ai) installed and running
- A local LLM model (e.g., `llama3.2`)
- Node.js 18+ and npm (for Next.js frontend, optional)

### Install Sibyl with Web Support

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Sibyl with web dependencies
uv pip install -e ".[web]"
```

## Quick Start

You need to run **both** the backend and the Next.js frontend:

1. **Configure Sibyl**:
   ```bash
   # Create .env file
   cp .env.example .env

   # Edit .env and set your model
   # OLLAMA_MODEL=llama3.2
   # OLLAMA_BASE_URL=http://localhost:11434
   ```

2. **Start the Backend** (Terminal 1):
   ```bash
   sibyl web
   ```

   This starts the FastAPI backend on `http://localhost:8000`

3. **Start the Frontend** (Terminal 2):
   ```bash
   cd web
   npm install  # First time only
   npm run dev
   ```

   This starts the Next.js frontend on `http://localhost:3000`

4. **Open in Browser**:
   ```
   http://localhost:3000
   ```

5. **Upload and Review**:
   - Drag and drop a PDF research paper
   - Click "Start Review"
   - Watch real-time progress
   - View comprehensive results

## Usage

### Command Line Options

Start the web server with custom host and port:

```bash
# Default (0.0.0.0:8000)
sibyl web

# Custom host and port
sibyl web --host 127.0.0.1 --port 8080

# Enable SSL with self-signed certificate
sibyl web --ssl

# Help
sibyl web --help
```

### API Endpoints

The backend provides the following REST API endpoints for the Next.js frontend:

#### `GET /api/health`
Health check endpoint to verify service status.

**Response**:
```json
{
  "status": "healthy",
  "providers": ["ollama"],
  "ollama_base_url": "http://localhost:11434"
}
```

#### `POST /api/upload`
Upload a PDF file for review.

**Request**:
- Form data with `file` field containing PDF

**Response**:
```json
{
  "session_id": "uuid-string",
  "filename": "paper.pdf"
}
```

#### `GET /api/session/{session_id}`
Get the status of a review session.

**Response**:
```json
{
  "session_id": "uuid-string",
  "status": "processing",
  "progress": 50,
  "message": "Reviewing with ollama...",
  "paper_title": "Research Paper Title"
}
```

#### `WebSocket /ws/{session_id}`
WebSocket endpoint for real-time review progress updates.

**Messages**:
```json
// Progress update
{
  "status": "progress",
  "progress": 50,
  "message": "Generating review..."
}

// Completion
{
  "status": "completed",
  "progress": 100,
  "message": "Review complete!",
  "results": {
    "paper_title": "...",
    "reviews": [...],
    "comparison": {...}
  }
}

// Error
{
  "status": "error",
  "message": "Error description"
}
```

## Architecture

### Backend (FastAPI)

- **FastAPI**: Modern, fast web framework with automatic API documentation
- **Uvicorn**: Lightning-fast ASGI server
- **WebSockets**: Real-time bidirectional communication
- **Pydantic**: Data validation and settings management

### Frontend (Next.js)

- **Next.js 15**: React framework with App Router
- **React 19**: UI library for component-based development
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: High-quality component library
- **WebSocket Client**: Real-time progress updates

### Flow

1. User uploads PDF via web interface
2. File is saved temporarily with unique session ID
3. WebSocket connection established for progress updates
4. PDF text extracted
5. LLM generates review (progress updates sent via WebSocket)
6. Results displayed in web interface
7. Temporary file cleaned up

## Development

### Running in Development Mode

```bash
# Install development dependencies
uv pip install -e ".[dev,web]"

# Run with auto-reload
uvicorn sibyl.web_app:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run web app tests
pytest tests/test_web_app.py -v

# Run all tests
pytest -v
```

### Project Structure

```
src/sibyl/
├── web_app.py           # FastAPI backend application
├── cli.py              # CLI with web command
└── ...                 # Core modules

web/                     # Next.js frontend (separate)
├── src/
│   ├── app/            # Next.js app pages
│   ├── components/     # React components (including shadcn/ui)
│   └── lib/            # Utility functions
├── public/             # Static assets
└── package.json
```

## Security Considerations

- **File Validation**: Only PDF files are accepted
- **Session Management**: Unique session IDs prevent conflicts
- **Temporary Files**: Automatically cleaned up after processing
- **XSS Prevention**: All user content is escaped in the UI
- **Local Processing**: No data sent to external services

## Troubleshooting

### Server won't start

**Issue**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Install web dependencies
```bash
uv pip install -e ".[web]"
```

### Can't connect to Ollama

**Issue**: Health check shows "unhealthy"

**Solution**:
1. Ensure Ollama is running: `ollama list`
2. Check `.env` configuration
3. Verify `OLLAMA_BASE_URL` is correct

### WebSocket connection fails

**Issue**: Connection error in browser console

**Solution**:
1. Check firewall settings
2. Ensure WebSocket traffic is allowed
3. Try using `--host 127.0.0.1` instead of `0.0.0.0`

### Review takes too long

**Issue**: Process seems stuck

**Solution**:
1. Check system resources (CPU/RAM)
2. Try a smaller model (e.g., `llama3.2:1b`)
3. Limit pages with `--max-pages` option
4. Check Ollama logs: `journalctl -u ollama -f`

## Performance Tips

1. **Use Appropriate Models**:
   - 8GB RAM: `llama3.2:1b`, `phi3:mini`
   - 16GB RAM: `llama3.2:3b`, `mistral:7b`
   - 32GB+ RAM: Larger models

2. **Limit Page Count**:
   - For testing, use `--max-pages 5`
   - For full reviews, use all pages

3. **GPU Acceleration**:
   - Ollama automatically uses GPU if available
   - Check with: `nvidia-smi` (NVIDIA) or `rocm-smi` (AMD)

## Browser Compatibility

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Opera 76+

## Accessibility

- Keyboard navigation support
- ARIA labels for screen readers
- High contrast support
- Responsive design for all screen sizes

## Future Enhancements

- [ ] Multiple model comparison in single review
- [ ] Batch processing of multiple papers
- [ ] Download results as PDF report
- [ ] User authentication and history
- [ ] Custom review criteria templates
- [ ] Dark mode support
- [ ] Review comparison visualization
- [ ] Export to various formats (JSON, Markdown, LaTeX)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../LICENSE) for details.
