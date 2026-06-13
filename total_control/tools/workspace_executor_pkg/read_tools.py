from __future__ import annotations

from pathlib import Path
from typing import Any

from .helpers import safe_workspace_path, scan_directory, split_values


def _workspace_dir(context: Any, arguments: dict[str, Any]) -> str:
    source = context.source_payload()
    config = context.node_config("repo.inspect")
    return str(
        arguments.get("workspace_dir")
        or source.get("workspace_dir")
        or config.get("workspace_dir")
        or ""
    ).strip()


def _read_text_file(path: Path, *, limit: int) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        stat = path.stat()
    except OSError as exc:
        return {"status": "error", "path": str(path), "error": str(exc)}
    return {
        "status": "read",
        "path": str(path),
        "name": path.name,
        "size": stat.st_size,
        "content": text[:limit],
        "truncated": len(text) > limit,
    }


def execute_file_read(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace_dir = _workspace_dir(context, arguments)
    path_text = str(arguments.get("path") or arguments.get("file") or arguments.get("target") or "").strip()
    if not workspace_dir:
        return {"status": "blocked", "message": "workspace_dir is required"}
    if not path_text:
        return {"status": "blocked", "message": "path is required"}
    try:
        limit = max(1000, min(int(float(arguments.get("limit") or arguments.get("max_chars") or 8000)), 24000))
    except (TypeError, ValueError):
        limit = 8000
    resolved = safe_workspace_path(workspace_dir, path_text)
    if not resolved:
        return {
            "status": "missing",
            "workspace_dir": workspace_dir,
            "path": path_text,
            "message": "文件不存在，或路径不在 workspace_dir 内。",
        }
    if resolved.is_dir():
        entries = scan_directory(resolved, max_depth=1, max_entries=120)
        return {
            "status": "directory",
            "workspace_dir": workspace_dir,
            "path": str(resolved),
            "entry_count": len(entries),
            "entries": entries,
        }
    return {
        "workspace_dir": workspace_dir,
        **_read_text_file(resolved, limit=limit),
    }


def execute_repo_read(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace_dir = _workspace_dir(context, arguments)
    if not workspace_dir:
        return {"status": "blocked", "message": "workspace_dir is required"}
    path_text = str(arguments.get("path") or arguments.get("file") or "").strip()
    if path_text:
        return execute_file_read(context, arguments)
    root = Path(workspace_dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return {"status": "missing", "workspace_dir": workspace_dir, "message": "workspace_dir 不存在或不是目录。"}
    requested = split_values(arguments.get("paths"))
    candidates = requested or [
        "README.md",
        "README.rst",
        "pyproject.toml",
        "requirements.txt",
        "environment.yml",
        "conda.yml",
        "setup.py",
    ]
    files: list[dict[str, Any]] = []
    for candidate in candidates:
        resolved = safe_workspace_path(str(root), candidate)
        if not resolved or not resolved.is_file():
            continue
        files.append(_read_text_file(resolved, limit=6000))
        if len(files) >= 6:
            break
    return {
        "status": "read" if files else "missing",
        "workspace_dir": str(root),
        "file_count": len(files),
        "files": files,
        "message": "已读取仓库关键文件。" if files else "没有找到 README 或常见 manifest。",
    }


def execute_repo_inspect(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace_dir = _workspace_dir(context, arguments)
    if not workspace_dir:
        return {"status": "blocked", "message": "workspace_dir is required"}
    root = Path(workspace_dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return {"status": "missing", "workspace_dir": workspace_dir, "message": "workspace_dir 不存在或不是目录。"}
    try:
        max_entries = max(30, min(int(float(arguments.get("max_entries") or 160)), 400))
    except (TypeError, ValueError):
        max_entries = 160
    entries = scan_directory(root, max_depth=1, max_entries=max_entries)
    names = {str(item.get("name") or "") for item in entries}
    manifests = [
        name
        for name in (
            "README.md",
            "README.rst",
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "environment.yml",
            "conda.yml",
            "conda.yaml",
        )
        if name in names
    ]
    run_suggestion = ""
    if "pytest.ini" in names or "tests" in names:
        run_suggestion = "python -m pytest -q"
    elif "train.py" in names:
        run_suggestion = "python train.py --help"
    elif "main.py" in names:
        run_suggestion = "python main.py --help"
    elif "app.py" in names:
        run_suggestion = "python app.py"
    return {
        "status": "inspected",
        "workspace_dir": str(root),
        "entry_count": len(entries),
        "entries": entries,
        "manifests": manifests,
        "run_suggestion": run_suggestion,
        "message": f"扫描到 {len(entries)} 个顶层条目。",
    }
