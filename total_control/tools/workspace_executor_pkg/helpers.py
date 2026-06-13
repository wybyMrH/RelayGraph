from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def split_values(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_items = [str(item or "") for item in value]
    else:
        raw_items = str(value or "").replace(",", "\n").splitlines()
    seen: set[str] = set()
    values: list[str] = []
    for raw in raw_items:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        values.append(item)
    return values


def safe_workspace_path(workspace_dir: str, path: str) -> Path | None:
    root_text = str(workspace_dir or "").strip()
    target_text = str(path or "").strip()
    if not root_text or not target_text:
        return None
    root = Path(root_text).expanduser().resolve()
    target = Path(target_text).expanduser()
    if not target.is_absolute():
        target = (root / target_text.lstrip("/")).resolve()
    else:
        target = target.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target if target.exists() else None


def preview_value(value: Any, *, limit: int = 120) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        text = " ".join(value.split())
        return text[:limit] + ("…" if len(text) > limit else "")
    if isinstance(value, list):
        if not value:
            return "[]"
        items = [preview_value(item, limit=40) for item in value[:4]]
        suffix = f" +{len(value) - 4}" if len(value) > 4 else ""
        return f"[{', '.join(items)}{suffix}]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = []
        for index, (key, item) in enumerate(value.items()):
            if index >= 4:
                parts.append("…")
                break
            parts.append(f"{key}: {preview_value(item, limit=32)}")
        return "{" + ", ".join(parts) + "}"
    return preview_value(str(value), limit=limit)


def scan_directory(
    root_path: Path,
    *,
    max_depth: int = 2,
    max_entries: int = 180,
    include_files: bool = True,
    include_dirs: bool = True,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    root = root_path.resolve()
    if not root.is_dir():
        return entries
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        depth = len(current.relative_to(root).parts)
        if depth > max_depth:
            dirnames[:] = []
            continue
        dirnames.sort()
        filenames.sort()
        if include_dirs:
            for name in dirnames:
                if len(entries) >= max_entries:
                    return entries
                path = current / name
                try:
                    rel = str(path.relative_to(root))
                except ValueError:
                    rel = str(path)
                entries.append({"name": name, "path": rel, "type": "dir", "depth": depth + 1})
        if include_files:
            for name in filenames:
                if len(entries) >= max_entries:
                    return entries
                path = current / name
                try:
                    rel = str(path.relative_to(root))
                except ValueError:
                    rel = str(path)
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                entries.append({"name": name, "path": rel, "type": "file", "depth": depth + 1, "size": size})
    return entries


def summarize_mapped_inputs(mapped_inputs: dict[str, Any] | None, *, limit: int = 6) -> list[dict[str, str]]:
    if not isinstance(mapped_inputs, dict):
        return []
    items: list[dict[str, str]] = []
    for key, value in mapped_inputs.items():
        name = str(key or "").strip()
        if not name:
            continue
        present = value is not None and value != "" and value != [] and value != {}
        items.append(
            {
                "name": name,
                "preview": preview_value(value),
                "present": "true" if present else "false",
            }
        )
        if len(items) >= limit:
            break
    return items


_split_values = split_values
_safe_workspace_path = safe_workspace_path
_preview_value = preview_value
_scan_directory = scan_directory
