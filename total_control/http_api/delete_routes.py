from __future__ import annotations

from http import HTTPStatus
from typing import Any


def handle_delete(handler: Any, state: Any, parsed: Any) -> bool:
    if parsed.path == "/api/jobs/clear-completed":
        count = state.clear_completed_jobs()
        handler.send_json({"deleted": count})
        return True
    if parsed.path.startswith("/api/jobs/"):
        job_id = parsed.path.split("/")[3]
        state.delete_job(job_id)
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/workspaces/"):
        workspace_id = parsed.path.split("/")[3]
        state.delete_workspace(workspace_id)
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
        template_id = parsed.path.split("/")[3]
        state.delete_workflow_template(template_id)
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/agent-definitions/") and "/" not in parsed.path[23:]:
        agent_id = parsed.path.split("/")[3]
        state.delete_agent_definition(agent_id)
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/tool-definitions/") and "/" not in parsed.path[22:]:
        tool_id = parsed.path.split("/")[3]
        state.delete_tool_definition(tool_id)
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/provider-profiles/") and "/" not in parsed.path[23:]:
        profile_id = parsed.path.split("/")[3]
        state.delete_provider_profile(profile_id)
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/admin/servers/"):
        server_id = parsed.path.split("/")[4]
        state.remove_server(server_id)
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/terminal/sessions/"):
        terminal_id = parsed.path.split("/")[4]
        state.terminal_close(terminal_id)
        handler.send_json({"ok": True})
        return True
    handler.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
    return True
