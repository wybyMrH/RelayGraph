from __future__ import annotations

from typing import Any

from ...utils import now_iso, remote_runtime_log_display_path, runtime_log_display_path, safe_int


def build_log_tail_snapshot_payload(
    job: dict[str, Any],
    payload: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    tail = str(payload.get("tail") or "").strip("\n")
    if not tail:
        return {}
    display_log_path = str(payload.get("display_log_path") or "").strip()
    if not display_log_path:
        display_log_path = runtime_log_display_path(payload.get("log_path") or job.get("log_path"))
    return {
        "schema": "relaygraph.job.log_tail_snapshot.v1",
        "captured_at": now_iso(),
        "source": source,
        "line_count": len(tail.splitlines()),
        "file_size": safe_int(payload.get("file_size"), 0),
        "read_bytes": safe_int(payload.get("read_bytes"), safe_int(payload.get("byte_count"), 0)),
        "tail_bytes": safe_int(payload.get("tail_bytes"), len(tail.encode("utf-8", errors="replace"))),
        "skipped_bytes": safe_int(payload.get("skipped_bytes"), 0),
        "truncated": bool(payload.get("truncated")),
        "truncation_reasons": [
            str(item or "").strip()
            for item in payload.get("truncation_reasons", [])
            if str(item or "").strip()
        ],
        "display_log_path": display_log_path,
        "remote_log_path": remote_runtime_log_display_path(
            payload.get("remote_log_path") or job.get("remote_log_path")
        ),
        "tail": tail,
    }


def build_remote_log_tail_payload(
    job: dict[str, Any],
    chunk: dict[str, Any],
    *,
    max_lines: int,
    max_bytes: int,
    tail_chars: int,
) -> dict[str, Any]:
    text = str(chunk.get("log") or "")
    if not text:
        return {}
    line_limited = "\n".join(text.splitlines()[-max(1, int(max_lines or 1)):])
    reasons = []
    if bool(chunk.get("truncated")) or safe_int(chunk.get("skipped_bytes"), 0) > 0:
        reasons.append("byte_window")
    if len(text.splitlines()) > max(1, int(max_lines or 1)):
        reasons.append("line_limit")
    if tail_chars > 0 and len(line_limited) > tail_chars:
        line_limited = line_limited[-tail_chars:]
        reasons.append("tail_char_limit")
    return {
        "tail": line_limited,
        "tail_source": "remote",
        "file_size": safe_int(chunk.get("file_size"), safe_int(chunk.get("next_offset"), 0)),
        "read_bytes": safe_int(chunk.get("byte_count"), len(text.encode("utf-8", errors="replace"))),
        "tail_bytes": len(line_limited.encode("utf-8", errors="replace")),
        "skipped_bytes": safe_int(chunk.get("skipped_bytes"), 0),
        "truncated": bool(chunk.get("truncated")) or bool(reasons),
        "truncation_reasons": list(dict.fromkeys(reasons)),
        "remote_log_path": remote_runtime_log_display_path(job.get("remote_log_path")),
    }
