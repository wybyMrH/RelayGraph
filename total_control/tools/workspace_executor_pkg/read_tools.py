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


def execute_path_resolve(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    source = context.source_payload()
    workspace_dir = _workspace_dir(context, arguments) or str(source.get("workspace_dir") or "").strip()
    config = context.node_config("path.resolve")
    values = [workspace_dir]
    values.extend(split_values(arguments.get("paths") or arguments.get("data_roots") or config.get("data_roots")))
    values.extend(split_values(arguments.get("output_roots") or config.get("output_roots")))
    root = Path(workspace_dir).expanduser().resolve() if workspace_dir else None
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        path = Path(text).expanduser()
        if not path.is_absolute() and root:
            path = root / text
        path = path.resolve()
        exists = path.exists()
        resolved.append(
            {
                "input": text,
                "path": str(path),
                "exists": exists,
                "is_dir": path.is_dir() if exists else False,
                "is_file": path.is_file() if exists else False,
            }
        )
    return {
        "status": "resolved" if resolved else "blocked",
        "workspace_dir": str(root) if root else "",
        "paths": resolved,
        "message": f"解析 {len(resolved)} 个路径。" if resolved else "等待 workspace_dir 或 paths。",
    }


def execute_artifact_collect(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace_dir = _workspace_dir(context, arguments)
    config = context.node_config("artifact.collect")
    artifacts = context.workspace_artifacts()
    artifact_paths = split_values(arguments.get("artifact_paths") or arguments.get("paths") or config.get("artifact_paths"))
    metric_paths = split_values(arguments.get("metric_paths") or config.get("metric_paths"))
    collected: list[dict[str, Any]] = []
    for label, values in (("artifact", artifact_paths), ("metric", metric_paths)):
        for value in values:
            resolved = safe_workspace_path(workspace_dir, value) if workspace_dir else None
            if not resolved:
                collected.append({"label": label, "input": value, "status": "missing"})
                continue
            item: dict[str, Any] = {
                "label": label,
                "input": value,
                "status": "found",
                "path": str(resolved),
                "is_dir": resolved.is_dir(),
                "is_file": resolved.is_file(),
            }
            if resolved.is_file():
                try:
                    item["size"] = resolved.stat().st_size
                except OSError:
                    item["size"] = 0
            elif resolved.is_dir():
                item["entries"] = scan_directory(resolved, max_depth=1, max_entries=80)
            collected.append(item)
    return {
        "status": "collected" if artifacts or collected else "draft",
        "workspace_dir": workspace_dir,
        "artifact_count": len(artifacts),
        "artifacts": artifacts[:20],
        "collected": collected[:40],
        "message": (
            f"收集到 {len(artifacts)} 条已登记产物、{len(collected)} 个路径结果。"
            if artifacts or collected
            else "等待 artifact_paths 或已登记产物。"
        ),
    }
