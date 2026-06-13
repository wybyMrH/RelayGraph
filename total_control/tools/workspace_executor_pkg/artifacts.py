from __future__ import annotations

from typing import Any

from .helpers import safe_workspace_path


def execute_artifact_read(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    artifacts = context.workspace_artifacts()
    output_key = str(arguments.get("output_key") or arguments.get("key") or "").strip()
    label = str(arguments.get("label") or "").strip().lower()
    node_kind = str(arguments.get("node_kind") or "").strip()
    if output_key:
        artifacts = [item for item in artifacts if str(item.get("output_key") or item.get("path") or "").strip() == output_key]
    if label:
        artifacts = [item for item in artifacts if label in str(item.get("label") or "").strip().lower()]
    if node_kind:
        artifacts = [item for item in artifacts if str(item.get("node_kind") or "").strip() == node_kind]

    read_path = str(arguments.get("path") or arguments.get("content_path") or "").strip()
    file_payload: dict[str, Any] | None = None
    if read_path:
        source = context.source_payload()
        resolved = safe_workspace_path(source.get("workspace_dir") or "", read_path)
        if resolved and resolved.is_file():
            try:
                text = resolved.read_text(encoding="utf-8", errors="replace")
                file_payload = {
                    "path": read_path,
                    "size": resolved.stat().st_size,
                    "content": text[:8000],
                    "truncated": len(text) > 8000,
                }
            except OSError as exc:
                file_payload = {"path": read_path, "error": str(exc)}

    return {
        "status": "read" if artifacts or file_payload else "draft",
        "artifact_count": len(artifacts),
        "artifacts": artifacts[:20],
        "file": file_payload,
    }
