"""Execution run export manifest helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .run_refs import WORKSPACE_LINKED_RUN_CLOSURE_MAX, WORKSPACE_RUN_CHILD_REF_MAX


def workspace_run_export_manifest(
    replay: dict[str, Any],
    *,
    logs: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    timeline = replay.get("timeline") if isinstance(replay.get("timeline"), list) else []
    event_timeline = replay.get("event_timeline") if isinstance(replay.get("event_timeline"), list) else []
    linked_runs = replay.get("linked_runs") if isinstance(replay.get("linked_runs"), list) else []
    linked_timeline_steps = sum(
        len(item.get("timeline")) for item in linked_runs if isinstance(item, dict) and isinstance(item.get("timeline"), list)
    )
    linked_event_count = sum(
        len(item.get("event_timeline"))
        for item in linked_runs
        if isinstance(item, dict) and isinstance(item.get("event_timeline"), list)
    )
    delta_evidence = replay.get("delta_evidence") if isinstance(replay.get("delta_evidence"), dict) else {}
    linked_delta_event_count = sum(
        safe_int(item.get("delta_evidence", {}).get("total_events"), 0)
        for item in linked_runs
        if isinstance(item, dict) and isinstance(item.get("delta_evidence"), dict)
    )
    all_timeline = [
        *timeline,
        *[
            step
            for item in linked_runs
            if isinstance(item, dict) and isinstance(item.get("timeline"), list)
            for step in item.get("timeline", [])
        ],
    ]
    run = replay.get("run") if isinstance(replay.get("run"), dict) else {}
    linked_run_closure = replay.get("linked_run_closure") if isinstance(replay.get("linked_run_closure"), dict) else {}
    delivery = replay.get("delivery_closure") if isinstance(replay.get("delivery_closure"), dict) else {}
    package_snapshot = replay.get("package_snapshot") if isinstance(replay.get("package_snapshot"), dict) else {}
    package_manifest = package_snapshot.get("package_manifest") if isinstance(package_snapshot.get("package_manifest"), dict) else {}
    commands = package_manifest.get("commands") if isinstance(package_manifest.get("commands"), dict) else {}
    failed_steps = [
        {
            "index": safe_int(step.get("index"), 0),
            "node_id": str(step.get("node_id") or "").strip(),
            "node_kind": str(step.get("node_kind") or "").strip(),
            "status": str(step.get("status") or "").strip(),
            "error": str(step.get("error") or "").strip(),
        }
        for step in all_timeline
        if isinstance(step, dict) and str(step.get("status") or "").strip() in {"failed", "blocked", "stopped"}
    ]
    status_counts: dict[str, int] = {}
    executor_counts: dict[str, int] = {}
    for step in all_timeline:
        if not isinstance(step, dict):
            continue
        status = str(step.get("status") or "unknown").strip() or "unknown"
        executor = str(step.get("executor") or "unknown").strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        executor_counts[executor] = executor_counts.get(executor, 0) + 1
    truncated_logs = [item for item in logs if isinstance(item, dict) and bool(item.get("truncated"))]
    omitted_log_bytes = sum(safe_int(item.get("skipped_bytes"), 0) for item in truncated_logs)
    return {
        "schema": "relaygraph.run.export.manifest.v1",
        "run_id": str(run.get("id") or "").strip(),
        "run_status": str(run.get("status") or "").strip(),
        "package_id": str(run.get("package_id") or package_snapshot.get("package_id") or "").strip(),
        "delivery_status": str(delivery.get("status") or "").strip(),
        "status_counts": status_counts,
        "executor_counts": executor_counts,
        "failed_steps": failed_steps[:12],
        "commands": {
            "checkout": str(commands.get("checkout_command") or "").strip(),
            "setup": str(commands.get("setup_command") or "").strip(),
            "run": str(commands.get("run_command") or "").strip(),
            "collect": str(commands.get("collect_command") or "").strip(),
            "report": str(commands.get("report_command") or "").strip(),
        },
        "included": {
            "timeline_steps": len(timeline),
            "event_timeline": len(event_timeline),
            "delta_evidence_events": safe_int(delta_evidence.get("total_events"), 0),
            "linked_runs": len(linked_runs),
            "linked_runs_truncated": bool(linked_run_closure.get("truncated")),
            "linked_timeline_steps": linked_timeline_steps,
            "linked_event_timeline": linked_event_count,
            "linked_delta_evidence_events": linked_delta_event_count,
            "linked_jobs": len(replay.get("linked_jobs") if isinstance(replay.get("linked_jobs"), list) else []),
            "agent_executions": len(replay.get("agent_execution_ids") if isinstance(replay.get("agent_execution_ids"), list) else []),
            "logs_returned": len(logs),
            "logs_truncated": len(truncated_logs),
            "artifacts_returned": len(artifacts),
            "reports_returned": len(reports),
        },
        "limits": {
            "logs": 12,
            "log_tail_bytes_each": 12000,
            "log_read_bytes_each": 24000,
            "log_tail_lines_each": 80,
            "artifacts": 48,
            "reports": 12,
            "child_refs_per_step": WORKSPACE_RUN_CHILD_REF_MAX,
            "linked_runs": safe_int(linked_run_closure.get("limit"), WORKSPACE_LINKED_RUN_CLOSURE_MAX),
            "delta_evidence_recent_per_run": WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX,
        },
        "truncation": {
            "linked_runs": bool(linked_run_closure.get("truncated")),
            "linked_run_pending_count": safe_int(linked_run_closure.get("pending_count"), 0),
            "missing_linked_run_count": safe_int(linked_run_closure.get("missing_count"), 0),
            "log_tails": len(truncated_logs),
            "omitted_log_bytes": omitted_log_bytes,
            "delta_evidence_truncated_events": safe_int(delta_evidence.get("truncated_events"), 0)
            + sum(
                safe_int(item.get("delta_evidence", {}).get("truncated_events"), 0)
                for item in linked_runs
                if isinstance(item, dict) and isinstance(item.get("delta_evidence"), dict)
            ),
            "delta_evidence_omitted_content": bool(
                safe_int(delta_evidence.get("total_events"), 0) or linked_delta_event_count
            ),
            "child_ref_steps": sum(
                1
                for step in all_timeline
                if isinstance(step, dict)
                and (bool(step.get("child_job_ids_truncated")) or bool(step.get("child_run_ids_truncated")))
            ),
        },
    }


def workspace_run_export_readme(manifest: dict[str, Any]) -> str:
    included = manifest.get("included") if isinstance(manifest.get("included"), dict) else {}
    failed_steps = manifest.get("failed_steps") if isinstance(manifest.get("failed_steps"), list) else []
    commands = manifest.get("commands") if isinstance(manifest.get("commands"), dict) else {}
    truncation = manifest.get("truncation") if isinstance(manifest.get("truncation"), dict) else {}
    lines = [
        "# RelayGraph Run Export",
        "",
        f"- Run: {str(manifest.get('run_id') or '').strip() or 'unknown'}",
        f"- Status: {str(manifest.get('run_status') or '').strip() or 'unknown'}",
        f"- Package: {str(manifest.get('package_id') or '').strip() or 'none'}",
        f"- Delivery: {str(manifest.get('delivery_status') or '').strip() or 'unknown'}",
        f"- Steps: {safe_int(included.get('timeline_steps'), 0)}",
        f"- Events: {safe_int(included.get('event_timeline'), 0)}",
        f"- Realtime delta evidence: {safe_int(included.get('delta_evidence_events'), 0)} summary-only events",
        f"- Linked runs: {safe_int(included.get('linked_runs'), 0)}",
        f"- Linked jobs: {safe_int(included.get('linked_jobs'), 0)}",
        f"- Logs included: {safe_int(included.get('logs_returned'), 0)}",
        f"- Artifacts included: {safe_int(included.get('artifacts_returned'), 0)}",
        f"- Reports included: {safe_int(included.get('reports_returned'), 0)}",
        "",
        "## Commands",
    ]
    if truncation and any(bool(value) for value in truncation.values()):
        lines[-1:] = [
            "## Truncation",
            "",
            f"- Linked runs truncated: {bool(truncation.get('linked_runs'))}",
            f"- Pending linked runs beyond limit: {safe_int(truncation.get('linked_run_pending_count'), 0)}",
            f"- Missing linked run references: {safe_int(truncation.get('missing_linked_run_count'), 0)}",
            f"- Logs with truncated tails: {safe_int(truncation.get('log_tails'), 0)}",
            f"- Omitted log bytes before included tails: {safe_int(truncation.get('omitted_log_bytes'), 0)}",
            f"- Realtime delta content omitted: {bool(truncation.get('delta_evidence_omitted_content'))}",
            f"- Realtime delta events with skipped content: {safe_int(truncation.get('delta_evidence_truncated_events'), 0)}",
            f"- Steps with truncated child refs: {safe_int(truncation.get('child_ref_steps'), 0)}",
            "",
            "## Commands",
        ]
    command_count = 0
    for key in ("checkout", "setup", "run", "collect", "report"):
        command = str(commands.get(key) or "").strip()
        if command:
            command_count += 1
            lines.append(f"- {key}: `{command}`")
    if command_count == 0:
        lines.append("- No package commands were recorded.")
    lines.extend(["", "## Triage"])
    if failed_steps:
        lines.append("- Failed or stopped steps:")
        for step in failed_steps[:8]:
            label = str(step.get("node_kind") or step.get("node_id") or "step").strip()
            status = str(step.get("status") or "").strip()
            error = str(step.get("error") or "").strip()
            lines.append(f"  - #{safe_int(step.get('index'), 0) + 1} {label}: {status}{' - ' + error if error else ''}")
    else:
        lines.append("- No failed, blocked, or stopped steps were recorded.")
    lines.append("- Use `replay.timeline` for ordered step history, `replay.event_timeline` for persisted runtime events, `replay.delta_evidence` for summary-only realtime stream coverage, and `logs[].tail` for cached job output.")
    return "\n".join(lines).strip() + "\n"
