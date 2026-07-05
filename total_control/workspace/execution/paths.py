"""Execution — paths helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403

def workspace_config_values(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").replace(",", "\n").splitlines()
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items

def compact_workspace_command(value: Any, *, limit: int = 180) -> str:
    text = " ".join(str(value or "").strip().split())
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"

def workspace_path_probe(path_value: str, *, root: str = "", label: str = "path", source: str = "config") -> dict[str, Any]:
    raw = str(path_value or "").strip()
    item: dict[str, Any] = {
        "label": label,
        "path": raw,
        "source": source,
        "status": "planned",
    }
    if not raw:
        item["status"] = "missing"
        return item
    path = Path(raw).expanduser()
    if root and not path.is_absolute():
        path = Path(root).expanduser() / path
    item["path"] = str(path)
    try:
        item["resolved_path"] = str(path.resolve())
        item["exists"] = path.exists()
        item["status"] = "found" if item["exists"] else "expected"
        if item["exists"]:
            item["kind"] = "dir" if path.is_dir() else "file"
    except OSError:
        item["exists"] = False
        item["status"] = "unreadable"
    return item

def _workspace_log_tail_reasons(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    reasons: list[str] = []
    seen: set[str] = set()
    for item in value:
        reason = str(item or "").strip()
        if not reason or reason in seen:
            continue
        seen.add(reason)
        reasons.append(reason)
    return reasons


def _workspace_limited_tail_payload(
    text: str,
    *,
    max_lines: int,
    tail_chars: int | None = None,
    truncated: bool = False,
    truncation_reasons: list[str] | None = None,
) -> dict[str, Any]:
    line_limit = max(1, int(max_lines or 1))
    reasons = list(truncation_reasons or [])
    lines = str(text or "").splitlines()
    if len(lines) > line_limit:
        reasons.append("line_limit")
    tail = "\n".join(lines[-line_limit:])
    char_limit = int(tail_chars or 0)
    if char_limit > 0 and len(tail) > char_limit:
        tail = tail[-char_limit:]
        reasons.append("tail_char_limit")
    clean_reasons: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        value = str(reason or "").strip()
        if value and value not in seen:
            seen.add(value)
            clean_reasons.append(value)
    tail_bytes = len(tail.encode("utf-8", errors="replace"))
    return {
        "tail": tail,
        "line_count": len(tail.splitlines()),
        "tail_bytes": tail_bytes,
        "truncated": bool(truncated or clean_reasons),
        "truncation_reasons": clean_reasons,
    }


def _workspace_job_log_tail_snapshot_payload(
    job: dict[str, Any],
    *,
    max_lines: int,
    max_bytes: int,
    tail_chars: int | None,
) -> dict[str, Any]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    snapshot = metadata.get("log_tail_snapshot") if isinstance(metadata.get("log_tail_snapshot"), dict) else {}
    text = str(snapshot.get("tail") or "").strip("\n")
    if not text:
        return {
            "tail": "",
            "tail_source": "",
            "truncated": False,
            "truncation_reasons": [],
        }
    reasons = _workspace_log_tail_reasons(snapshot.get("truncation_reasons"))
    truncated = bool(snapshot.get("truncated"))
    limit = max(0, int(max_bytes or 0))
    if limit > 0 and len(text) > limit:
        text = text[-limit:]
        reasons.append("snapshot_request_limit")
    limited = _workspace_limited_tail_payload(
        text,
        max_lines=max_lines,
        tail_chars=tail_chars,
        truncated=truncated,
        truncation_reasons=reasons,
    )
    file_size = safe_int(snapshot.get("file_size"), 0)
    read_bytes = safe_int(snapshot.get("read_bytes"), safe_int(snapshot.get("byte_count"), limited["tail_bytes"]))
    skipped_bytes = safe_int(snapshot.get("skipped_bytes"), max(file_size - read_bytes, 0) if file_size and read_bytes else 0)
    if skipped_bytes > 0 and "byte_window" not in limited["truncation_reasons"]:
        limited["truncation_reasons"].append("byte_window")
        limited["truncated"] = True
    return {
        **limited,
        "tail_source": "snapshot",
        "snapshot_source": str(snapshot.get("source") or "").strip(),
        "snapshot_captured_at": str(snapshot.get("captured_at") or "").strip(),
        "snapshot_schema": str(snapshot.get("schema") or "").strip(),
        "file_size": file_size,
        "read_bytes": read_bytes,
        "skipped_bytes": skipped_bytes,
        "log_path": str(snapshot.get("log_path") or job.get("log_path") or "").strip(),
        "remote_log_path": remote_runtime_log_display_path(snapshot.get("remote_log_path") or job.get("remote_log_path")),
    }


def workspace_job_cached_log_tail_payload(
    job: dict[str, Any] | None,
    *,
    max_lines: int = 240,
    max_bytes: int = 65536,
    tail_chars: int | None = None,
) -> dict[str, Any]:
    if not job:
        return {
            "tail": "",
            "tail_source": "",
            "truncated": False,
            "truncation_reasons": [],
        }

    def snapshot_payload() -> dict[str, Any]:
        return _workspace_job_log_tail_snapshot_payload(
            job,
            max_lines=max_lines,
            max_bytes=max_bytes,
            tail_chars=tail_chars,
        )

    path_text = str(job.get("log_path") or "").strip()
    if not path_text:
        return snapshot_payload()
    path = normalize_allowed_local_job_log_path(job, path_text)
    if not path:
        return snapshot_payload()
    try:
        if not path.exists() or path.is_dir() or not path.is_file():
            return snapshot_payload()
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            limit = max(1, int(max_bytes or 1))
            read_from = max(size - limit, 0)
            handle.seek(read_from, os.SEEK_SET)
            data = handle.read(limit)
    except OSError:
        return snapshot_payload()
    text = data.decode("utf-8", errors="replace")
    reasons = ["byte_window"] if read_from > 0 else []
    limited = _workspace_limited_tail_payload(
        text,
        max_lines=max_lines,
        tail_chars=tail_chars,
        truncated=bool(reasons),
        truncation_reasons=reasons,
    )
    return {
        **limited,
        "tail_source": "file",
        "file_size": size,
        "read_bytes": len(data),
        "skipped_bytes": max(read_from, 0),
        "log_path": str(path),
        "display_log_path": runtime_log_display_path(path),
        "remote_log_path": remote_runtime_log_display_path(job.get("remote_log_path")),
    }


def workspace_job_cached_log_tail(job: dict[str, Any] | None, *, max_lines: int = 240, max_bytes: int = 65536) -> str:
    payload = workspace_job_cached_log_tail_payload(job, max_lines=max_lines, max_bytes=max_bytes)
    return str(payload.get("tail") or "")
