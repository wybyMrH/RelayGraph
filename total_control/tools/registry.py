from __future__ import annotations

from enum import Enum
from typing import Any, Callable


class ToolSideEffect(str, Enum):
    READ = "read"
    MUTATE_CONFIG = "mutate_config"
    MUTATE_RUNTIME = "mutate_runtime"
    DANGEROUS = "dangerous"


# Tool side-effect map. `implemented=False` means the dispatcher returns a dry-run or simulated payload.
TOOL_SIDE_EFFECTS: dict[str, dict[str, object]] = {
    "repo.read": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "repo.inspect": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "file.read": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "gpu.inspect": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "artifact.read": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "artifact.write": {"side_effect": ToolSideEffect.MUTATE_CONFIG, "implemented": True},
    "workflow.edit": {"side_effect": ToolSideEffect.MUTATE_CONFIG, "implemented": True},
    "report.write": {"side_effect": ToolSideEffect.MUTATE_CONFIG, "implemented": True},
    "dataset.find": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "dir.scan": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "web.search": {"side_effect": ToolSideEffect.READ, "implemented": False},
    "job.run": {"side_effect": ToolSideEffect.MUTATE_RUNTIME, "implemented": False},
    "host.exec": {"side_effect": ToolSideEffect.MUTATE_RUNTIME, "implemented": False},
    "gpu.allocate": {"side_effect": ToolSideEffect.MUTATE_RUNTIME, "implemented": False},
    "job.stop": {"side_effect": ToolSideEffect.DANGEROUS, "implemented": False},
}


def tool_side_effect(tool_id: str) -> ToolSideEffect:
    meta = TOOL_SIDE_EFFECTS.get(str(tool_id or "").strip(), {})
    value = meta.get("side_effect")
    if isinstance(value, ToolSideEffect):
        return value
    return ToolSideEffect.READ


def create_workspace_tool_executor(
    workspace: dict[str, Any],
    server_config: Any = None,
    *,
    statuses: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> Callable[[str, dict[str, Any]], str]:
    """Create a workspace-bound tool executor (implementation in workspace_executor)."""
    from .workspace_executor import create_workspace_tool_executor as _factory

    return _factory(workspace, server_config, statuses=statuses, jobs=jobs)


def summarize_mapped_inputs(mapped_inputs: dict[str, Any] | None, *, limit: int = 6) -> list[dict[str, str]]:
    from .workspace_executor import summarize_mapped_inputs as _summarize

    return _summarize(mapped_inputs, limit=limit)


def WorkspaceToolContext(*args: Any, **kwargs: Any) -> Any:
    from .workspace_executor import WorkspaceToolContext as _Context

    return _Context(*args, **kwargs)
