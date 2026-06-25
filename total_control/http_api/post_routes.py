from __future__ import annotations

import signal
from http import HTTPStatus
from typing import Any

from ..infra.shell import check_transfer_conflicts
from ..utils import safe_int
from ..workspace.errors import WorkspaceWorkflowReadinessError


def handle_post(handler: Any, state: Any, parsed: Any) -> bool:
    if parsed.path == "/api/workspaces":
        workspace = state.create_workspace(handler.read_body())
        handler.send_json({"workspace": workspace}, HTTPStatus.CREATED)
        return True
    if parsed.path == "/api/workflow-templates":
        template = state.create_workflow_template(handler.read_body())
        handler.send_json({"workflow_template": template}, HTTPStatus.CREATED)
        return True
    if parsed.path == "/api/workflow-templates/preview":
        try:
            handler.send_json(state.validate_workflow_template(handler.read_body()))
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return True
    if parsed.path == "/api/agent-definitions":
        agent = state.create_agent_definition(handler.read_body())
        handler.send_json({"agent_definition": agent}, HTTPStatus.CREATED)
        return True
    if parsed.path == "/api/tool-definitions":
        tool = state.create_tool_definition(handler.read_body())
        handler.send_json({"tool_definition": tool}, HTTPStatus.CREATED)
        return True
    if parsed.path.startswith("/api/tool-definitions/") and parsed.path.endswith("/test"):
        tool_id = parsed.path.split("/")[3]
        try:
            handler.send_json({"test": state.test_tool_definition(tool_id, handler.read_body())})
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path == "/api/provider-profiles":
        profile = state.create_provider_profile(handler.read_body())
        handler.send_json({"provider_profile": profile}, HTTPStatus.CREATED)
        return True
    if parsed.path == "/api/provider-profiles/from-catalog":
        body = handler.read_body()
        try:
            profile = state.create_provider_profile_from_catalog(
                str(body.get("vendor_id") or body.get("id") or "").strip(),
                api_key=str(body.get("api_key") or "").strip(),
                name=str(body.get("name") or "").strip(),
                models=body.get("models") if isinstance(body.get("models"), list) else None,
                is_default=bool(body.get("is_default")),
            )
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return True
        handler.send_json({"provider_profile": profile}, HTTPStatus.CREATED)
        return True
    if parsed.path == "/api/provider-profiles/test":
        result = state.test_provider_profile(handler.read_body())
        handler.send_json({"test": result})
        return True
    if parsed.path == "/api/provider-profiles/models":
        result = state.list_provider_models(handler.read_body())
        handler.send_json({"models": result})
        return True
    if parsed.path == "/api/jobs":
        job = state.create_job(handler.read_body())
        handler.send_json({"job": job}, HTTPStatus.CREATED)
        return True
    if parsed.path == "/api/task-plans/preview":
        handler.send_json(state.task_plan_preview(handler.read_body()))
        return True
    if parsed.path == "/api/files/fetch":
        body = handler.read_body()
        handler.send_json(
            state.fetch_file_preview(
                server_id=str(body.get("server_id") or ""),
                path_text=str(body.get("path") or ""),
                limit_bytes=safe_int(body.get("limit_bytes"), 131072),
            )
        )
        return True
    if parsed.path == "/api/files/transfer-conflicts":
        body = handler.read_body()
        handler.send_json(check_transfer_conflicts(body, state.servers))
        return True
    if parsed.path == "/api/task-plans/schedule":
        result = state.create_task_plan_jobs(handler.read_body())
        status = HTTPStatus.OK if result.get("dry_run") else HTTPStatus.CREATED
        handler.send_json(result, status)
        return True
    if parsed.path == "/api/presets/plan":
        handler.send_json(state.preset_plan(handler.read_body()))
        return True
    if parsed.path == "/api/presets/schedule":
        result = state.create_preset_jobs(handler.read_body())
        status = HTTPStatus.OK if result.get("dry_run") else HTTPStatus.CREATED
        handler.send_json(result, status)
        return True
    if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/stop"):
        job_id = parsed.path.split("/")[3]
        job = state.stop_job(job_id)
        handler.send_json({"job": job})
        return True
    if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/retry"):
        job_id = parsed.path.split("/")[3]
        job = state.retry_job(job_id)
        handler.send_json({"job": job}, HTTPStatus.CREATED)
        return True
    if parsed.path.startswith("/api/agent-executions/") and parsed.path.endswith("/cancel"):
        execution_id = parsed.path.split("/")[3]
        result = state.cancel_agent_execution(execution_id)
        status = HTTPStatus.OK if result.get("cancelled") else HTTPStatus.NOT_FOUND
        handler.send_json(result, status)
        return True
    if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/copy"):
        job_id = parsed.path.split("/")[3]
        job = state.copy_job(job_id)
        handler.send_json({"job": job}, HTTPStatus.CREATED)
        return True
    if (
        parsed.path.startswith("/api/servers/")
        and "/processes/" in parsed.path
        and parsed.path.endswith("/stop")
    ):
        parts = parsed.path.split("/")
        if len(parts) >= 7:
            server_id = parts[3]
            pid = parts[5]
            result = state.stop_process(server_id, pid)
            handler.send_json(result)
            return True
    if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/reorder"):
        job_id = parsed.path.split("/")[3]
        body = handler.read_body()
        result = state.reorder_job(job_id, str(body.get("direction") or ""))
        handler.send_json(result)
        return True
    if parsed.path == "/api/terminal/open":
        result = state.terminal_open(str(handler.read_body().get("server_id") or ""))
        handler.send_json(result, HTTPStatus.CREATED)
        return True
    if parsed.path == "/api/terminal/sessions":
        result = state.terminal_open(str(handler.read_body().get("server_id") or ""))
        handler.send_json(result, HTTPStatus.CREATED)
        return True
    if parsed.path.startswith("/api/terminal/sessions/") and parsed.path.endswith("/input"):
        terminal_id = parsed.path.split("/")[4]
        body = handler.read_body()
        state.terminal_write(terminal_id, str(body.get("data") or ""))
        handler.send_json({"ok": True})
        return True
    if parsed.path.startswith("/api/terminal/sessions/") and parsed.path.endswith("/signal"):
        terminal_id = parsed.path.split("/")[4]
        body = handler.read_body()
        sig = safe_int(body.get("signal"), signal.SIGINT)
        state.terminal_signal(terminal_id, sig)
        handler.send_json({"ok": True})
        return True
    if parsed.path == "/api/admin/servers":
        entry = state.add_server(handler.read_body())
        handler.send_json({"server": entry}, HTTPStatus.CREATED)
        return True
    if (
        parsed.path.startswith("/api/agent-definitions/")
        and parsed.path.endswith("/debug")
    ):
        parts = parsed.path.split("/")
        if len(parts) >= 5:
            agent_id = parts[3]
            result = state.debug_agent_definition(agent_id, handler.read_body())
            handler.send_json(result, HTTPStatus.CREATED)
            return True
    if (
        parsed.path.startswith("/api/workspaces/")
        and "/nodes/" in parsed.path
        and parsed.path.endswith("/run")
    ):
        parts = parsed.path.split("/")
        if len(parts) >= 7:
            workspace_id = parts[3]
            node_id = parts[5]
            result = state.run_workspace_node(workspace_id, node_id, handler.read_body())
            handler.send_json(result, HTTPStatus.CREATED)
            return True
    if (
        parsed.path.startswith("/api/workspaces/")
        and "/agents/" in parsed.path
        and parsed.path.endswith("/debug")
    ):
        parts = parsed.path.split("/")
        if len(parts) >= 7:
            workspace_id = parts[3]
            agent_id = parts[5]
            result = state.debug_workspace_agent(workspace_id, agent_id, handler.read_body())
            handler.send_json(result, HTTPStatus.CREATED)
            return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/chat"):
        parts = parsed.path.split("/")
        workspace_id = parts[3] if len(parts) > 3 else ""
        result = state.append_workspace_chat(workspace_id, handler.read_body())
        handler.send_json(result, HTTPStatus.CREATED)
        return True
    if (
        parsed.path.startswith("/api/workspaces/")
        and "/context-reflections/" in parsed.path
        and parsed.path.endswith("/accept")
    ):
        parts = parsed.path.split("/")
        workspace_id = parts[3] if len(parts) > 3 else ""
        message_id = parts[5] if len(parts) > 5 else ""
        try:
            result = state.accept_workspace_context_reflection(workspace_id, message_id, handler.read_body())
            handler.send_json(result)
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/automation/apply"):
        parts = parsed.path.split("/")
        workspace_id = parts[3] if len(parts) > 3 else ""
        result = state.apply_workspace_automation_defaults(workspace_id, handler.read_body())
        handler.send_json(result)
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/runs"):
        parts = parsed.path.split("/")
        workspace_id = parts[3] if len(parts) > 3 else ""
        try:
            result = state.create_workspace_execution_run(workspace_id, handler.read_body())
            handler.send_json(result, HTTPStatus.CREATED)
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/discovery/run"):
        parts = parsed.path.split("/")
        workspace_id = parts[3] if len(parts) > 3 else ""
        result = state.run_workspace_discovery(workspace_id, handler.read_body())
        handler.send_json(result, HTTPStatus.CREATED)
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/advance"):
        parts = parsed.path.split("/")
        workspace_id = parts[3] if len(parts) > 3 else ""
        result = state.advance_workspace_automation(workspace_id, handler.read_body())
        status = HTTPStatus.CREATED if result.get("jobs") else HTTPStatus.OK
        handler.send_json(result, status)
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/run"):
        parts = parsed.path.split("/")
        workspace_id = parts[3] if len(parts) > 3 else ""
        try:
            result = state.run_workspace_workflow(workspace_id, handler.read_body())
            handler.send_json(result, HTTPStatus.CREATED)
        except WorkspaceWorkflowReadinessError as exc:
            handler.send_json(
                {
                    "error": str(exc),
                    "blocked_checks": exc.blocked_checks,
                    "workspace": exc.workspace,
                    "applied": exc.applied,
                    "evidence_applied": exc.evidence_applied,
                },
                HTTPStatus.CONFLICT,
            )
        return True
    if parsed.path.startswith("/api/workspaces/"):
        workspace_id = parsed.path.split("/")[3] if len(parsed.path.split("/")) > 3 else ""
        workspace = state.update_workspace(workspace_id, handler.read_body())
        handler.send_json({"workspace": workspace})
        return True
    if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
        template_id = parsed.path.split("/")[3]
        template = state.update_workflow_template(template_id, handler.read_body())
        handler.send_json({"workflow_template": template})
        return True
    if parsed.path.startswith("/api/workflow-templates/") and parsed.path.endswith("/preview"):
        template_id = parsed.path.split("/")[3]
        try:
            handler.send_json(state.validate_workflow_template(handler.read_body(), template_id=template_id))
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
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
    if (
        parsed.path.startswith("/api/admin/servers/")
        and parsed.path.endswith("/edit")
    ):
        server_id = parsed.path.split("/")[4]
        entry = state.update_server(server_id, handler.read_body())
        handler.send_json({"server": entry})
        return True
    if (
        parsed.path.startswith("/api/admin/servers/")
        and parsed.path.endswith("/alias")
    ):
        server_id = parsed.path.split("/")[4]
        body = handler.read_body()
        state.set_server_alias(server_id, str(body.get("alias") or ""))
        handler.send_json({"ok": True})
        return True
    if (
        parsed.path.startswith("/api/admin/servers/")
        and parsed.path.endswith("/check")
    ):
        server_id = parsed.path.split("/")[4]
        handler.send_json(state.check_server(server_id))
        return True
    if parsed.path == "/api/admin/discovery/restore":
        body = handler.read_body()
        state.restore_discovery(str(body.get("alias") or ""))
        handler.send_json({"ok": True})
        return True
    if parsed.path == "/api/admin/preview-cache/cleanup":
        handler.send_json(state.cleanup_preview_cache_manual())
        return True
    handler.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
    return True
