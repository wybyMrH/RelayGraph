"""Execution run artifact normalization helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .log_parser import workspace_dedupe_artifacts


def normalize_workspace_run_step_artifacts(value: Any, current: Any = None) -> list[dict[str, Any]]:
    raw_items = value if isinstance(value, list) else (current if isinstance(current, list) else [])
    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("name") or item.get("kind") or "artifact").strip()
        path = str(item.get("resolved_path") or item.get("path") or item.get("value") or "").strip()
        if not label and not path:
            continue
        normalized = {
            "label": label or "artifact",
            "path": path,
            "resolved_path": str(item.get("resolved_path") or path).strip(),
            "source": str(item.get("source") or "").strip(),
            "status": str(item.get("status") or "planned").strip() or "planned",
            "exists": bool(item.get("exists")) if item.get("exists") is not None else False,
        }
        artifact_type = str(item.get("type") or item.get("artifact_type") or "").strip()
        if artifact_type:
            normalized["type"] = artifact_type
        summary = str(item.get("summary") or "").strip()
        if summary:
            normalized["summary"] = summary[:240]
        content = str(item.get("content") or "")
        if not item.get("report_id"):
            content = content.strip()
        if content:
            normalized["content"] = content[:4000]
        if item.get("node_id"):
            normalized["node_id"] = str(item.get("node_id") or "").strip()
        if item.get("node_kind"):
            normalized["node_kind"] = str(item.get("node_kind") or "").strip()
        if item.get("report_id"):
            for key in ("report_id", "run_id", "step_id", "attempt_id", "host_id", "sha256", "verified_at", "reason"):
                normalized[key] = str(item.get(key) or "")
            normalized["size_bytes"] = safe_int(item.get("size_bytes"), 0)
            normalized["file_verified"] = bool(item.get("file_verified"))
        items.append(normalized)
    return workspace_dedupe_artifacts(items)[:24]
