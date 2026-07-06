"""Execution — runs helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .jobs import workspace_job_binding, workspace_job_sort_key
from .run_artifacts import normalize_workspace_run_step_artifacts
from .run_delivery import _workspace_delivery_path_candidates, workspace_execution_run_delivery_closure
from .run_events import (
    _compact_run_event_payload,
    _compact_run_event_text,
    _workspace_delta_event_text,
    _workspace_delta_evidence_id_list,
    normalize_workspace_run_delta_evidence,
    normalize_workspace_run_event,
    normalize_workspace_run_events,
    workspace_run_delta_evidence_from_event,
)
from .run_refs import (
    WORKSPACE_LINKED_RUN_CLOSURE_MAX,
    WORKSPACE_RUN_CHILD_REF_MAX,
    _unique_run_ref_list,
    workspace_execution_run_linked_run_closure,
    workspace_execution_run_linked_runs,
    workspace_job_matches_run_scope,
    workspace_run_allowed_child_run_ids,
    workspace_run_child_run_ids,
    workspace_run_job_ids,
    workspace_run_step_agent_execution_ids,
    workspace_run_step_child_run_ids,
    workspace_run_step_job_ids,
    workspace_runs_job_ids,
)
from .run_records import (
    derive_workspace_execution_run_progress,
    derive_workspace_execution_run_status,
    filter_workspace_execution_runs,
    make_agent_execution_id,
    make_workspace_execution_run_id,
    normalize_workspace_execution_run,
    normalize_workspace_execution_runs,
    workspace_execution_run_snapshot,
    workspace_execution_run_sort_key,
)
from .run_refresh import (
    _workspace_agent_child_runtime_status,
    _workspace_child_run_error,
    _workspace_child_run_status,
    refresh_workspace_agent_run_step_from_child_jobs,
    refresh_workspace_execution_run,
    workspace_execution_runs_public,
    workspace_jobs_bound_to_execution_run,
)
from .run_replay import (
    workspace_execution_run_replay_payload,
    workspace_execution_run_replay_run_summary,
    workspace_execution_run_timeline,
)
from .run_steps import (
    _normalize_agent_meta,
    normalize_workspace_run_step,
    normalize_workspace_run_step_resources,
    workspace_agent_runtime_refs,
    workspace_run_step_artifacts_from_job,
    workspace_run_step_from_agent,
    workspace_run_step_from_job,
    workspace_run_step_resources_from_job,
    workspace_run_step_status_from_job,
)
from .run_compare import workspace_execution_run_compare_payload
from .run_export import (
    workspace_execution_run_export_payload,
    workspace_run_export_manifest,
    workspace_run_export_readme,
)
from .trace import workspace_node_artifacts, workspace_node_resources, workspace_node_trace


def derive_workspace_execution_state(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    workspace_id = str(workspace.get("id") or "").strip()
    counts = {
        "pending": 0,
        "queued": 0,
        "running": 0,
        "done": 0,
        "failed": 0,
    }
    node_states: list[dict[str, Any]] = []
    latest_job: dict[str, Any] | None = None
    latest_error_job: dict[str, Any] | None = None

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        bound_jobs = [
            job for job in jobs
            if workspace_job_binding(job) == (workspace_id, node_id)
        ]
        bound_jobs.sort(key=workspace_job_sort_key, reverse=True)
        latest = bound_jobs[0] if bound_jobs else None
        state = "pending"
        if latest:
            job_status = str(latest.get("status") or "").strip()
            if job_status in {"queued", "blocked", "starting"}:
                state = "queued"
            elif job_status == "running":
                state = "running"
            elif job_status == "done":
                state = "done"
            else:
                state = "failed"
            if latest_job is None or workspace_job_sort_key(latest) > workspace_job_sort_key(latest_job):
                latest_job = latest
            if str(latest.get("error") or "").strip():
                if latest_error_job is None or workspace_job_sort_key(latest) > workspace_job_sort_key(latest_error_job):
                    latest_error_job = latest
        counts[state] += 1
        resources = workspace_node_resources(workspace, node, latest)
        artifacts = workspace_node_artifacts(workspace, node, latest)
        trace = workspace_node_trace(node, bound_jobs, state)
        latest_metadata = latest.get("metadata") if latest and isinstance(latest.get("metadata"), dict) else {}
        runtime_contract = latest_metadata.get("workflow_contract_node") if isinstance(latest_metadata.get("workflow_contract_node"), dict) else {}
        runtime_bundle = latest_metadata.get("execution_bundle") if isinstance(latest_metadata.get("execution_bundle"), dict) else {}
        if not runtime_contract:
            from ..automation.contracts import workspace_node_workflow_contract_metadata

            runtime_contract = workspace_node_workflow_contract_metadata(workspace, node)
        node_states.append(
            {
                "id": node_id,
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or "").strip(),
                "status": state,
                "agent_id": str(handler.get("agent_id") or "").strip(),
                "agent_name": str(handler.get("name") or "").strip(),
                "job_id": str(latest.get("id") or "").strip() if latest else "",
                "job_status": str(latest.get("status") or "").strip() if latest else "",
                "error": str(latest.get("error") or "").strip() if latest else "",
                "run_count": len(bound_jobs),
                "trace": trace,
                "artifacts": artifacts,
                "resources": resources,
                "workflow_contract_node": runtime_contract,
                "execution_bundle": runtime_bundle,
            }
        )

    selected_node = (
        next((item for item in node_states if item["status"] == "running"), None)
        or next((item for item in node_states if item["status"] == "queued"), None)
        or next((item for item in node_states if item["status"] == "failed"), None)
        or next((item for item in node_states if item["status"] == "pending"), None)
        or (node_states[-1] if node_states else None)
    )
    current_node_id = str(selected_node.get("id") or "").strip() if selected_node else ""
    current_agent_id = str(selected_node.get("agent_id") or "").strip() if selected_node else ""

    return {
        "current_node_id": current_node_id,
        "current_agent_id": current_agent_id,
        "counts": counts,
        "nodes": node_states,
        "last_job_id": str(latest_job.get("id") or "").strip() if latest_job else "",
        "last_job_status": str(latest_job.get("status") or "").strip() if latest_job else "",
        "latest_error": str(latest_error_job.get("error") or "").strip() if latest_error_job else "",
    }
