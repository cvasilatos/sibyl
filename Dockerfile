FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install the package with web dependencies
RUN pip install --no-cache-dir -e ".[web]"

# Expose the API port
EXPOSE 8000

# Run the FastAPI web server
CMD ["sibyl", "web", "--host", "0.0.0.0", "--port", "8000"]
