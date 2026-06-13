"""Execution — trace helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .log_parser import (
    parse_workspace_artifacts_from_log,
    parse_workspace_metrics_from_log,
    parse_workspace_resources_from_log,
    workspace_dedupe_artifacts,
)
from .jobs import workspace_job_sort_key
from .paths import (
    compact_workspace_command,
    workspace_config_values,
    workspace_job_cached_log_tail,
    workspace_path_probe,
)

def workspace_node_artifacts(
    workspace: dict[str, Any],
    node: dict[str, Any],
    latest_job: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    kind = str(node.get("kind") or "").strip()
    workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
    artifacts: list[dict[str, Any]] = []

    if workspace_dir and kind in {"repo.clone", "path.resolve", "repo.inspect", "env.infer", "env.prepare", "run.command", "artifact.collect"}:
        artifacts.append(workspace_path_probe(workspace_dir, label="工作目录", source="workspace"))

    if kind == "path.resolve":
        for value in workspace_config_values(config.get("data_roots"))[:12]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="数据根目录", source="path.resolve"))
        for value in workspace_config_values(config.get("output_roots") or "runs\noutputs\ncheckpoints\nlogs")[:12]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="输出目录", source="path.resolve"))
    elif kind == "dataset.find":
        for value in workspace_config_values(config.get("dataset_hints"))[:12]:
            artifacts.append(workspace_path_probe(value, label="数据集线索", source="dataset.find"))
        for value in workspace_config_values(config.get("data_roots"))[:12]:
            artifacts.append(workspace_path_probe(value, label="数据根目录", source="dataset.find"))
        query = str(config.get("query") or workspace.get("brief") or "").strip()
        if query:
            artifacts.append(
                {
                    "label": "检索词",
                    "path": query,
                    "source": "dataset.find",
                    "status": "planned",
                }
            )
    elif kind == "env.infer":
        for value in workspace_config_values(config.get("manifest_paths") or "requirements.txt, pyproject.toml, environment.yml, setup.py")[:12]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="环境清单", source="env.infer"))
    elif kind == "artifact.collect":
        for value in workspace_config_values(config.get("artifact_paths") or "runs\noutputs\ncheckpoints\nlogs")[:16]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="产物路径", source="artifact.collect"))
        for value in workspace_config_values(config.get("metric_paths"))[:16]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="指标路径", source="artifact.collect"))
    elif kind == "eval.report":
        for value in workspace_config_values(config.get("metric_paths"))[:16]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="指标路径", source="eval.report"))

    if latest_job:
        log_path = str(latest_job.get("log_path") or "").strip()
        if log_path:
            artifacts.append(workspace_path_probe(log_path, label="最近日志", source="job"))
        remote_log_path = str(latest_job.get("remote_log_path") or "").strip()
        if remote_log_path:
            artifacts.append(
                {
                    "label": "远端日志",
                    "path": remote_log_path,
                    "source": "job",
                    "status": "expected",
                }
            )
        log_text = workspace_job_cached_log_tail(latest_job)
        if log_text:
            artifacts.extend(parse_workspace_artifacts_from_log(kind, log_text))

    return workspace_dedupe_artifacts(artifacts)

def workspace_node_resources(
    workspace: dict[str, Any],
    node: dict[str, Any],
    latest_job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    metadata = latest_job.get("metadata") if latest_job and isinstance(latest_job.get("metadata"), dict) else {}
    kind = str(node.get("kind") or "").strip()
    gpu_policy = str(config.get("gpu_policy") or ("none" if kind in {"repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "env.prepare", "artifact.collect", "eval.report"} else "auto")).strip().lower() or "auto"
    if latest_job:
        gpu_value = latest_job.get("gpu_index")
    elif gpu_policy in {"cpu", "none", "no_gpu"}:
        gpu_value = "none"
    else:
        gpu_value = str(config.get("gpu_index") or "auto").strip() or "auto"
    if gpu_value is None or not str(gpu_value).strip():
        gpu_value = "auto"
    resources = {
        "server_id": str((latest_job or {}).get("server_id") or config.get("server_id") or "auto").strip() or "auto",
        "requested_server_id": str((latest_job or {}).get("requested_server_id") or config.get("server_id") or "auto").strip() or "auto",
        "gpu_index": str(gpu_value),
        "gpu_policy": gpu_policy,
        "execution_mode": str(metadata.get("execution_mode") or ("gpu" if kind in {"gpu.allocate", "run.command"} and gpu_policy not in {"cpu", "none", "no_gpu"} else "cpu")),
        "cwd": str((latest_job or {}).get("cwd") or config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip(),
        "env_name": str((latest_job or {}).get("env_name") or config.get("env_name") or workspace_env.get("name") or "").strip(),
        "depends_on": [str(item) for item in ((latest_job or {}).get("target_job_ids") or []) if str(item).strip()],
        "wait_for_idle": bool((latest_job or {}).get("wait_for_idle", kind in WORKSPACE_EXECUTABLE_NODE_KINDS)),
    }
    runtime_binding = metadata.get("runtime_binding") if isinstance(metadata.get("runtime_binding"), dict) else {}
    if runtime_binding:
        resources["runtime_binding"] = copy.deepcopy(runtime_binding)
        for key in ("server_id", "gpu_index", "gpu_policy", "execution_mode", "cwd", "env_name", "wait_for_idle"):
            if key in runtime_binding and runtime_binding.get(key) not in (None, ""):
                resources[key] = runtime_binding[key]
    scheduler_binding = metadata.get("scheduler_binding") if isinstance(metadata.get("scheduler_binding"), dict) else {}
    if scheduler_binding:
        resources["scheduler_binding"] = copy.deepcopy(scheduler_binding)
        resources["scheduler_status"] = str(scheduler_binding.get("status") or "").strip()
        resources["scheduler_summary"] = str(scheduler_binding.get("summary") or "").strip()
        resources["scheduler_reasons"] = copy.deepcopy(
            scheduler_binding.get("reasons") if isinstance(scheduler_binding.get("reasons"), list) else []
        )
    log_text = workspace_job_cached_log_tail(latest_job)
    if log_text:
        resources.update(parse_workspace_resources_from_log(kind, log_text))
        metrics = parse_workspace_metrics_from_log(kind, log_text)
        if metrics:
            resources["metrics"] = metrics
    return resources

def workspace_node_trace(
    node: dict[str, Any],
    bound_jobs: list[dict[str, Any]],
    state: str,
) -> list[dict[str, Any]]:
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    trace: list[dict[str, Any]] = [
        {
            "status": "planned",
            "label": "节点已编排",
            "detail": f"{str(node.get('kind') or '').strip()} · {str(handler.get('name') or handler.get('agent_id') or '未指派 Agent').strip()}",
            "at": str(node.get("updated_at") or node.get("created_at") or "").strip(),
        }
    ]
    if not bound_jobs:
        if state == "pending":
            trace.append(
                {
                    "status": "pending",
                    "label": "等待执行",
                    "detail": "还没有提交到调度队列。",
                    "at": "",
                }
            )
        return trace

    for job in sorted(bound_jobs, key=workspace_job_sort_key):
        job_id = str(job.get("id") or "").strip()
        created_at = str(job.get("created_at") or "").strip()
        trace.append(
            {
                "status": "queued",
                "label": "已提交队列",
                "detail": f"{job_id} · {compact_workspace_command(job.get('command_display') or job.get('command'))}",
                "at": created_at,
                "job_id": job_id,
            }
        )
        dependency_ids = [str(item).strip() for item in job.get("target_job_ids", []) if str(item).strip()]
        if dependency_ids:
            trace.append(
                {
                    "status": "blocked" if str(job.get("status") or "") == "queued" and str(job.get("error") or "").startswith("waiting for dependency") else "queued",
                    "label": "上游依赖",
                    "detail": "等待 " + ", ".join(dependency_ids),
                    "at": created_at,
                    "job_id": job_id,
                }
            )
        started_at = str(job.get("started_at") or "").strip()
        if started_at:
            server_id = str(job.get("server_id") or "").strip() or "auto"
            gpu_index = str(job.get("gpu_index") if job.get("gpu_index") is not None else "auto")
            trace.append(
                {
                    "status": "running",
                    "label": "开始执行",
                    "detail": f"server={server_id} · gpu={gpu_index}",
                    "at": started_at,
                    "job_id": job_id,
                }
            )
        error = str(job.get("error") or "").strip()
        finished_at = str(job.get("finished_at") or "").strip()
        job_status = str(job.get("status") or "").strip() or "queued"
        if finished_at:
            trace.append(
                {
                    "status": job_status,
                    "label": workspace_execution_trace_label(job_status),
                    "detail": error or f"任务状态：{job_status}",
                    "at": finished_at,
                    "job_id": job_id,
                }
            )
        elif error:
            trace.append(
                {
                    "status": "blocked" if job_status == "queued" else job_status,
                    "label": "调度提示",
                    "detail": error,
                    "at": started_at or created_at,
                    "job_id": job_id,
                }
            )
    return trace[-10:]

def workspace_execution_trace_label(status: str) -> str:
    if status == "done":
        return "执行完成"
    if status == "failed":
        return "执行失败"
    if status == "stopped":
        return "已停止"
    if status == "running":
        return "运行中"
    if status in {"queued", "blocked"}:
        return "等待中"
    return "状态更新"
