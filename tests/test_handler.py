from __future__ import annotations

import http.client
import os
import threading
from http.server import HTTPServer

from total_control.handler import Handler


def test_handler_serves_static_file_when_cwd_is_missing(monkeypatch):
    def missing_cwd() -> str:
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(os, "getcwd", missing_cwd)
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)

    try:
        connection.request("HEAD", "/")
        response = connection.getresponse()
        response.read()
    finally:
        connection.close()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == 200
    assert not thread.is_alive()
