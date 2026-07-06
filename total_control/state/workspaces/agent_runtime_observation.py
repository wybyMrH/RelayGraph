"""Workspace Agent runtime job observation helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .agent_runtime_safety import redact_runtime_observation_text


def workspace_tool_observe_options(args: dict[str, Any]) -> dict[str, Any]:
    data = args if isinstance(args, dict) else {}
    requested = bool(
        data.get("wait_for_completion")
        or data.get("wait_until_complete")
        or data.get("observe")
        or data.get("observe_job")
    )
    seconds = safe_float(data.get("observe_seconds"), 0.0)
    if seconds <= 0:
        seconds = safe_float(data.get("wait_timeout_seconds"), 0.0)
    if seconds <= 0 and requested:
        seconds = 30.0
    seconds = min(max(seconds, 0.0), 300.0)
    poll_interval = safe_float(data.get("poll_interval_seconds"), 0.5)
    poll_interval = min(max(poll_interval, 0.05), 5.0)
    log_tail_lines = safe_int(data.get("log_tail_lines"), 120)
    log_tail_lines = min(max(log_tail_lines, 0), 2000)
    return {
        "enabled": requested or seconds > 0,
        "seconds": seconds,
        "poll_interval": poll_interval,
        "log_tail_lines": log_tail_lines,
    }


def workspace_tool_job_snapshot(state: Any, job_id: str) -> dict[str, Any] | None:
    target = str(job_id or "").strip()
    if not target:
        return None
    with state.lock:
        job = next((item for item in state.jobs if str(item.get("id") or "").strip() == target), None)
        return copy.deepcopy(job) if isinstance(job, dict) else None


def workspace_tool_run_snapshot(state: Any, workspace_id: str, run_id: str) -> dict[str, Any] | None:
    workspace_id = str(workspace_id or "").strip()
    run_id = str(run_id or "").strip()
    if not workspace_id or not run_id:
        return None
    with state.lock:
        workspace = state.workspace_by_id(workspace_id)
        runs = workspace.get("runs") if isinstance(workspace, dict) and isinstance(workspace.get("runs"), list) else []
        run = next((item for item in runs if str(item.get("id") or "").strip() == run_id), None)
        return copy.deepcopy(run) if isinstance(run, dict) else None


def observe_workspace_tool_job(
    state: Any,
    *,
    workspace_id: str,
    job_id: str,
    run_id: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    workspace_id = str(workspace_id or "").strip()
    job_id = str(job_id or "").strip()
    run_id = str(run_id or "").strip()
    seconds = safe_float(options.get("seconds"), 0.0)
    poll_interval = safe_float(options.get("poll_interval"), 0.5)
    log_tail_lines = safe_int(options.get("log_tail_lines"), 120)
    terminal_statuses = {"done", "failed", "stopped"}
    started = time.monotonic()
    deadline = started + seconds
    timed_out = False
    last_job = workspace_tool_job_snapshot(state, job_id)
    monitored_once = False

    while True:
        if last_job and str(last_job.get("status") or "").strip() in terminal_statuses:
            break
        if monitored_once and time.monotonic() > deadline:
            timed_out = True
            break
        try:
            state.refresh_status()
            state.monitor_jobs()
            monitored_once = True
        except Exception as exc:  # noqa: BLE001 - observation reports scheduler issues in-band.
            return {
                "observed": True,
                "status": "error",
                "runtime_status": "error",
                "job_status": str((last_job or {}).get("status") or "").strip(),
                "error": f"job observation failed: {exc}",
                "observe_seconds": round(time.monotonic() - started, 3),
            }
        last_job = workspace_tool_job_snapshot(state, job_id)
        if last_job and str(last_job.get("status") or "").strip() in terminal_statuses:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        wait_for = min(max(poll_interval, 0.05), remaining)
        stop_event = getattr(state, "stop_event", None)
        if stop_event is not None and stop_event.wait(wait_for):
            timed_out = True
            break
        if stop_event is None:
            time.sleep(wait_for)

    if workspace_id:
        state.sync_workspace_execution_runs_from_jobs(workspace_id)
    last_job = workspace_tool_job_snapshot(state, job_id) or last_job or {}
    job_status = str(last_job.get("status") or "").strip()
    result_status = job_status if job_status in terminal_statuses else "timeout" if timed_out else job_status or "unknown"
    log_tail = ""
    log_error = ""
    if log_tail_lines > 0 and last_job:
        try:
            if hasattr(state, "job_log_payload"):
                payload = state.job_log_payload(last_job, lines=log_tail_lines)
                log_tail = str(payload.get("log") or "")
            else:
                log_tail = str(state.tail_log(last_job, lines=log_tail_lines))
        except Exception as exc:  # noqa: BLE001 - log tail should not hide job status.
            log_error = str(exc)
    if len(log_tail) > 12000:
        log_tail = log_tail[-12000:]
    observed_run = workspace_tool_run_snapshot(state, workspace_id, run_id)
    payload: dict[str, Any] = {
        "observed": True,
        "status": result_status,
        "runtime_status": result_status,
        "job_status": job_status,
        "timed_out": bool(timed_out),
        "observe_seconds": round(time.monotonic() - started, 3),
        "job": public_job_payload(last_job) if isinstance(last_job, dict) else {},
        "job_id": job_id,
    }
    if run_id:
        payload["run_id"] = run_id
    if observed_run:
        payload["run"] = observed_run
    if log_tail:
        redacted_tail = redact_runtime_observation_text(log_tail)
        payload["log_tail"] = redacted_tail
        payload["log_line_count"] = len(redacted_tail.splitlines())
    if log_error:
        payload["log_error"] = log_error
    if result_status in {"failed", "stopped"}:
        payload["error"] = str(last_job.get("error") or f"job {result_status}").strip()
    elif result_status == "timeout":
        payload["message"] = "观察窗口已结束，任务仍在队列或运行中；后续状态会继续通过 run/job 事件同步。"
    elif result_status == "done":
        payload["message"] = "任务已完成，观察结果和日志尾部已返回。"
    return payload
