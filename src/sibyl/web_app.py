"""Web application module for programmatic server startup."""

import uvicorn

from sibyl.main import app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    ssl_certfile: str | None = None,
    ssl_keyfile: str | None = None,
) -> None:
    """Run the Sibyl web server programmatically.

    Args:
        host: Host to bind to
        port: Port to bind to
        ssl_certfile: Path to SSL certificate file for HTTPS
        ssl_keyfile: Path to SSL key file for HTTPS

    """
    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        log_config=None,
    )
