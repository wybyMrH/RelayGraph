from __future__ import annotations

import copy
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote

from ..events import public_job_event_payload, stream_workspace_events
from ..utils import now_iso, safe_int


def _workspace_jobs_snapshot(state: Any, workspace_id: str) -> list[dict[str, Any]]:
    jobs = getattr(state, "jobs", [])
    items: list[dict[str, Any]] = []
    for job in jobs if isinstance(jobs, list) else []:
        if not isinstance(job, dict):
            continue
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        if str(metadata.get("workspace_id") or "").strip() != workspace_id:
            continue
        items.append(public_job_event_payload(job))
    return items


def _workspace_stream_snapshot_event(state: Any, workspace_id: str, gap: dict[str, Any]) -> dict[str, Any]:
    latest_id = state.event_broker.latest_event_id()
    if hasattr(state, "sync_workspace_execution_runs_from_jobs"):
        state.sync_workspace_execution_runs_from_jobs(workspace_id)
    with state.lock:
        workspace = state.workspace_by_id(workspace_id)
        if not workspace:
            raise ValueError("workspace not found")
        public_workspace = state.workspace_public_payload(workspace)
        jobs = _workspace_jobs_snapshot(state, workspace_id)
    automation = public_workspace.get("automation") if isinstance(public_workspace.get("automation"), dict) else {}
    cockpit = automation.get("cockpit") if isinstance(automation.get("cockpit"), dict) else {}
    return {
        "id": latest_id,
        "type": "workspace.snapshot",
        "workspace_id": workspace_id,
        "run_id": "",
        "job_id": "",
        "agent_execution_id": "",
        "created_at": now_iso(),
        "payload": {
            "workspace_id": workspace_id,
            "workspace": public_workspace,
            "runs": public_workspace.get("runs") if isinstance(public_workspace.get("runs"), list) else [],
            "jobs": jobs,
            "cockpit": cockpit,
            "execution": public_workspace.get("execution") if isinstance(public_workspace.get("execution"), dict) else {},
            "automation": automation,
            "snapshot_reason": str(gap.get("reason") or "event_replay_gap"),
            "gap": copy.deepcopy(gap),
        },
    }


