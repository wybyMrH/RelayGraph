from __future__ import annotations

from typing import Any


def build_remote_runtime_log_status_error_payload(
    server: Any,
    error: Any,
    *,
    skipped: bool = False,
) -> dict[str, Any]:
    payload = {
        "server_id": server.id,
        "server_name": server.name,
        "log_dir": "$HOME/.total_control/logs",
        "error": str(error or "").strip(),
    }
    if skipped:
        payload["skipped"] = True
    return payload
