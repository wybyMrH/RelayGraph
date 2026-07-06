"""Execution run comparison payload helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .run_replay import workspace_execution_run_replay_payload


def workspace_execution_run_compare_payload(
    workspace: dict[str, Any],
    base_run: dict[str, Any],
    target_run: dict[str, Any],
    *,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base = workspace_execution_run_replay_payload(workspace, base_run, jobs=jobs)
    target = workspace_execution_run_replay_payload(workspace, target_run, jobs=jobs)

    def metric(replay: dict[str, Any]) -> dict[str, Any]:
        timeline = replay.get("timeline") if isinstance(replay.get("timeline"), list) else []
        linked_runs = replay.get("linked_runs") if isinstance(replay.get("linked_runs"), list) else []
        linked_timeline = [
            step
            for item in linked_runs
            if isinstance(item, dict) and isinstance(item.get("timeline"), list)
            for step in item.get("timeline", [])
        ]
        all_timeline = [*timeline, *linked_timeline]
        linked_jobs = replay.get("linked_jobs") if isinstance(replay.get("linked_jobs"), list) else []
        delivery = replay.get("delivery_closure") if isinstance(replay.get("delivery_closure"), dict) else {}
        node_keys = [
            (
                f"{str(step.get('run_id') or '').strip()}:"
                f"{str(step.get('node_kind') or '').strip()}:"
                f"{str(step.get('node_id') or '').strip()}"
            )
            for step in all_timeline
            if isinstance(step, dict)
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
        return {
            "run_id": str(replay.get("run", {}).get("id") if isinstance(replay.get("run"), dict) else "").strip(),
            "status": str(replay.get("run", {}).get("status") if isinstance(replay.get("run"), dict) else "").strip(),
            "package_id": str(replay.get("run", {}).get("package_id") if isinstance(replay.get("run"), dict) else "").strip(),
            "step_count": len(all_timeline),
            "linked_run_count": len(linked_runs),
            "job_count": len(linked_jobs),
            "agent_count": len(replay.get("agent_execution_ids") if isinstance(replay.get("agent_execution_ids"), list) else []),
            "failed_step_count": sum(1 for step in all_timeline if isinstance(step, dict) and str(step.get("status") or "") in {"failed", "blocked", "stopped"}),
            "artifact_count": sum(safe_int(step.get("artifact_count"), 0) for step in all_timeline if isinstance(step, dict)),
            "trace_event_count": sum(safe_int(step.get("trace_event_count"), 0) for step in all_timeline if isinstance(step, dict)),
            "delivery_status": str(delivery.get("status") or "").strip(),
            "node_keys": node_keys,
            "status_counts": status_counts,
            "executor_counts": executor_counts,
        }

    base_metric = metric(base)
    target_metric = metric(target)
    base_nodes = set(base_metric["node_keys"])
    target_nodes = set(target_metric["node_keys"])

    numeric_keys = (
        "step_count",
        "linked_run_count",
        "job_count",
        "agent_count",
        "failed_step_count",
        "artifact_count",
        "trace_event_count",
    )
    metric_delta = {
        key: safe_int(target_metric.get(key), 0) - safe_int(base_metric.get(key), 0)
        for key in numeric_keys
    }
    changes = []
    for key, label in (
        ("status", "运行状态"),
        ("package_id", "执行包"),
        ("delivery_status", "交付闭环"),
    ):
        if str(base_metric.get(key) or "") != str(target_metric.get(key) or ""):
            changes.append(
                {
                    "field": key,
                    "label": label,
                    "base": str(base_metric.get(key) or ""),
                    "target": str(target_metric.get(key) or ""),
                }
            )
    for key, delta in metric_delta.items():
        if delta:
            changes.append(
                {
                    "field": key,
                    "label": key,
                    "base": safe_int(base_metric.get(key), 0),
                    "target": safe_int(target_metric.get(key), 0),
                    "delta": delta,
                }
            )

    return {
        "schema": "relaygraph.run.compare.v1",
        "exported_at": now_iso(),
        "workspace": copy.deepcopy(base.get("workspace") if isinstance(base.get("workspace"), dict) else {}),
        "base": {
            "run": copy.deepcopy(base.get("run") if isinstance(base.get("run"), dict) else {}),
            "metrics": base_metric,
        },
        "target": {
            "run": copy.deepcopy(target.get("run") if isinstance(target.get("run"), dict) else {}),
            "metrics": target_metric,
        },
        "diff": {
            "metric_delta": metric_delta,
            "added_nodes": sorted(target_nodes - base_nodes),
            "removed_nodes": sorted(base_nodes - target_nodes),
            "common_node_count": len(base_nodes & target_nodes),
            "changes": changes,
        },
    }