def _workspace_events_replay_payload(
    state: Any,
    workspace_id: str,
    *,
    since_id: int = 0,
    limit: int = 200,
) -> dict[str, Any]:
    workspace_id = str(workspace_id or "").strip()
    since_id = safe_int(since_id, 0)
    limit = min(max(safe_int(limit, 200), 1), 1000)
    broker = state.event_broker
    gap = broker.replay_gap(since_id, workspace_id=workspace_id)
    latest_id = broker.latest_event_id()
    first_retained_id = broker.first_retained_event_id(workspace_id=workspace_id)
    if gap:
        snapshot = _workspace_stream_snapshot_event(state, workspace_id, gap)
        snapshot_id = safe_int(snapshot.get("id"), latest_id)
        return {
            "workspace_id": workspace_id,
            "since_id": since_id,
            "next_since_id": snapshot_id,
            "latest_id": latest_id,
            "first_retained_id": first_retained_id,
            "gap": copy.deepcopy(gap),
            "limited": False,
            "events": [snapshot],
            "replay_mode": "snapshot",
        }

    retained_events = broker.events_after(since_id, workspace_id=workspace_id)
    if len(retained_events) > limit:
        omitted_until_id = safe_int(retained_events[-limit - 1].get("id"), since_id) if limit < len(retained_events) else since_id
        limited_gap = {
            "reason": "replay_limit_exceeded",
            "requested_since_id": since_id,
            "dropped_until_id": omitted_until_id,
            "first_retained_id": first_retained_id,
            "latest_id": latest_id,
            "retained_count": len(retained_events),
            "limit": limit,
        }
        snapshot = _workspace_stream_snapshot_event(state, workspace_id, limited_gap)
        snapshot_id = safe_int(snapshot.get("id"), latest_id)
        return {
            "workspace_id": workspace_id,
            "since_id": since_id,
            "next_since_id": snapshot_id,
            "latest_id": latest_id,
            "first_retained_id": first_retained_id,
            "gap": limited_gap,
            "limited": True,
            "events": [snapshot],
            "replay_mode": "snapshot",
        }
    limited = False
    events = retained_events
    next_since_id = safe_int(events[-1].get("id"), since_id) if events else since_id
    return {
        "workspace_id": workspace_id,
        "since_id": since_id,
        "next_since_id": next_since_id,
        "latest_id": latest_id,
        "first_retained_id": first_retained_id,
        "gap": None,
        "limited": limited,
        "events": events,
        "replay_mode": "events",
    }


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
        handler.send_json({"jobs": [public_job_event_payload(job) for job in state.jobs]})
        return True
    if parsed.path == "/api/workspaces":
        handler.send_json(state.list_workspaces())
        return True
    if parsed.path == "/api/workflow-templates":
        handler.send_json(state.list_workflow_templates())
        return True
    if parsed.path.startswith("/api/workflow-templates/") and parsed.path.endswith("/preview"):
        template_id = parsed.path.split("/")[3]
        try:
            handler.send_json(state.validate_workflow_template({}, template_id=template_id))
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
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
    if parsed.path == "/api/provider-route-health":
        handler.send_json({"provider_route_health": state.provider_route_health()})
        return True
    if parsed.path == "/api/execution-overview":
        query = parse_qs(parsed.query)
        handler.send_json(
            state.execution_overview(
                {
                    "limit": (query.get("limit") or ["50"])[0],
                    "query": (query.get("query") or query.get("q") or [""])[0],
                    "status": (query.get("status") or [""])[0],
                    "kind": (query.get("kind") or ["all"])[0],
                },
            )
        )
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
        query_since_id = safe_int((query.get("since") or ["0"])[0], 0)
        header_since_id = safe_int(handler.headers.get("Last-Event-ID", "0"), 0)
        since_id = max(query_since_id, header_since_id)
        gap = state.event_broker.replay_gap(since_id, workspace_id=workspace_id)
        prelude_events = [_workspace_stream_snapshot_event(state, workspace_id, gap)] if gap else []
        stream_workspace_events(
            handler,
            state.event_broker,
            workspace_id,
            since_id=since_id,
            stop_event=getattr(state, "stop_event", None),
            prelude_events=prelude_events,
        )
        return True
    if parsed.path.startswith("/api/workspaces/") and len(parts) == 6 and parts[4] == "events" and parts[5] == "replay":
        workspace_id = unquote(parts[3])
        if not state.workspace_by_id(workspace_id):
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
            return True
        query = parse_qs(parsed.query)
        since_id = safe_int((query.get("since") or ["0"])[0], 0)
        limit = safe_int((query.get("limit") or ["200"])[0], 200)
        handler.send_json(
            _workspace_events_replay_payload(
                state,
                workspace_id,
                since_id=since_id,
                limit=limit,
            )
        )
        return True
    if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/cockpit"):
        workspace_id = parsed.path.split("/")[3]
        try:
            handler.send_json(state.workspace_cockpit_payload(workspace_id))
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path.startswith("/api/workspaces/") and len(parts) == 5 and parts[4] == "template-diff":
        workspace_id = unquote(parts[3])
        try:
            handler.send_json(state.workspace_template_diff(workspace_id))
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path.startswith("/api/workspaces/") and len(parts) == 7 and parts[4] == "runs" and parts[6] == "replay":
        workspace_id = unquote(parts[3])
        run_id = unquote(parts[5])
        try:
            handler.send_json(state.get_workspace_execution_run_replay(workspace_id, run_id))
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        except KeyError:
            handler.send_json({"error": "workspace execution run not found"}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path.startswith("/api/workspaces/") and len(parts) == 7 and parts[4] == "runs" and parts[6] == "export":
        workspace_id = unquote(parts[3])
        run_id = unquote(parts[5])
        try:
            handler.send_json(state.get_workspace_execution_run_export(workspace_id, run_id))
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        except KeyError:
            handler.send_json({"error": "workspace execution run not found"}, HTTPStatus.NOT_FOUND)
        return True
    if parsed.path.startswith("/api/workspaces/") and len(parts) == 6 and parts[4] == "runs" and parts[5] == "compare":
        workspace_id = unquote(parts[3])
        query = parse_qs(parsed.query)
        base_run_id = str((query.get("base") or [""])[0])
        target_run_id = str((query.get("target") or [""])[0])
        try:
            handler.send_json(state.compare_workspace_execution_runs(workspace_id, base_run_id, target_run_id))
        except ValueError:
            handler.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
        except KeyError:
            handler.send_json({"error": "workspace execution run not found"}, HTTPStatus.NOT_FOUND)
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
    if parsed.path == "/api/admin/runtime-storage":
        handler.send_json(state.runtime_storage_status())
        return True
    if parsed.path == "/api/admin/runtime-state":
        handler.send_json(state.runtime_state_status())
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
        query = parse_qs(parsed.query)
        lines = safe_int((query.get("lines") or ["200"])[0], 200)
        max_bytes = safe_int((query.get("max_bytes") or ["131072"])[0], 131072)
        offset = None
        if "offset" in query:
            offset = safe_int((query.get("offset") or ["0"])[0], 0)
        if hasattr(state, "job_log_payload"):
            handler.send_json(state.job_log_payload(job, lines=lines, offset=offset, max_bytes=max_bytes))
        else:
            handler.send_json({"job_id": job_id, "mode": "tail", "log": state.tail_log(job, lines=lines)})
        return True
    if parsed.path.startswith("/api/"):
        handler.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        return True
    return False
