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

def workspace_job_cached_log_tail(job: dict[str, Any] | None, *, max_lines: int = 240, max_bytes: int = 65536) -> str:
    if not job:
        return ""
    def snapshot_tail() -> str:
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        snapshot = metadata.get("log_tail_snapshot") if isinstance(metadata.get("log_tail_snapshot"), dict) else {}
        text = str(snapshot.get("tail") or "").strip("\n")
        if not text:
            return ""
        limited = text[-max(max_bytes, 0):] if max_bytes > 0 else text
        return "\n".join(limited.splitlines()[-max_lines:])

    path_text = str(job.get("log_path") or "").strip()
    if not path_text:
        return snapshot_tail()
    path = normalize_allowed_local_job_log_path(job, path_text)
    if not path:
        return snapshot_tail()
    try:
        if not path.exists() or path.is_dir() or not path.is_file():
            return snapshot_tail()
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - max_bytes, 0), os.SEEK_SET)
            data = handle.read(max_bytes)
    except OSError:
        return snapshot_tail()
    text = data.decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-max_lines:])
