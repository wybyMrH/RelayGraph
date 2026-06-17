from __future__ import annotations

import copy
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote

from ..events import stream_workspace_events
from ..utils import safe_int


def handle_get(handler: Any, state: Any, parsed: Any) -> bool:
    if parsed.path == "/api/status":
        handler.send_json(state.status_payload())
        return True
    if parsed.path == "/api/refresh":
        state.refresh_status()
        state.monitor_jobs()
        handler.send_json(state.status_payload())
        return True
    if parsed.path == "/api/jobs":
        handler.send_json({"jobs": state.jobs})
        return True
    if parsed.path == "/api/workspaces":
        handler.send_json(state.list_workspaces())
        return True
    if parsed.path == "/api/workflow-templates":
        handler.send_json(state.list_workflow_templates())
        return True
    if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
        template_id = parsed.path.split("/")[3]
        template = state.workflow_template_by_id(template_id)
        if not template:
            handler.send_json({"error": "workflow template not found"}, HTTPStatus.NOT_FOUND)
            return True
        handler.send_json({"workflow_template": state.workflow_template_public_payload(template)})
        return True
    if parsed.path == "/api/agent-definitions":
        handler.send_json(state.list_agent_definitions())
        return True
    if parsed.path.startswith("/api/agent-definitions/") and "/" not in parsed.path[23:]:
        agent_id = parsed.path.split("/")[3]
        agent = state.agent_definition_by_id(agent_id)
        if not agent:
            handler.send_json({"error": "agent definition not found"}, HTTPStatus.NOT_FOUND)
            return True
        handler.send_json({"agent_definition": copy.deepcopy(agent)})
        return True
    if parsed.path == "/api/tool-definitions":
        handler.send_json(state.list_tool_definitions())
        return True
    if parsed.path.startswith("/api/tool-definitions/") and "/" not in parsed.path[22:]:
        tool_id = parsed.path.split("/")[3]
        tool = state.tool_definition_by_id(tool_id)
        if not tool:
            handler.send_json({"error": "tool definition not found"}, HTTPStatus.NOT_FOUND)
            return True
        handler.send_json({"tool_definition": copy.deepcopy(tool)})
        return True
    parts = parsed.path.split("/")
    if parsed.path.startswith("/api/workspaces/") and len(parts) == 5 and parts[4] == "events":
        workspace_id = unquote(parts[3])
        if not state.workspace_by_id(workspace_id):
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
            return True
        query = parse_qs(parsed.query)
        since_id = safe_int((query.get("since") or [handler.headers.get("Last-Event-ID", "0")])[0], 0)
        stream_workspace_events(
            handler,
            state.event_broker,
            workspace_id,
            since_id=since_id,
            stop_event=getattr(state, "stop_event", None),
        )
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/cockpit"):
        workspace_id = parsed.path.split("/")[3]
        try:
            handler.send_json(state.workspace_cockpit_payload(workspace_id))
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path.startswith("/api/workspaces/") and len(parts) == 6 and parts[4] == "runs":
        workspace_id = unquote(parts[3])
        run_id = unquote(parts[5])
        try:
            handler.send_json(state.get_workspace_execution_run(workspace_id, run_id))
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        except KeyError:
            handler.send_json({"error": "workspace execution run not found"}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/runs"):
        workspace_id = parsed.path.split("/")[3]
        query = parse_qs(parsed.query)
        try:
            handler.send_json(
                state.list_workspace_execution_runs(
                    workspace_id,
                    status=str((query.get("status") or [""])[0]),
                    node_kind=str((query.get("node_kind") or [""])[0]),
                    job_id=str((query.get("job_id") or [""])[0]),
                    agent_execution_id=str((query.get("agent_execution_id") or [""])[0]),
                )
            )
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path.startswith("/api/workspaces/") and "/" not in parsed.path[16:]:
        workspace_id = parsed.path.split("/")[3]
        workspace = state.workspace_by_id(workspace_id)
        if not workspace:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
            return True
        handler.send_json({"workspace": state.workspace_public_payload(workspace)})
        return True
    if parsed.path == "/api/provider-profiles":
        handler.send_json(state.list_provider_profiles())
        return True
    if parsed.path == "/api/provider-catalog":
        handler.send_json(state.list_provider_catalog())
        return True
    if parsed.path.startswith("/api/provider-profiles/") and "/" not in parsed.path[19:]:
        profile_id = parsed.path.split("/")[3]
        profile = state.provider_profile_by_id(profile_id)
        if not profile:
            handler.send_json({"error": "provider profile not found"}, HTTPStatus.NOT_FOUND)
            return True
        result = dict(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        handler.send_json({"provider_profile": result})
        return True
    if parsed.path == "/api/files/browse":
        query = parse_qs(parsed.query)
        path = (query.get("path") or [""])[0]
        server_id = (query.get("server_id") or [""])[0]
        max_entries = safe_int((query.get("max") or ["300"])[0], 300)
        dirs_only = str((query.get("dirs_only") or ["0"])[0]).lower() in {"1", "true", "yes", "on"}
        handler.send_json(
            state.browse_files(
                server_id=server_id,
                path_text=path,
                max_entries=max_entries,
                dirs_only=dirs_only,
            )
        )
        return True
    if parsed.path == "/api/files/read":
        query = parse_qs(parsed.query)
        path = (query.get("path") or [""])[0]
        server_id = (query.get("server_id") or [""])[0]
        limit = safe_int((query.get("limit") or ["131072"])[0], 131072)
        handler.send_json(
            state.read_file_text(
                server_id=server_id,
                path_text=path,
                limit_bytes=limit,
            )
        )
        return True
    if parsed.path.startswith("/api/files/cache/"):
        parts = parsed.path.split("/")
        cache_id = parts[4] if len(parts) >= 5 else ""
        entry = state.file_preview_entry(cache_id)
        query = parse_qs(parsed.query)
        download = str((query.get("download") or ["0"])[0]).lower() in {"1", "true", "yes", "on"}
        handler.send_file(
            Path(str(entry.get("local_path") or "")),
            content_type=str(entry.get("mime_type") or "application/octet-stream"),
            disposition="attachment" if download else "inline",
            filename=Path(str(entry.get("source_path") or entry.get("local_path") or "preview")).name or "preview",
        )
        return True
    if parsed.path == "/api/admin/servers":
        handler.send_json(state.list_servers_admin())
        return True
    if parsed.path == "/api/admin/preview-cache":
        handler.send_json(state.preview_cache_status())
        return True
    if parsed.path.startswith("/api/servers/") and parsed.path.endswith("/tmux"):
        server_id = parsed.path.split("/")[3]
        try:
            sessions = state.list_tmux_sessions(server_id)
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return True
        handler.send_json({"server_id": server_id, "sessions": sessions})
        return True
    if parsed.path.startswith("/api/servers/") and parsed.path.endswith("/refresh"):
        server_id = parsed.path.split("/")[3]
        try:
            server_status = state.refresh_server_status(server_id)
            state.monitor_jobs()
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return True
        payload = state.status_payload()
        payload["server"] = server_status
        handler.send_json(payload)
        return True
    if (
        parsed.path.startswith("/api/servers/")
        and "/tmux/" in parsed.path
        and parsed.path.endswith("/capture")
    ):
        parts = parsed.path.split("/")
        if len(parts) >= 7:
            server_id = parts[3]
            session = unquote(parts[5])
            query = parse_qs(parsed.query)
            lines = safe_int((query.get("lines") or ["10000"])[0], 10000)
            try:
                text = state.capture_tmux(server_id, session, lines=lines)
                handler.send_json({"server_id": server_id, "session": session, "log": text})
            except ValueError as exc:
                handler.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return True
    if parsed.path.startswith("/api/terminal/sessions/") and parsed.path.endswith("/output"):
        parts = parsed.path.split("/")
        if len(parts) >= 6:
            terminal_id = parts[4]
            query = parse_qs(parsed.query)
            cursor = safe_int((query.get("cursor") or ["0"])[0], 0)
            handler.send_json(state.terminal_read(terminal_id, cursor))
            return True
    if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/log"):
        job_id = parsed.path.split("/")[3]
        job = next((item for item in state.jobs if item["id"] == job_id), None)
        if not job:
            handler.send_json({"error": "job not found"}, HTTPStatus.NOT_FOUND)
            return True
        handler.send_json({"job_id": job_id, "log": state.tail_log(job)})
        return True
    if parsed.path.startswith("/api/"):
        handler.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        return True
    return False
