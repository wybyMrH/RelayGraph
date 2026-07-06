"""Execution run replay payload helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .agent_trace import normalize_agent_trace_events
from .run_events import normalize_workspace_run_delta_evidence, normalize_workspace_run_events
from .run_refs import (
    WORKSPACE_LINKED_RUN_CLOSURE_MAX,
    _unique_run_ref_list,
    workspace_execution_run_linked_run_closure,
    workspace_jobs_for_run,
    workspace_run_step_child_run_ids,
    workspace_run_step_job_ids,
    workspace_runs_job_ids,
)


def workspace_execution_run_timeline(run: dict[str, Any]) -> list[dict[str, Any]]:
    steps = [copy.deepcopy(step) for step in (run.get("steps") if isinstance(run.get("steps"), list) else []) if isinstance(step, dict)]
    step_timeline = []
    for step in steps:
        artifacts = step.get("artifacts") if isinstance(step.get("artifacts"), list) else []
        trace_events = step.get("trace_events") if isinstance(step.get("trace_events"), list) else []
        normalized_trace_events = normalize_agent_trace_events(trace_events, limit=12)
        step_timeline.append(
            {
                "index": safe_int(step.get("index"), len(step_timeline)),
                "run_id": str(run.get("id") or "").strip(),
                "node_id": str(step.get("node_id") or "").strip(),
                "node_kind": str(step.get("node_kind") or "").strip(),
                "node_title": str(step.get("node_title") or step.get("node_kind") or "").strip(),
                "executor": str(step.get("executor") or "job").strip(),
                "status": str(step.get("status") or "").strip(),
                "job_id": str(step.get("job_id") or "").strip(),
                "child_job_ids": (
                    workspace_run_step_job_ids(step)[1:]
                    if str(step.get("job_id") or "").strip()
                    else workspace_run_step_job_ids(step)
                ),
                "child_run_ids": workspace_run_step_child_run_ids(step),
                "child_job_ref_count": safe_int(step.get("child_job_ref_count"), len(workspace_run_step_job_ids(step))),
                "child_run_ref_count": safe_int(step.get("child_run_ref_count"), len(workspace_run_step_child_run_ids(step))),
                "child_job_ids_truncated": bool(step.get("child_job_ids_truncated")),
                "child_run_ids_truncated": bool(step.get("child_run_ids_truncated")),
                "runtime_control": str(step.get("runtime_control") or "").strip(),
                "runtime_status": str(step.get("runtime_status") or "").strip(),
                "runtime_side_effect": str(step.get("runtime_side_effect") or "").strip(),
                "agent_execution_id": str(step.get("agent_execution_id") or "").strip(),
                "output_key": str(step.get("output_key") or "").strip(),
                "started_at": str(step.get("started_at") or "").strip(),
                "completed_at": str(step.get("completed_at") or "").strip(),
                "error": str(step.get("error") or "").strip(),
                "artifact_count": len([item for item in artifacts if isinstance(item, dict)]),
                "trace_event_count": len([item for item in trace_events if isinstance(item, dict)]),
                "trace_events": normalized_trace_events,
                "validation": copy.deepcopy(step.get("validation") if isinstance(step.get("validation"), dict) else {}),
            }
        )
    return step_timeline


def workspace_execution_run_replay_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    package_snapshot = run.get("package_snapshot") if isinstance(run.get("package_snapshot"), dict) else {}
    run_events = normalize_workspace_run_events(run.get("events") if isinstance(run.get("events"), list) else [])
    delta_evidence = normalize_workspace_run_delta_evidence(
        run.get("delta_evidence") if isinstance(run.get("delta_evidence"), dict) else {}
    )
    delivery = package_snapshot.get("delivery_closure") if isinstance(package_snapshot.get("delivery_closure"), dict) else {}
    return {
        "run": {
            "id": str(run.get("id") or "").strip(),
            "kind": str(run.get("kind") or "").strip(),
            "status": str(run.get("status") or "").strip(),
            "trigger": str(run.get("trigger") or "").strip(),
            "summary": str(run.get("summary") or "").strip(),
            "progress": copy.deepcopy(run.get("progress") if isinstance(run.get("progress"), dict) else {}),
            "package_id": str(run.get("package_id") or package_snapshot.get("package_id") or "").strip(),
            "event_count": len(run_events),
            "delta_evidence_count": safe_int(delta_evidence.get("total_events"), 0),
            "created_at": str(run.get("created_at") or "").strip(),
            "updated_at": str(run.get("updated_at") or "").strip(),
        },
        "timeline": workspace_execution_run_timeline(run),
        "event_timeline": run_events,
        "delta_evidence": delta_evidence,
        "package_snapshot": copy.deepcopy(package_snapshot),
        "delivery_closure": copy.deepcopy(delivery),
    }


def workspace_execution_run_replay_payload(
    workspace: dict[str, Any],
    run: dict[str, Any],
    *,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    workspace_id = str(workspace.get("id") or run.get("workspace_id") or "").strip()
    linked_closure = workspace_execution_run_linked_run_closure(workspace, run)
    linked_runs = linked_closure.get("runs") if isinstance(linked_closure.get("runs"), list) else []
    all_runs = [run, *linked_runs]
    job_ids = workspace_runs_job_ids(all_runs)
    agent_execution_ids = [
        str(step.get("agent_execution_id") or "").strip()
        for source_run in all_runs
        for step in (source_run.get("steps") if isinstance(source_run.get("steps"), list) else [])
        if isinstance(step, dict)
        if str(step.get("agent_execution_id") or "").strip()
    ]
    agent_execution_ids = _unique_run_ref_list(agent_execution_ids)
    job_index = workspace_jobs_for_run(workspace_id, run, jobs, linked_runs=linked_runs)
    linked_jobs = []
    for job_id in job_ids:
        job = job_index.get(job_id)
        if not job:
            continue
        linked_jobs.append(
            {
                "id": job_id,
                "status": str(job.get("status") or "").strip(),
                "server_id": str(job.get("server_id") or "").strip(),
                "created_at": str(job.get("created_at") or "").strip(),
                "started_at": str(job.get("started_at") or "").strip(),
                "finished_at": str(job.get("finished_at") or "").strip(),
                "error": str(job.get("error") or "").strip(),
                "command": str(job.get("command_display") or job.get("command") or "").strip(),
            }
        )
    root_replay = workspace_execution_run_replay_run_summary(run)
    return {
        "schema": "relaygraph.run.replay.v1",
        "exported_at": now_iso(),
        "workspace": {
            "id": workspace_id,
            "name": str(workspace.get("name") or "").strip(),
            "template_id": str(workspace.get("template_id") or "").strip(),
            "template_name": str(workspace.get("template_name") or "").strip(),
        },
        "run": root_replay["run"],
        "timeline": root_replay["timeline"],
        "event_timeline": root_replay["event_timeline"],
        "delta_evidence": root_replay["delta_evidence"],
        "linked_runs": [
            workspace_execution_run_replay_run_summary(linked_run)
            for linked_run in linked_runs
        ],
        "linked_run_closure": {
            "limit": safe_int(linked_closure.get("limit"), WORKSPACE_LINKED_RUN_CLOSURE_MAX),
            "included_count": safe_int(linked_closure.get("included_count"), len(linked_runs)),
            "truncated": bool(linked_closure.get("truncated")),
            "pending_count": safe_int(linked_closure.get("pending_count"), 0),
            "pending_run_ids": [
                str(item or "").strip()
                for item in (linked_closure.get("pending_run_ids") if isinstance(linked_closure.get("pending_run_ids"), list) else [])
                if str(item or "").strip()
            ],
            "missing_count": safe_int(linked_closure.get("missing_count"), 0),
            "missing_run_ids": [
                str(item or "").strip()
                for item in (linked_closure.get("missing_run_ids") if isinstance(linked_closure.get("missing_run_ids"), list) else [])
                if str(item or "").strip()
            ],
            "cross_workspace_count": safe_int(linked_closure.get("cross_workspace_count"), 0),
        },
        "linked_jobs": linked_jobs,
        "agent_execution_ids": agent_execution_ids,
        "package_snapshot": root_replay["package_snapshot"],
        "delivery_closure": root_replay["delivery_closure"],
    }
