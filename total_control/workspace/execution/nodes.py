"""Execution — nodes helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403

def workspace_node_config_by_kind(workspace: dict[str, Any], kind: str) -> dict[str, Any]:
    node = next(
        (
            item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
            if isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        ),
        None,
    )
    return node.get("config") if node and isinstance(node.get("config"), dict) else {}

def workspace_node_by_kind(workspace: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(
        (
            item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
            if isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        ),
        {},
    )

def workspace_has_node_kind(workspace: dict[str, Any], kind: str) -> bool:
    return any(
        isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
    )
