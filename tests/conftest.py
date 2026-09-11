import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.support import STREAM_BODY


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format_string: str, *args: object) -> None:
        return

    def _send(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str | None = None,
        content_length: int | None = None,
    ) -> None:
        self.send_response(status)
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.end_headers()
        self.wfile.write(body)

    def _respond(self) -> None:
        route = urlsplit(self.path)
        query = parse_qs(route.query)
        length = int(self.headers.get("Content-Length", "0"))
        request_body = self.rfile.read(length)
        if route.path == "/error-json":
            self._send(
                400, b'{"message":"bad request"}', content_type="application/json"
            )
            return
        if query.get("failure") == ["http"]:
            self._send(
                500,
                b'{"message":"download failed"}',
                content_type="application/json",
            )
            return
        if query.get("failure") == ["terminal"]:
            self._send(
                500,
                json.dumps({"message": "bad\x1b]0;title\n\u202e"}).encode(),
                content_type="application/json",
            )
            return
        if query.get("failure") == ["truncated"]:
            self._send(200, b"incomplete", content_length=64)
            self.close_connection = True
            return
        if query.get("stream") == ["true"]:
            self._send(
                200,
                STREAM_BODY,
                content_type="application/octet-stream",
                content_length=len(STREAM_BODY),
            )
            return
        payload = json.dumps(
            {
                "method": self.command,
                "path": route.path,
                "query": query,
                "key": self.headers.get("key"),
                "accept": self.headers.get("Accept"),
                "content_type": self.headers.get("Content-Type"),
                "body": json.loads(request_body) if request_body else None,
            }
        ).encode()
        self._send(200, payload, content_type="application/json")

    do_GET = do_POST = do_PUT = do_DELETE = _respond


@pytest.fixture(scope="session")
def api_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
