from __future__ import annotations

import argparse
import os
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from .constants import DEFAULT_CONFIG, ROOT, WEB_DIR
from .http_api import handle_delete, handle_get, handle_post, handle_put
from .state import TotalControlState
from .utils import now_iso, safe_int


STATE: TotalControlState | None = None


class Handler(SimpleHTTPRequestHandler):
    server_version = "TotalControl/0.1"

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        clean = unquote(parsed.path)
        if clean == "/":
            return str(WEB_DIR / "index.html")
        return str(WEB_DIR / clean.lstrip("/"))

    def _suppress_access_log(self, args: tuple[Any, ...]) -> bool:
        if os.environ.get("TOTAL_CONTROL_VERBOSE_ACCESS_LOG", "").strip().lower() in {"1", "true", "yes", "on"}:
            return False
        request_line = str(args[0] or "") if args else ""
        status_code = safe_int(args[1], 0) if len(args) > 1 else 0
        if status_code >= 400:
            return False
        parts = request_line.split()
        if len(parts) < 2 or parts[0].upper() not in {"GET", "HEAD"}:
            return False
        path = urlparse(parts[1]).path
        if path in {"/", "/api/status", "/api/execution-overview", "/favicon.ico"}:
            return True
        if path.endswith("/events"):
            return True
        return path.endswith((".css", ".js", ".map", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp", ".woff", ".woff2"))

    def log_message(self, format: str, *args: Any) -> None:
        if self._suppress_access_log(args):
            return
        print(f"[{now_iso()}] {self.address_string()} {format % args}", flush=True)

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def send_file(self, path: Path, *, content_type: str, disposition: str, filename: str) -> None:
        target = path.expanduser().resolve()
        stat = target.stat()
        encoded_name = quote(filename or target.name)
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(stat.st_size))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Disposition", f"{disposition}; filename*=UTF-8''{encoded_name}")
            self.end_headers()
            with target.open("rb") as handle:
                while True:
                    chunk = handle.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            return

    def read_body(self) -> dict[str, Any]:
        size = safe_int(self.headers.get("Content-Length"), 0)
        raw = self.rfile.read(size).decode("utf-8") if size else "{}"
        return json.loads(raw or "{}")

    def do_GET(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            if handle_get(self, STATE, parsed):
                return
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            handle_post(self, STATE, parsed)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self.send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            handle_put(self, STATE, parsed)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self.send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)

    def do_DELETE(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            handle_delete(self, STATE, parsed)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

def run(host: str, port: int, config_path: Path) -> None:
    global STATE
    os.chdir(ROOT)
    STATE = TotalControlState(config_path)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[total-control] serving http://{host}:{port}", flush=True)
    print(f"[total-control] config {config_path}", flush=True)
    print("[total-control] press Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if STATE:
            STATE.stop_event.set()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="RelayGraph GPU monitor and command launcher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    run(args.host, args.port, args.config)


if __name__ == "__main__":
    main()
