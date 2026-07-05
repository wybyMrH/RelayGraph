from __future__ import annotations

from http import HTTPStatus
from typing import Any


def handle_put(handler: Any, state: Any, parsed: Any) -> bool:
    if parsed.path.startswith("/api/workspaces/") and "/" not in parsed.path[16:]:
        workspace_id = parsed.path.split("/")[3]
        workspace = state.update_workspace(workspace_id, handler.read_body())
        handler.send_json({"workspace": workspace})
        return True
    if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
        template_id = parsed.path.split("/")[3]
        template = state.update_workflow_template(template_id, handler.read_body())
        handler.send_json({"workflow_template": template})
        return True
    if parsed.path.startswith("/api/agent-definitions/") and "/" not in parsed.path[23:]:
        agent_id = parsed.path.split("/")[3]
        agent = state.update_agent_definition(agent_id, handler.read_body())
        handler.send_json({"agent_definition": agent})
        return True
    if parsed.path.startswith("/api/tool-definitions/") and "/" not in parsed.path[22:]:
        tool_id = parsed.path.split("/")[3]
        tool = state.update_tool_definition(tool_id, handler.read_body())
        handler.send_json({"tool_definition": tool})
        return True
    if parsed.path.startswith("/api/provider-profiles/") and "/" not in parsed.path[19:]:
        profile_id = parsed.path.split("/")[3]
        profile = state.update_provider_profile(profile_id, handler.read_body())
        handler.send_json({"provider_profile": profile})
        return True
    if parsed.path == "/api/admin/preview-cache/settings":
        body = handler.read_body()
        handler.send_json(state.update_preview_cache_settings(body))
        return True
    if parsed.path == "/api/admin/runtime-storage/settings":
        body = handler.read_body()
        handler.send_json(state.update_runtime_storage_settings(body))
        return True
    handler.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
    return True
