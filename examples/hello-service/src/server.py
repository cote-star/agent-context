"""HTTP handler for hello-service."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Tuple
from urllib.parse import parse_qs, urlparse

from .config import Config


class HelloHandler(BaseHTTPRequestHandler):
    """Handle GET /hello?name=<str>."""

    server_version = "hello-service/0.1"
    config: Config = Config.from_env()

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler contract)
        parsed = urlparse(self.path)
        if parsed.path != "/hello":
            self.send_error(404, "Not Found")
            return
        name = _extract_name(parsed.query)
        body = f"{self.config.greeting}, {name}!\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003, N802
        # Silence the default stderr access log during tests.
        return


def _extract_name(query_string: str) -> str:
    params = parse_qs(query_string)
    values = params.get("name", [])
    return values[0] if values else "world"


def build_server(config: Config) -> Tuple[HTTPServer, Config]:
    """Bind an HTTPServer instance and return it alongside its config."""
    HelloHandler.config = config
    return HTTPServer((config.host, config.port), HelloHandler), config


def serve_forever(config: Config) -> None:
    server, _ = build_server(config)
    server.serve_forever()


if __name__ == "__main__":
    serve_forever(Config.from_env())
