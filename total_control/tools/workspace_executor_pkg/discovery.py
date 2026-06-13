from __future__ import annotations

from pathlib import Path
from typing import Any

from .helpers import safe_workspace_path, scan_directory, split_values


def execute_dataset_find(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    source = context.source_payload()
    config = context.node_config("dataset.find")
    workspace_dir = str(
        arguments.get("workspace_dir")
        or source.get("workspace_dir")
        or config.get("workspace_dir")
        or ""
    ).strip()
    query = str(arguments.get("query") or config.get("query") or source.get("goal_text") or "").strip()
    roots = split_values(arguments.get("data_roots") or config.get("data_roots"))
    hints = split_values(arguments.get("dataset_hints") or config.get("dataset_hints"))
    for value in source["references"]:
        text = str(value or "").strip()
        if not text:
            continue
        if text.startswith("/") or text.startswith("./") or "data" in text.lower():
            if text not in roots:
                roots.append(text)
        elif text not in hints:
            hints.append(text)

    data_like_names = {
        "data",
        "dataset",
        "datasets",
        "assets",
        "resources",
        "input",
        "inputs",
        "raw",
        "storage",
    }
    scanned_roots: list[str] = []
    discovered_dirs: list[dict[str, Any]] = []
    readme_hints: list[str] = []
    scan_targets: list[str] = []
    if workspace_dir:
        scan_targets.append(workspace_dir)
    scan_targets.extend(roots)
    seen_roots: set[str] = set()
    for root_text in scan_targets:
        text = str(root_text or "").strip()
        if not text or text in seen_roots:
            continue
        seen_roots.add(text)
        root_path = Path(text).expanduser()
        if not root_path.is_absolute() and workspace_dir:
            resolved = safe_workspace_path(workspace_dir, text)
            root_path = resolved or (Path(workspace_dir).expanduser() / text.lstrip("/"))
        root_path = root_path.resolve()
        if not root_path.exists() or not root_path.is_dir():
            continue
        scanned_roots.append(str(root_path))
        entries = scan_directory(root_path, max_depth=2, max_entries=120, include_dirs=True, include_files=False)
        for entry in entries:
            name = str(entry.get("name") or "").strip().lower()
            rel = str(entry.get("path") or "").strip()
            if not rel:
                continue
            if name in data_like_names or "data" in name or "dataset" in name:
                discovered_dirs.append(
                    {
                        "name": entry.get("name"),
                        "path": rel,
                        "root": str(root_path),
                        "depth": entry.get("depth"),
                    }
                )
                candidate = rel if rel.startswith("/") else str((root_path / rel).resolve())
                if candidate not in roots:
                    roots.append(candidate)

    if workspace_dir:
        for readme_name in ("README.md", "README.rst", "readme.md", "README"):
            readme_path = safe_workspace_path(workspace_dir, readme_name)
            if not readme_path or not readme_path.is_file():
                continue
            try:
                text = readme_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                normalized = line.strip()
                if not normalized:
                    continue
                lower = normalized.lower()
                if any(token in lower for token in ("dataset", "data/", "download", "数据", "数据集")):
                    if normalized not in readme_hints:
                        readme_hints.append(normalized[:200])
            break

    merged_hints = hints + readme_hints
    status = "found" if roots or merged_hints else "draft"
    return {
        "status": status,
        "query": query,
        "data_roots": roots[:16],
        "dataset_hints": merged_hints[:16],
        "scanned_roots": scanned_roots[:8],
        "discovered_dirs": discovered_dirs[:24],
        "message": (
            f"发现 {len(roots)} 个数据根目录、{len(merged_hints)} 条线索。"
            if status == "found"
            else "等待 workspace_dir、数据根目录或参考线索。"
        ),
    }


def execute_dir_scan(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    source = context.source_payload()
    config = context.node_config("dataset.find")
    workspace_dir = str(arguments.get("workspace_dir") or source.get("workspace_dir") or config.get("workspace_dir") or "").strip()
    scan_root = str(arguments.get("path") or arguments.get("root") or workspace_dir or "").strip()
    if not scan_root:
        return {"status": "draft", "message": "等待 workspace_dir 或 path。", "entries": []}
    root_path = Path(scan_root).expanduser()
    if not root_path.is_absolute() and workspace_dir:
        resolved = safe_workspace_path(workspace_dir, scan_root)
        root_path = resolved or (Path(workspace_dir).expanduser() / scan_root.lstrip("/"))
    root_path = root_path.resolve()
    if not root_path.exists():
        return {"status": "missing", "root": str(root_path), "message": "目录不存在。", "entries": []}
    if not root_path.is_dir():
        return {"status": "blocked", "root": str(root_path), "message": "目标不是目录。", "entries": []}
    max_depth = max(0, min(int(float(arguments.get("max_depth") or 2)), 4))
    max_entries = max(20, min(int(float(arguments.get("max_entries") or 180)), 400))
    entries = scan_directory(root_path, max_depth=max_depth, max_entries=max_entries)
    return {
        "status": "scanned",
        "root": str(root_path),
        "entry_count": len(entries),
        "truncated": len(entries) >= max_entries,
        "max_depth": max_depth,
        "entries": entries,
    }
