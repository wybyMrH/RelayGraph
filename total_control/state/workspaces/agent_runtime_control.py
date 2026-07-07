"""Workspace Agent runtime control helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403


def bind_workspace_tool_gpu_allocation(
    state: Any,
    workspace: dict[str, Any],
    arguments: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    _ = state
    args = arguments if isinstance(arguments, dict) else {}
    selected = args.get("selected") if isinstance(args.get("selected"), dict) else None
    if not selected and context:
        min_free_mib = safe_int(args.get("min_free_mib"), 0)
        server_id = str(args.get("server_id") or "").strip()
        selected = next((item for item in context.gpu_candidates(min_free_mib=min_free_mib, server_id=server_id) if item.get("eligible")), None)
    if not selected:
        return {
            "status": "blocked",
            "tool": "gpu.allocate",
            "controlled": True,
            "error": "没有满足条件的 GPU 候选。",
        }
    server_id = str(selected.get("server_id") or "").strip()
    gpu_index = str(selected.get("gpu_index") if selected.get("gpu_index") is not None else "").strip()
    min_free_mib = safe_int(args.get("min_free_mib"), 0)
    min_free_gib = round(min_free_mib / 1024, 2) if min_free_mib else 0
    return {
        "status": "planned",
        "tool": "gpu.allocate",
        "controlled": True,
        "runtime_control": "scheduler_plan",
        "runtime_side_effect": "none",
        "plan_only": True,
        "selected": copy.deepcopy(selected),
        "recommended_binding": {
            "server_id": server_id,
            "gpu_policy": "auto",
            "gpu_index": gpu_index,
            "min_free_memory_gib": str(min_free_gib) if min_free_gib else "",
        },
        "persisted": False,
        "message": "已生成 GPU 候选和绑定建议；未修改配置。需要持久化时请在配置中心应用调度目标，实际执行仍走 job 队列。",
    }


def control_workspace_tool_job(
    state: Any,
    workspace: dict[str, Any],
    tool_id: str,
    arguments: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    _ = context
    workspace_id = str(workspace.get("id") or "").strip()
    tool = str(tool_id or "").strip()
    args = arguments if isinstance(arguments, dict) else {}
    if not workspace_id:
        return {"status": "error", "tool": tool, "error": "workspace_id is required"}

    requested_job_id = str(args.get("job_id") or args.get("id") or "").strip()
    with state.lock:
        workspace_jobs = []
        for job in state.jobs:
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            if str(metadata.get("workspace_id") or "").strip() == workspace_id:
                workspace_jobs.append(job)
        if not requested_job_id and bool(args.get("latest")) and workspace_jobs:
            workspace_jobs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
            requested_job_id = str(workspace_jobs[0].get("id") or "").strip()
        job = next((item for item in workspace_jobs if str(item.get("id") or "").strip() == requested_job_id), None)

    if not requested_job_id:
        return {"status": "blocked", "tool": tool, "controlled": True, "error": "job_id is required"}
    if not job:
        return {
            "status": "blocked",
            "tool": tool,
            "controlled": True,
            "error": "job not found in this workspace",
            "job_id": requested_job_id,
        }

    if tool == "job.stop":
        current_status = str(job.get("status") or "").strip()
        if current_status in {"done", "failed", "stopped"}:
            return {
                "status": "noop",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_control",
                "job": public_job_payload(job),
                "job_id": requested_job_id,
                "message": f"任务已是 {current_status}，无需停止。",
            }
        stopped = state.stop_job(requested_job_id)
        return {
            "status": "stopped",
            "tool": tool,
            "controlled": True,
            "runtime_control": "workspace_job_control",
            "job": public_job_payload(stopped),
            "job_id": requested_job_id,
            "message": "任务已通过受控 job 控制停止。",
        }

    if tool == "job.reorder":
        direction = str(args.get("direction") or args.get("move") or "top").strip().lower()
        try:
            result = state.reorder_job(requested_job_id, direction)
        except ValueError as exc:
            return {
                "status": "blocked",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_control",
                "job_id": requested_job_id,
                "error": str(exc),
            }
        changed_job = result.get("job") if isinstance(result.get("job"), dict) else job
        state.publish_job_event(changed_job, "job.updated")
        return {
            "status": "reordered",
            "tool": tool,
            "controlled": True,
            "runtime_control": "workspace_job_control",
            "job": public_job_payload(changed_job),
            "job_id": requested_job_id,
            "queue_position": result.get("queue_position"),
            "total_waiting": result.get("total_waiting"),
            "message": "任务队列顺序已通过受控 job 控制更新。",
        }

    return {"status": "error", "tool": tool, "controlled": True, "error": "unsupported job control tool"}
