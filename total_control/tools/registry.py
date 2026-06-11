from __future__ import annotations

from enum import Enum


class ToolSideEffect(str, Enum):
    READ = "read"
    MUTATE_CONFIG = "mutate_config"
    MUTATE_RUNTIME = "mutate_runtime"
    DANGEROUS = "dangerous"


# Phase 3 rollout map. `implemented=False` keeps current simulated responses.
TOOL_SIDE_EFFECTS: dict[str, dict[str, object]] = {
    "repo.read": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "repo.inspect": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "file.read": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "gpu.inspect": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "artifact.read": {"side_effect": ToolSideEffect.READ, "implemented": True},
    "artifact.write": {"side_effect": ToolSideEffect.MUTATE_CONFIG, "implemented": True},
    "workflow.edit": {"side_effect": ToolSideEffect.MUTATE_CONFIG, "implemented": True},
    "report.write": {"side_effect": ToolSideEffect.MUTATE_CONFIG, "implemented": True},
    "dataset.find": {"side_effect": ToolSideEffect.READ, "implemented": False},
    "dir.scan": {"side_effect": ToolSideEffect.READ, "implemented": False},
    "web.search": {"side_effect": ToolSideEffect.READ, "implemented": False},
    "job.run": {"side_effect": ToolSideEffect.MUTATE_RUNTIME, "implemented": True},
    "host.exec": {"side_effect": ToolSideEffect.MUTATE_RUNTIME, "implemented": False},
    "job.stop": {"side_effect": ToolSideEffect.DANGEROUS, "implemented": False},
}


def tool_side_effect(tool_id: str) -> ToolSideEffect:
    meta = TOOL_SIDE_EFFECTS.get(str(tool_id or "").strip(), {})
    value = meta.get("side_effect")
    if isinstance(value, ToolSideEffect):
        return value
    return ToolSideEffect.READ
