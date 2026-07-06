from __future__ import annotations

import copy
import json
import time
from typing import Any

from ...tools.registry import ToolSideEffect, create_workspace_tool_executor, tool_side_effect
from ...workspace.execution import redact_sensitive_arguments


def run_tool_definition_safe_test(
    requested_tool_id: str,
    *,
    tool: dict[str, Any] | None,
    workspace: dict[str, Any],
    arguments: dict[str, Any],
    config: Any = None,
    statuses: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
    provider_profiles: list[dict[str, Any]] | None = None,
    tool_definitions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not tool:
        raise ValueError("tool definition not found")

    side_effect = str(tool.get("side_effect") or tool_side_effect(requested_tool_id).value).strip()
    workspace_summary = {
        "id": str(workspace.get("id") or "").strip(),
        "name": str(workspace.get("name") or workspace.get("brief") or "").strip(),
    }
    if side_effect != ToolSideEffect.READ.value:
        return {
            "tool_id": requested_tool_id,
            "status": "blocked",
            "safe": False,
            "side_effect": side_effect,
            "workspace": workspace_summary,
            "arguments": redact_sensitive_arguments(copy.deepcopy(arguments)),
            "result": {
                "status": "blocked",
                "plan_only": True,
                "message": "配置中心只允许安全测试 read-only 工具；runtime/config/dangerous 工具必须通过 Agent trace 或受控 workflow/job 队列验证。",
            },
        }

    executor = create_workspace_tool_executor(
        workspace,
        config,
        statuses=statuses,
        jobs=jobs,
        provider_profiles=provider_profiles,
        tool_definitions=tool_definitions,
        runtime=None,
    )
    started = time.time()
    observation = executor(requested_tool_id, arguments)
    latency_ms = round((time.time() - started) * 1000, 1)
    parsed_result: Any
    try:
        parsed_result = json.loads(observation)
    except (TypeError, json.JSONDecodeError):
        parsed_result = {"text": str(observation or "")[:4000]}
    return {
        "tool_id": requested_tool_id,
        "status": "ok",
        "safe": True,
        "side_effect": side_effect,
        "workspace": workspace_summary,
        "arguments": redact_sensitive_arguments(copy.deepcopy(arguments)),
        "latency_ms": latency_ms,
        "result": parsed_result,
    }
