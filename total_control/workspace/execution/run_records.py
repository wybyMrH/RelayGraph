"""Execution run record normalization, filtering, and snapshots."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .run_delivery import workspace_execution_run_delivery_closure
from .run_events import normalize_workspace_run_delta_evidence, normalize_workspace_run_events
from .run_refs import workspace_run_step_agent_execution_ids, workspace_run_step_job_ids
from .run_steps import normalize_workspace_run_step


def make_workspace_execution_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]


def make_agent_execution_id() -> str:
    return "aex-" + uuid.uuid4().hex[:12]


def derive_workspace_execution_run_status(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "pending"
    statuses = [str(step.get("status") or "").strip() for step in steps]
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "stopped" for status in statuses):
        return "stopped"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "running" for status in statuses):
        return "running"
    if any(status == "queued" for status in statuses):
        return "queued"
    if all(status == "done" for status in statuses):
        return "done"
    return "pending"


def derive_workspace_execution_run_progress(steps: list[dict[str, Any]]) -> dict[str, int]:
    total = len(steps)
    done = sum(1 for step in steps if str(step.get("status") or "") == "done")
    stopped = sum(1 for step in steps if str(step.get("status") or "") == "stopped")
    failed = sum(1 for step in steps if str(step.get("status") or "") in {"failed", "blocked", "stopped"})
    running = sum(1 for step in steps if str(step.get("status") or "") == "running")
    queued = sum(1 for step in steps if str(step.get("status") or "") == "queued")
    percent = int((done / total) * 100) if total else 0
    return {
        "total": total,
        "done": done,
        "failed": failed,
        "stopped": stopped,
        "running": running,
        "queued": queued,
        "percent": percent,
    }


def normalize_workspace_execution_run(
    value: Any,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing if isinstance(existing, dict) else {}
    payload = value if isinstance(value, dict) else {}
    run_id = str(payload.get("id") or current.get("id") or "").strip() or make_workspace_execution_run_id()
    workspace_id = str(payload.get("workspace_id") or current.get("workspace_id") or "").strip()
    kind = str(payload.get("kind") or current.get("kind") or "node").strip() or "node"
    if kind not in WORKSPACE_EXECUTION_RUN_KINDS:
        kind = "node"
    raw_steps = payload.get("steps") if isinstance(payload.get("steps"), list) else current.get("steps")
    existing_steps = current.get("steps") if isinstance(current.get("steps"), list) else []
    steps = [
        normalize_workspace_run_step(
            item,
            existing=existing_steps[index] if index < len(existing_steps) and isinstance(existing_steps[index], dict) else None,
        )
        for index, item in enumerate(raw_steps or [])
        if isinstance(item, dict)
    ]
    steps.sort(key=lambda item: safe_int(item.get("index"), 0))
    status = str(payload.get("status") or current.get("status") or derive_workspace_execution_run_status(steps)).strip()
    progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else current.get("progress")
    if not isinstance(progress, dict):
        progress = derive_workspace_execution_run_progress(steps)
    else:
        progress = derive_workspace_execution_run_progress(steps)
    package_snapshot = payload.get("package_snapshot") if isinstance(payload.get("package_snapshot"), dict) else {}
    if not package_snapshot and isinstance(current.get("package_snapshot"), dict):
        package_snapshot = current.get("package_snapshot") or {}
    package_id = ""
    if isinstance(package_snapshot, dict):
        package_id = str(package_snapshot.get("package_id") or "").strip()
        if not package_id:
            manifest = package_snapshot.get("package_manifest")
            if isinstance(manifest, dict):
                package_id = str(manifest.get("package_id") or "").strip()
    if not package_id:
        package_id = str(payload.get("package_id") or current.get("package_id") or "").strip()
    if isinstance(package_snapshot, dict) and package_snapshot:
        package_snapshot = {
            **package_snapshot,
            "delivery_closure": workspace_execution_run_delivery_closure(package_snapshot, steps),
        }
    raw_events = payload.get("events") if isinstance(payload.get("events"), list) else current.get("events")
    events = normalize_workspace_run_events(raw_events)
    delta_evidence = normalize_workspace_run_delta_evidence(
        payload.get("delta_evidence") if isinstance(payload.get("delta_evidence"), dict) else current.get("delta_evidence")
    )
    created_at = str(payload.get("created_at") or current.get("created_at") or now_iso()).strip() or now_iso()
    return {
        "id": run_id,
        "workspace_id": workspace_id,
        "kind": kind,
        "status": status,
        "trigger": str(payload.get("trigger") or current.get("trigger") or "user").strip() or "user",
        "summary": str(payload.get("summary") or current.get("summary") or "").strip(),
        "steps": steps,
        "progress": progress,
        "package_snapshot": copy.deepcopy(package_snapshot) if isinstance(package_snapshot, dict) else {},
        "package_id": package_id,
        "events": events,
        "delta_evidence": delta_evidence,
        "created_at": created_at,
        "updated_at": str(payload.get("updated_at") or current.get("updated_at") or created_at).strip() or created_at,
    }


def normalize_workspace_execution_runs(
    value: Any,
    *,
    existing: list[dict[str, Any]] | None = None,
    limit: int = WORKSPACE_EXECUTION_RUN_MAX,
) -> list[dict[str, Any]]:
    raw_items = value if isinstance(value, list) else []
    existing_items = existing if isinstance(existing, list) else []
    existing_by_id = {
        str(item.get("id") or "").strip(): item
        for item in existing_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    runs = [
        normalize_workspace_execution_run(
            item,
            existing=existing_by_id.get(str(item.get("id") or "").strip()),
        )
        for item in raw_items
        if isinstance(item, dict)
    ]
    runs.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
    return runs[: max(limit, 1)]


def workspace_execution_run_sort_key(run: dict[str, Any]) -> tuple[str, str]:
    return (str(run.get("created_at") or ""), str(run.get("id") or ""))


def filter_workspace_execution_runs(
    runs: list[dict[str, Any]],
    *,
    status: str = "",
    node_kind: str = "",
    job_id: str = "",
    agent_execution_id: str = "",
    created_after: str = "",
    created_before: str = "",
) -> list[dict[str, Any]]:
    # 按状态、节点类型、任务、Agent 执行 id 或时间范围过滤运行记录。
    filtered = [run for run in runs if isinstance(run, dict)]
    status_filter = str(status or "").strip().lower()
    if status_filter:
        filtered = [run for run in filtered if str(run.get("status") or "").strip().lower() == status_filter]
    after_ts = parse_iso_timestamp(created_after)
    before_ts = parse_iso_timestamp(created_before)
    if after_ts or before_ts:
        def run_ts(run: dict[str, Any]) -> float:
            return (
                parse_iso_timestamp(run.get("created_at"))
                or parse_iso_timestamp(run.get("started_at"))
                or parse_iso_timestamp(run.get("updated_at"))
                or parse_iso_timestamp(run.get("completed_at"))
            )

        if after_ts:
            filtered = [run for run in filtered if run_ts(run) >= after_ts]
        if before_ts:
            filtered = [run for run in filtered if run_ts(run) <= before_ts]
    node_kind_filter = str(node_kind or "").strip()
    if node_kind_filter:
        filtered = [
            run for run in filtered
            if any(
                isinstance(step, dict) and str(step.get("node_kind") or "").strip() == node_kind_filter
                for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            )
        ]
    job_id_filter = str(job_id or "").strip()
    if job_id_filter:
        job_id_filter_lower = job_id_filter.lower()
        filtered = [
            run for run in filtered
            if any(
                isinstance(step, dict)
                and any(job_id_filter_lower in item.lower() for item in workspace_run_step_job_ids(step))
                for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            )
        ]
    agent_filter = str(agent_execution_id or "").strip()
    if agent_filter:
        agent_filter_lower = agent_filter.lower()
        filtered = [
            run for run in filtered
            if any(
                isinstance(step, dict)
                and any(agent_filter_lower in item.lower() for item in workspace_run_step_agent_execution_ids(step))
                for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            )
        ]
    return filtered


def workspace_execution_run_snapshot(run: dict[str, Any]) -> tuple[str, tuple[tuple[str, str], ...]]:
    steps = run.get("steps") if isinstance(run.get("steps"), list) else []
    return (
        str(run.get("status") or ""),
        tuple(
            (
                str(step.get("status") or ""),
                str(step.get("error") or ""),
                str(step.get("artifact_count") or ""),
                json.dumps(step.get("artifacts") if isinstance(step.get("artifacts"), list) else [], sort_keys=True, ensure_ascii=True),
                json.dumps(step.get("resources") if isinstance(step.get("resources"), dict) else {}, sort_keys=True, ensure_ascii=True),
                json.dumps(step.get("child_job_ids") if isinstance(step.get("child_job_ids"), list) else [], sort_keys=True, ensure_ascii=True),
                json.dumps(step.get("child_run_ids") if isinstance(step.get("child_run_ids"), list) else [], sort_keys=True, ensure_ascii=True),
                str(step.get("runtime_control") or ""),
                str(step.get("runtime_status") or ""),
                str(step.get("runtime_side_effect") or ""),
                str(step.get("started_at") or ""),
                str(step.get("completed_at") or ""),
            )
            for step in steps
            if isinstance(step, dict)
        ),
    )
