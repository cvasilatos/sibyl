import logging
from typing import cast

import click
import uvicorn
from decimalog.logger import CustomLogger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sibyl.routers import web_reviews, web_upload, web_ws

CustomLogger.setup_logging("logs", "app", level="DEBUG")

app = FastAPI(
    title="Sibyl Research Paper Review System",
    description="AI-powered research paper review using local LLMs",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(web_upload.router, prefix="/api", tags=["Upload"])
app.include_router(web_ws.router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "online", "system": "Sibyl"}


@click.command()
@click.option("--host", default="0.0.0.0", type=str)
@click.option("--port", default=8000, type=int)
@click.option("--ssl-certfile", default=None, type=str, help="Path to SSL certificate file for HTTPS")
@click.option("--ssl-keyfile", default=None, type=str, help="Path to SSL key file for HTTPS")
@click.option("--log-level", required=True, type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=True))
def run_server(host: str, port: int, ssl_certfile: str | None, ssl_keyfile: str | None, log_level: str) -> None:
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to bind to
        ssl_certfile: Path to SSL certificate file
        ssl_keyfile: Path to SSL key file
        log_level: Logging level (TRACE, DEBUG, INFO, WARNING, ERROR)

    """
    logger: CustomLogger = cast("CustomLogger", logging.getLogger("alal"))
    logger.info(f"Starting Sibyl server on {host}:{port} with log level {log_level}")

    uvicorn.run(app, host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile, log_config=None, log_level=log_level.lower())


if __name__ == "__main__":
    run_server()
