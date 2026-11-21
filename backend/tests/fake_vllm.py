"""Stand-in for ``vllm serve`` used by tests: answers /health and /v1/chat/completions.

Usage mirrors vLLM: ``python fake_vllm.py serve <model> --port <port> ...``.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

args = sys.argv[1:]
model = args[1]
port = int(args[args.index("--port") + 1])
if model == "crash/model":
    sys.exit("simulated load failure")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        content = json.dumps({"served_model": model, "requested_model": body["model"], "has_schema": "response_format" in body})
        payload = json.dumps({"choices": [{"message": {"content": content}}], "usage": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args: object) -> None:
        pass


HTTPServer(("127.0.0.1", port), Handler).serve_forever()
