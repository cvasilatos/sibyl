"""The ``sibyl`` command: ``sibyl run`` starts the backend and the web app together, ``sibyl serve`` only the backend.

Nothing here is platform-specific beyond how the web app's process tree is stopped, so the same command works on
Linux, macOS and Windows. ``sibyl.main`` is imported inside the commands: it loads the whole pipeline, which
``sibyl --help`` should not wait for.
"""

import contextlib
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
from enum import StrEnum
from pathlib import Path
from types import FrameType
from typing import Annotated

import typer
import uvicorn

app = typer.Typer(help="Sibyl: LLM-powered research paper reviews with local models.", no_args_is_help=True)

DEFAULT_WEB_DIR: Path = Path(__file__).resolve().parents[3] / "web"
"""``web/`` of the source checkout this package runs from (the Next.js app is not part of the Python package)."""

STOP_TIMEOUT_S: float = 10
DEFAULT_PORT = 8000
DEFAULT_WEB_PORT = 3000
PORT_ATTEMPTS = 20
"""How many ports after a busy default ``run`` tries before giving up."""


class LogLevel(StrEnum):
    """Log levels uvicorn accepts."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


PortOption = Annotated[int, typer.Option(help="Port of the backend API.")]
CertOption = Annotated[Path | None, typer.Option(help="SSL certificate file, to serve the backend over HTTPS.")]
KeyOption = Annotated[Path | None, typer.Option(help="SSL key file, to serve the backend over HTTPS.")]
LogLevelOption = Annotated[LogLevel, typer.Option(case_sensitive=False, help="Backend log level.")]


def _say(message: str) -> None:
    typer.secho(f"[sibyl] {message}", fg=typer.colors.MAGENTA, bold=True)


def _fail(message: str) -> typer.Exit:
    typer.secho(f"[sibyl] {message}", fg=typer.colors.RED, bold=True, err=True)
    return typer.Exit(1)


def start_web(web_dir: Path, web_port: int, api_url: str) -> subprocess.Popen[bytes]:
    """Start the Next.js dev server in ``web_dir``, installing its dependencies first if they are missing.

    Next is started with ``node`` directly instead of ``npm run dev``: one process layer fewer to stop, and no
    ``npm.cmd`` shim on Windows. The server gets its own process group so that stopping it takes its children along.
    """
    if not (web_dir / "package.json").is_file():
        raise _fail(f"No web app in {web_dir}. Run sibyl from a source checkout, or pass --web-dir (SIBYL_WEB_DIR).")
    node = shutil.which("node")
    if node is None:
        raise _fail("Node.js 20+ is required for the web app: https://nodejs.org/en/download")

    next_bin = web_dir / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_bin.is_file():
        npm = shutil.which("npm")
        if npm is None:
            raise _fail("npm is required to install the web app's dependencies; it ships with Node.js.")
        _say("Installing web dependencies...")
        if subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=web_dir, check=False).returncode != 0:  # noqa: S603
            raise _fail("Installing the web dependencies failed (npm ci).")

    # A NEXT_PUBLIC_API_URL already in the environment wins, e.g. when the browser reaches the backend under another name.
    env = {"NEXT_PUBLIC_API_URL": api_url, **os.environ}
    command = [node, str(next_bin), "dev", "-p", str(web_port)]
    if sys.platform == "win32":
        return subprocess.Popen(command, cwd=web_dir, env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)  # noqa: S603
    return subprocess.Popen(command, cwd=web_dir, env=env, start_new_session=True)  # noqa: S603


def stop_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Stop ``process`` and its children (Next's dev server runs in a child of the process we start)."""
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)  # noqa: S603, S607
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(STOP_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        # Children that ignored SIGTERM (or had not exited yet when the parent did) must not outlive it.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def port_is_free(host: str, port: int) -> bool:
    """Return whether a server could listen on ``host``:``port`` now (a port another server listens on is not free)."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        if sys.platform != "win32":  # as uvicorn does; ports left in TIME_WAIT are usable. On Windows it would steal ports.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(host: str, requested: int | None, default: int, what: str) -> int:
    """Return ``requested`` if given (failing when busy), else ``default`` or the first free port after it."""
    if requested is not None:
        if not port_is_free(host, requested):
            raise _fail(f"Port {requested} for the {what} is in use. Pick another, or leave the option out to use a free one.")
        return requested
    for port in range(default, default + PORT_ATTEMPTS):
        if port_is_free(host, port):
            if port != default:
                _say(f"Port {default} is in use; the {what} uses port {port}.")
            return port
    raise _fail(f"Ports {default}-{default + PORT_ATTEMPTS - 1} for the {what} are all in use. Pass a free one.")


def _interrupt(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


@app.command()
def run(  # noqa: PLR0913
    host: Annotated[str, typer.Option(help="Interface the backend binds to. Use 0.0.0.0 to reach it from other machines.")] = "127.0.0.1",
    port: Annotated[int | None, typer.Option(help="Port of the backend API. Default: 8000, or the next free port.")] = None,
    web_port: Annotated[int | None, typer.Option(help="Port of the web app. Default: 3000, or the next free port.")] = None,
    web_dir: Annotated[Path, typer.Option(envvar="SIBYL_WEB_DIR", help="Directory of the Next.js app.")] = DEFAULT_WEB_DIR,
    ssl_certfile: CertOption = None,
    ssl_keyfile: KeyOption = None,
    log_level: LogLevelOption = LogLevel.INFO,
) -> None:
    """Run the whole application: the backend API and the web app, until Ctrl+C."""
    scheme = "https" if ssl_certfile else "http"
    port = choose_port(host, port, DEFAULT_PORT, "backend")
    # Next listens on every interface, so the web port must be free on all of them.
    web_port = choose_port("0.0.0.0", web_port, DEFAULT_WEB_PORT, "web app")  # noqa: S104
    if web_port == port:
        web_port = choose_port("0.0.0.0", None, port + 1, "web app")  # noqa: S104
    web = start_web(web_dir, web_port, api_url=f"{scheme}://localhost:{port}")
    try:
        from sibyl.main import app as api  # noqa: PLC0415

        config = uvicorn.Config(api, host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile, log_config=None, log_level=log_level.lower())
        server = uvicorn.Server(config)

        def stop_backend_when_web_exits() -> None:
            web.wait()
            server.should_exit = True

        threading.Thread(target=stop_backend_when_web_exits, daemon=True).start()
        # uvicorn re-raises SIGTERM once it has shut down; turn it into an exception so the web app is stopped as well.
        previous_sigterm = signal.signal(signal.SIGTERM, _interrupt)
        _say(f"Backend on {scheme}://localhost:{port}, web app on http://localhost:{web_port} (Ctrl+C to stop).")
        try:
            server.run()
        except KeyboardInterrupt:
            pass
        else:
            if web.poll() is not None:
                raise _fail(f"The web app exited (code {web.returncode}); stopped the backend.")
        finally:
            signal.signal(signal.SIGTERM, previous_sigterm)
    finally:
        stop_process_tree(web)


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Interface the backend binds to.")] = "0.0.0.0",  # noqa: S104
    port: PortOption = DEFAULT_PORT,
    ssl_certfile: CertOption = None,
    ssl_keyfile: KeyOption = None,
    log_level: LogLevelOption = LogLevel.INFO,
) -> None:
    """Run only the backend API (what the Docker image does)."""
    from sibyl.main import app as api  # noqa: PLC0415

    uvicorn.run(api, host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile, log_config=None, log_level=log_level.lower())
