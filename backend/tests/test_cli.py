# ruff: noqa: S603  (the tests start fixed Python one-liners)

import subprocess
import sys
import time

import pytest
from typer.testing import CliRunner

from sibyl import cli

runner = CliRunner()


def test_help_lists_commands():
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "serve" in result.output


def test_run_without_web_app_fails(tmp_path):
    result = runner.invoke(cli.app, ["run", "--web-dir", str(tmp_path)])
    assert result.exit_code == 1


def test_start_web_requires_node(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    with pytest.raises(cli.typer.Exit):
        cli.start_web(tmp_path, 3000, "http://localhost:8000")


def test_stop_process_tree_stops_children():
    # A parent that starts a long-running child, as `next dev` does.
    code = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
    if sys.platform == "win32":
        process = subprocess.Popen([sys.executable, "-c", code], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        process = subprocess.Popen([sys.executable, "-c", code], start_new_session=True)
    time.sleep(0.5)
    cli.stop_process_tree(process)
    assert process.poll() is not None
    if sys.platform != "win32":
        # The killed child is reaped by init asynchronously, so give the group a moment to disappear.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                cli.os.killpg(process.pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        with pytest.raises(ProcessLookupError):
            cli.os.killpg(process.pid, 0)  # the whole group is gone


class FakeServer:
    """Stands in for uvicorn.Server: runs until asked to exit, like the real one."""

    def __init__(self, config):
        self.config = config
        self.should_exit = False

    def run(self):
        deadline = time.monotonic() + 10
        while not self.should_exit and time.monotonic() < deadline:
            time.sleep(0.05)


def test_run_stops_backend_when_web_app_exits(tmp_path, monkeypatch):
    web = subprocess.Popen([sys.executable, "-c", "raise SystemExit(3)"])
    monkeypatch.setattr(cli, "start_web", lambda *_args, **_kwargs: web)
    monkeypatch.setattr(cli.uvicorn, "Server", FakeServer)
    result = runner.invoke(cli.app, ["run", "--web-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "code 3" in result.output


def test_run_passes_backend_url_to_web_app(tmp_path, monkeypatch):
    seen = {}

    def fake_start_web(web_dir, web_port, api_url):
        seen.update(web_dir=web_dir, web_port=web_port, api_url=api_url)
        return subprocess.Popen([sys.executable, "-c", "pass"])

    monkeypatch.setattr(cli, "start_web", fake_start_web)
    monkeypatch.setattr(cli.uvicorn, "Server", FakeServer)
    runner.invoke(cli.app, ["run", "--web-dir", str(tmp_path), "--port", "9001", "--web-port", "4001"])
    assert seen == {"web_dir": tmp_path, "web_port": 4001, "api_url": "http://localhost:9001"}


def test_run_moves_off_busy_default_ports(tmp_path, monkeypatch):
    seen = {}

    def fake_start_web(web_dir, web_port, api_url):
        seen.update(web_port=web_port, api_url=api_url)
        return subprocess.Popen([sys.executable, "-c", "pass"])

    busy = {("127.0.0.1", 8000), ("0.0.0.0", 3000), ("0.0.0.0", 3001)}  # noqa: S104
    monkeypatch.setattr(cli, "port_is_free", lambda host, port: (host, port) not in busy)
    monkeypatch.setattr(cli, "start_web", fake_start_web)
    monkeypatch.setattr(cli.uvicorn, "Server", FakeServer)
    result = runner.invoke(cli.app, ["run", "--web-dir", str(tmp_path)])
    assert seen == {"web_port": 3002, "api_url": "http://localhost:8001"}
    assert "Port 8000 is in use; the backend uses port 8001" in result.output


def test_run_refuses_a_busy_port_the_user_chose(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "port_is_free", lambda _host, port: port != 9001)
    monkeypatch.setattr(cli, "start_web", lambda *_args: pytest.fail("must not start"))
    result = runner.invoke(cli.app, ["run", "--web-dir", str(tmp_path), "--port", "9001"])
    assert result.exit_code == 1
    assert "Port 9001 for the backend is in use" in result.output


def test_port_is_free_sees_a_listening_server():
    import socket

    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        assert not cli.port_is_free("127.0.0.1", port)
    assert cli.port_is_free("127.0.0.1", port)
