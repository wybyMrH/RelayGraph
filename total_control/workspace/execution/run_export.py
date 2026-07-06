"""Execution run export manifest helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .log_parser import workspace_dedupe_artifacts
from .paths import workspace_job_cached_log_tail_payload
from .run_refs import (
    WORKSPACE_LINKED_RUN_CLOSURE_MAX,
    WORKSPACE_RUN_CHILD_REF_MAX,
    workspace_execution_run_linked_runs,
    workspace_jobs_for_run,
    workspace_run_step_job_ids,
)
from .run_replay import workspace_execution_run_replay_payload, workspace_execution_run_timeline


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


def workspace_execution_run_export_payload(
    workspace: dict[str, Any],
    run: dict[str, Any],
    *,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    replay = workspace_execution_run_replay_payload(workspace, run, jobs=jobs)
    timeline = replay.get("timeline") if isinstance(replay.get("timeline"), list) else []
    event_timeline = replay.get("event_timeline") if isinstance(replay.get("event_timeline"), list) else []
    workspace_payload = replay.get("workspace") if isinstance(replay.get("workspace"), dict) else {}
    workspace_id = str(workspace_payload.get("id") or "").strip()
    linked_runs = workspace_execution_run_linked_runs(workspace, run)
    source_runs = [run, *linked_runs]
    job_index = workspace_jobs_for_run(workspace_id, run, jobs, linked_runs=linked_runs)
    log_items: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    seen_log_job_ids: set[str] = set()
    for source_run in source_runs:
        source_run_id = str(source_run.get("id") or "").strip()
        source_steps = [step for step in (source_run.get("steps") if isinstance(source_run.get("steps"), list) else []) if isinstance(step, dict)]
        source_timeline = workspace_execution_run_timeline(source_run)
        for step_index, step in enumerate(source_timeline):
            if not isinstance(step, dict):
                continue
            source_step = next(
                (
                    item for item in source_steps
                    if safe_int(item.get("index"), -1) == safe_int(step.get("index"), -2)
                    and str(item.get("node_id") or "").strip() == str(step.get("node_id") or "").strip()
                ),
                source_steps[step_index] if step_index < len(source_steps) else {},
            )
            for job_id in workspace_run_step_job_ids(step):
                job = job_index.get(job_id)
                if not job or job_id in seen_log_job_ids:
                    continue
                log_payload = workspace_job_cached_log_tail_payload(
                    job,
                    max_lines=80,
                    max_bytes=24000,
                    tail_chars=12000,
                )
                log_text = str(log_payload.get("tail") or "")
                if not log_text:
                    continue
                seen_log_job_ids.add(job_id)
                tail_source = str(log_payload.get("tail_source") or "snapshot").strip() or "snapshot"
                display_log_path = str(log_payload.get("display_log_path") or "").strip()
                if not display_log_path:
                    display_log_path = runtime_log_display_path(log_payload.get("log_path") or job.get("log_path"))
                log_items.append(
                    {
                        "run_id": source_run_id,
                        "job_id": job_id,
                        "node_id": str(step.get("node_id") or "").strip(),
                        "node_kind": str(step.get("node_kind") or "").strip(),
                        "status": str(job.get("status") or step.get("status") or "").strip(),
                        "log_path": display_log_path,
                        "display_log_path": display_log_path,
                        "remote_log_path": remote_runtime_log_display_path(log_payload.get("remote_log_path") or job.get("remote_log_path")),
                        "tail_source": tail_source,
                        "snapshot_captured_at": str(log_payload.get("snapshot_captured_at") or "").strip() if tail_source == "snapshot" else "",
                        "file_size": safe_int(log_payload.get("file_size"), 0),
                        "read_bytes": safe_int(log_payload.get("read_bytes"), 0),
                        "tail_bytes": safe_int(log_payload.get("tail_bytes"), len(log_text.encode("utf-8", errors="replace"))),
                        "skipped_bytes": safe_int(log_payload.get("skipped_bytes"), 0),
                        "line_count": safe_int(log_payload.get("line_count"), len(log_text.splitlines())),
                        "truncated": bool(log_payload.get("truncated")),
                        "truncation_reasons": list(log_payload.get("truncation_reasons") if isinstance(log_payload.get("truncation_reasons"), list) else []),
                        "tail": log_text,
                    }
                )
            for artifact in source_step.get("artifacts") if isinstance(source_step.get("artifacts"), list) else []:
                if not isinstance(artifact, dict):
                    continue
                item = copy.deepcopy(artifact)
                item.setdefault("run_id", source_run_id)
                item.setdefault("node_id", str(step.get("node_id") or "").strip())
                item.setdefault("node_kind", str(step.get("node_kind") or "").strip())
                artifacts.append(item)
                artifact_type = str(item.get("type") or "").strip()
                label = str(item.get("label") or "").strip().lower()
                if artifact_type == "report" or label in {"report", "eval_report", "evaluation_report"}:
                    reports.append(copy.deepcopy(item))

        source_package = source_run.get("package_snapshot") if isinstance(source_run.get("package_snapshot"), dict) else {}
        source_delivery = source_package.get("delivery_closure") if isinstance(source_package.get("delivery_closure"), dict) else {}
        report_payload = source_delivery.get("report") if isinstance(source_delivery.get("report"), dict) else {}
        for report in report_payload.get("artifacts") if isinstance(report_payload.get("artifacts"), list) else []:
            if isinstance(report, dict):
                item = copy.deepcopy(report)
                item.setdefault("run_id", source_run_id)
                reports.append(item)

    artifacts = workspace_dedupe_artifacts(artifacts)[:48]
    reports = reports[:12]
    log_items = log_items[:12]
    manifest = workspace_run_export_manifest(replay, logs=log_items, artifacts=artifacts, reports=reports)
    readme = workspace_run_export_readme(manifest)
    run_payload = replay.get("run") if isinstance(replay.get("run"), dict) else {}
    delivery = replay.get("delivery_closure") if isinstance(replay.get("delivery_closure"), dict) else {}
    run_id = str(run_payload.get("id") or "").strip()
    package_id = str(run_payload.get("package_id") or "").strip()
    filename_bits = [workspace_id or "workspace", run_id or "run", package_id or "export"]
    filename = "relaygraph-run-" + "-".join(safe_id(bit) for bit in filename_bits if bit) + ".json"
    return {
        "schema": "relaygraph.run.export.v1",
        "exported_at": now_iso(),
        "filename": filename,
        "workspace": copy.deepcopy(workspace_payload),
        "run": copy.deepcopy(run_payload),
        "summary": {
            "step_count": len(timeline),
            "linked_run_count": len(linked_runs),
            "linked_step_count": sum(
                len(workspace_execution_run_timeline(linked_run))
                for linked_run in linked_runs
                if isinstance(linked_run, dict)
            ),
            "linked_job_count": len(replay.get("linked_jobs") if isinstance(replay.get("linked_jobs"), list) else []),
            "agent_execution_count": len(replay.get("agent_execution_ids") if isinstance(replay.get("agent_execution_ids"), list) else []),
            "event_count": len(event_timeline),
            "artifact_count": len(artifacts),
            "report_count": len(reports),
            "log_count": len(log_items),
            "delivery_status": str(delivery.get("status") or "").strip(),
        },
        "manifest": manifest,
        "readme_markdown": readme,
        "replay": replay,
        "logs": log_items,
        "artifacts": artifacts,
        "reports": reports,
    }
