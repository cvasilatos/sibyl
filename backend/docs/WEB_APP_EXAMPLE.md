# Sibyl Web App Example Usage

This guide demonstrates how to use the Sibyl web application for reviewing research papers.

## Prerequisites

Before starting, ensure you have:

1. **Ollama installed and running**:
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   ```

2. **A model pulled in Ollama**:
   ```bash
   # Pull llama3.2 (recommended)
   ollama pull llama3.2
   
   # Or another model
   ollama pull mistral
   ```

3. **Sibyl installed with web support**:
   ```bash
   # Install uv if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install Sibyl with web dependencies
   uv pip install -e ".[web]"
   ```

4. **Configuration file**:
   ```bash
   # Create .env from example
   cp .env.example .env
   
   # Edit .env to set your model
   echo "OLLAMA_MODEL=llama3.2" > .env
   ```

## Starting the Web Server

### Basic Usage

```bash
# Start server on default port (8000)
sibyl web
```

Output:
```
Starting Sibyl Web Interface

Server: http://0.0.0.0:8000
Press Ctrl+C to stop

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Custom Port

```bash
# Start on port 3000
sibyl web --port 3000
```

### Localhost Only

```bash
# Bind to localhost only (more secure for local use)
sibyl web --host 127.0.0.1 --port 8080
```

## Using the Web Interface

1. **Start the Backend** (Terminal 1):
   ```bash
   sibyl web
   ```

2. **Start the Frontend** (Terminal 2):
   ```bash
   cd web
   npm install  # First time only
   npm run dev
   ```

3. **Open your browser** to `http://localhost:3000`

4. **Upload a PDF**:
   - Click the upload area or drag and drop a PDF file
   - Only `.pdf` files are accepted
   - File is uploaded immediately upon selection

5. **Start Review**:
   - Click the "Start Review" button
   - Progress bar shows real-time status:
     - "Uploading file..." (10%)
     - "Extracting text from PDF..." (30%)
     - "Generating review..." (40-90%)
     - "Comparing reviews..." (95%)
     - "Review complete!" (100%)

6. **View Results**:
   - Overall statistics (mean score, range, consensus)
   - Individual reviews from each model
   - Detailed feedback for each criterion:
     - Novelty
     - Methodology
     - Results
     - Clarity
     - Impact
     - Strengths
     - Limitations
     - Detailed Feedback

## API Usage

You can also use the API programmatically:

### Upload a Paper

```python
import requests

# Upload PDF
with open("paper.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/upload",
        files={"file": f}
    )

session_id = response.json()["session_id"]
print(f"Session ID: {session_id}")
```

### Check Health

```python
import requests

response = requests.get("http://localhost:8000/api/health")
health = response.json()

print(f"Status: {health['status']}")
print(f"Providers: {health['providers']}")
print(f"Ollama URL: {health['ollama_base_url']}")
```

### WebSocket for Real-time Updates

```python
import asyncio
import websockets
import json

async def review_paper(session_id):
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["status"] == "progress":
                print(f"{data['progress']}%: {data['message']}")
            
            elif data["status"] == "completed":
                print("Review complete!")
                results = data["results"]
                print(f"Paper: {results['paper_title']}")
                print(f"Reviews: {len(results['reviews'])}")
                break
            
            elif data["status"] == "error":
                print(f"Error: {data['message']}")
                break

# Usage
asyncio.run(review_paper("your-session-id"))
```

## Example Session

Here's a complete example session:

```bash
# 1. Start the server
$ sibyl web
Starting Sibyl Web Interface

Server: http://0.0.0.0:8000
Press Ctrl+C to stop

# 2. In another terminal, upload a paper
$ curl -X POST -F "file=@research_paper.pdf" http://localhost:8000/api/upload
{"session_id":"550e8400-e29b-41d4-a716-446655440000","filename":"research_paper.pdf"}

# 3. Check health
$ curl http://localhost:8000/api/health
{"status":"healthy","providers":["ollama"],"ollama_base_url":"http://localhost:11434"}

# 4. Open browser to http://localhost:8000 and interact with the UI
```

## Troubleshooting

### Server won't start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
uv pip install -e ".[web]"
```

### Can't access from other machines

**Issue**: Server only accessible from localhost

**Solution**: Use `--host 0.0.0.0`
```bash
sibyl web --host 0.0.0.0 --port 8000
```

### Ollama connection error

**Error**: "unhealthy" status or connection refused

**Solutions**:
1. Check if Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Verify `.env` configuration:
   ```bash
   cat .env
   ```

3. Check Ollama logs:
   ```bash
   # Linux
   journalctl -u ollama -f
   
   # macOS
   tail -f ~/Library/Logs/Ollama/server.log
   ```

### Review takes too long

**Issue**: Process seems stuck at "Generating review..."

**Solutions**:
1. Check system resources (CPU/RAM usage)
2. Try a smaller model:
   ```bash
   echo "OLLAMA_MODEL=llama3.2:1b" > .env
   ```
3. Check Ollama is responding:
   ```bash
   ollama list
   ```

### WebSocket connection fails

**Issue**: "Connection error" in browser

**Solutions**:
1. Check firewall settings
2. Ensure WebSocket traffic is allowed
3. Try different browser
4. Check browser console for errors (F12)

## Performance Tips

1. **Model Selection**:
   - Fast: `llama3.2:1b`, `phi3:mini`
   - Balanced: `llama3.2:3b`, `mistral:7b`
   - Quality: Larger models if you have RAM

2. **Hardware**:
   - CPU-only: 2-5 minutes per review
   - With GPU: 30-120 seconds per review

3. **Optimization**:
   - Close other applications
   - Ensure sufficient RAM
   - Use SSD for better I/O

## Security Considerations

1. **Local Network Only**:
   - For production, use `--host 127.0.0.1`
   - Add authentication if exposing to network

2. **File Validation**:
   - Only PDF files are accepted
   - Files are temporary and auto-deleted

3. **Privacy**:
   - All processing is local
   - No data sent to external services
   - Reviews are not stored permanently

## Next Steps

- Try the [CLI interface](../README.md#usage) for scripted workflows
- Explore [model comparison](MODEL_COMPARISON.md) strategies
- Read the [API documentation](WEB_APP.md) for advanced usage
- Contribute improvements on [GitHub](https://github.com/cvasilatos/sibyl)

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review the troubleshooting section above
