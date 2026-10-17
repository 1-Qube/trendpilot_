"""Serve the local TrendPilot UI and research API."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from trendpilot.envfile import load_env

load_env()

from trendpilot.agent import run

HOST = "127.0.0.1"
PORT = int(os.environ.get("TRENDPILOT_PORT", "8788"))
UI = Path(__file__).resolve().parent / "ui"
FILES = {
    "/": UI / "index.html",
    "/index.html": UI / "index.html",
    "/live.js": UI / "live.js",
    "/favicon.svg": UI / "favicon.svg",
}
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}


def serve() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"TrendPilot UI on http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"ok": True, "service": "trendpilot"})
            return
        file_path = FILES.get(path)
        if file_path and file_path.exists():
            raw = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TYPES.get(file_path.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/research":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "body must be JSON"})
            return
        if not isinstance(body, dict):
            self._json(400, {"error": "body must be a JSON object"})
            return
        company = body.get("company")
        if not isinstance(company, dict):
            self._json(400, {"error": "company object is required"})
            return
        question = body.get("question") or None
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            for event in run(company, question=question):
                self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
                self.wfile.flush()
        except Exception as exc:
            self.wfile.write(
                (json.dumps({"kind": "error", "title": "Agent failed", "detail": str(exc)}) + "\n").encode("utf-8")
            )

    def log_message(self, fmt: str, *args) -> None:
        print(f"[ui] {self.address_string()} {fmt % args}", flush=True)

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
