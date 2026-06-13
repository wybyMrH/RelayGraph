from __future__ import annotations

from typing import Any, Callable

from .workspace_executor_pkg.context import WorkspaceToolContext
from .workspace_executor_pkg.helpers import (
    _preview_value,
    _safe_workspace_path,
    _scan_directory,
    _split_values,
    summarize_mapped_inputs,
)


def create_workspace_tool_executor(
    workspace: dict[str, Any],
    server_config: Any = None,
    *,
    statuses: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
    runtime: Any = None,
) -> Callable[[str, dict[str, Any]], str]:
    """Create a tool executor bound to a workspace snapshot."""
    _ = server_config
    context = WorkspaceToolContext(
        workspace=workspace if isinstance(workspace, dict) else {},
        statuses=[item for item in (statuses or []) if isinstance(item, dict)],
        jobs=[item for item in (jobs or []) if isinstance(item, dict)],
        runtime=runtime,
    )

    def executor(tool_id: str, arguments: dict[str, Any]) -> str:
        return context.execute(tool_id, arguments)

    return executor


__all__ = [
    "WorkspaceToolContext",
    "_preview_value",
    "_safe_workspace_path",
    "_scan_directory",
    "_split_values",
    "create_workspace_tool_executor",
    "summarize_mapped_inputs",
]
