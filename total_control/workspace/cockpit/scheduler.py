"""Cockpit — scheduler helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .helpers import clamp_score
from ..automation.core import workspace_status_priority
from ..automation.helpers import compact_contract_items
from ..execution import workspace_node_config_by_kind

def workspace_status_age_seconds(status: dict[str, Any], now_ts: float | None = None) -> int:
    collected_ts = parse_iso_timestamp(status.get("collected_at"))
    if collected_ts <= 0:
        return 0
    current = now_ts if now_ts is not None else time.time()
    return max(0, int(round(current - collected_ts)))

def workspace_host_resource_summary_for_scheduler(status: dict[str, Any]) -> dict[str, Any]:
    resources = status.get("host_resources") if isinstance(status.get("host_resources"), dict) else {}
    if not resources:
        return {
            "ok": False,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "load1": 0.0,
            "summary": "主机资源待采集",
        }
    if resources.get("ok") is False:
        return {
            "ok": False,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "load1": 0.0,
            "summary": str(resources.get("error") or "主机资源采集异常"),
        }
    cpu = resources.get("cpu") if isinstance(resources.get("cpu"), dict) else {}
    memory = resources.get("memory") if isinstance(resources.get("memory"), dict) else {}
    cpu_percent = safe_float(cpu.get("util_percent"), 0.0)
    memory_percent = safe_float(memory.get("used_percent"), 0.0)
    load1 = safe_float(cpu.get("load1"), 0.0)
    return {
        "ok": True,
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory_percent, 1),
        "load1": round(load1, 2),
        "summary": f"CPU {cpu_percent:.1f}% · 内存 {memory_percent:.1f}%",
    }

def workspace_scheduler_candidate_status(
    *,
    mode: str,
    gpu_state: str = "",
    memory_free_mib: int = 0,
    min_free_memory_mib: int = 0,
    host: dict[str, Any] | None = None,
) -> str:
    host = host or {}
    if mode == "cpu":
        if host.get("ok") is False:
            return "warning"
        if safe_float(host.get("cpu_percent"), 0.0) >= 92 or safe_float(host.get("memory_percent"), 0.0) >= 94:
            return "warning"
        return "ready"
    if min_free_memory_mib and memory_free_mib < min_free_memory_mib:
        return "blocked"
    if gpu_state == "idle":
        return "ready"
    return "warning"

def workspace_scheduler_score(
    *,
    mode: str,
    status_value: str,
    memory_free_mib: int = 0,
    gpu_state: str = "",
    gpu_util: int = 0,
    process_count: int = 0,
    host: dict[str, Any] | None = None,
    age_seconds: int = 0,
) -> int:
    host = host or {}
    score = 70.0 if mode == "cpu" else 45.0
    if mode == "gpu":
        score += min(memory_free_mib / 1024 * 1.8, 34)
        score += 18 if gpu_state == "idle" else -16
        score -= min(max(gpu_util, 0) / 2.5, 24)
        score -= min(max(process_count, 0) * 7, 21)
    score -= max(safe_float(host.get("cpu_percent"), 0.0) - 70, 0) * 0.35
    score -= max(safe_float(host.get("memory_percent"), 0.0) - 78, 0) * 0.45
    if host.get("ok") is False:
        score -= 7
    if age_seconds > 180:
        score -= min((age_seconds - 180) / 30, 18)
    if status_value == "blocked":
        score -= 45
    elif status_value == "warning":
        score -= 12
    return clamp_score(score)

def workspace_scheduler_reasons(
    *,
    mode: str,
    candidate_status: str,
    memory_free_mib: int = 0,
    min_free_memory_mib: int = 0,
    gpu_state: str = "",
    gpu_util: int = 0,
    process_count: int = 0,
    host: dict[str, Any] | None = None,
    age_seconds: int = 0,
) -> tuple[list[str], list[str]]:
    host = host or {}
    reasons: list[str] = []
    warnings: list[str] = []
    if mode == "cpu":
        reasons.append("CPU/无 GPU 模式")
    else:
        reasons.append(f"{memory_free_mib // 1024} GiB 显存空闲")
        reasons.append("GPU 空闲" if gpu_state == "idle" else f"GPU {gpu_state or '未知'}")
        if gpu_util:
            warnings.append(f"GPU util {gpu_util}%")
        if process_count:
            warnings.append(f"{process_count} 个 GPU 进程")
        if min_free_memory_mib and memory_free_mib < min_free_memory_mib:
            warnings.append(f"低于最小显存 {min_free_memory_mib // 1024} GiB")
    if host.get("summary"):
        reasons.append(str(host.get("summary")))
    if host.get("ok") is False:
        warnings.append(str(host.get("summary") or "主机资源异常"))
    if safe_float(host.get("cpu_percent"), 0.0) >= 90:
        warnings.append("主机 CPU 偏高")
    if safe_float(host.get("memory_percent"), 0.0) >= 90:
        warnings.append("主机内存偏高")
    if age_seconds > 180:
        warnings.append(f"快照 {age_seconds}s 前")
    if candidate_status == "ready" and not warnings:
        reasons.append("可作为执行包目标")
    return (compact_contract_items(reasons, limit=5), compact_contract_items(warnings, limit=5))

def derive_workspace_resource_scheduler(
    statuses: list[dict[str, Any]],
    *,
    gpu_policy: str = "auto",
    requested_server_id: str = "",
    requested_gpu_index: str = "",
    min_free_memory_gib: int = 0,
) -> dict[str, Any]:
    policy = str(gpu_policy or "auto").strip().lower() or "auto"
    cpu_mode = policy in {"cpu", "none", "no_gpu"}
    mode = "cpu" if cpu_mode else "gpu"
    min_free_memory_mib = max(safe_int(min_free_memory_gib, 0), 0) * 1024
    now_ts = time.time()
    candidates: list[dict[str, Any]] = []
    rejected_count = 0
    online_statuses = [item for item in statuses if isinstance(item, dict) and item.get("online")]

    for status in online_statuses:
        server_id = str(status.get("id") or "").strip()
        if requested_server_id and requested_server_id not in {"auto", server_id}:
            continue
        server_name = str(status.get("name") or server_id).strip()
        host = workspace_host_resource_summary_for_scheduler(status)
        age_seconds = workspace_status_age_seconds(status, now_ts)
        process_count_by_gpu: dict[str, int] = {}
        for process in (status.get("processes") if isinstance(status.get("processes"), list) else []):
            if not isinstance(process, dict):
                continue
            key = str(process.get("gpu_index") if process.get("gpu_index") is not None else "").strip()
            if key:
                process_count_by_gpu[key] = process_count_by_gpu.get(key, 0) + 1
        if cpu_mode:
            candidate_status = workspace_scheduler_candidate_status(mode="cpu", host=host)
            score = workspace_scheduler_score(mode="cpu", status_value=candidate_status, host=host, age_seconds=age_seconds)
            reasons, warnings = workspace_scheduler_reasons(
                mode="cpu",
                candidate_status=candidate_status,
                host=host,
                age_seconds=age_seconds,
            )
            candidates.append(
                {
                    "id": f"{server_id}:cpu",
                    "status": candidate_status,
                    "mode": "cpu",
                    "score": score,
                    "server_id": server_id,
                    "server_name": server_name,
                    "gpu_index": "cpu",
                    "gpu_name": "CPU",
                    "gpu_state": "cpu",
                    "memory_free_mib": 0,
                    "memory_total_mib": 0,
                    "gpu_util": 0,
                    "process_count": 0,
                    "host": host,
                    "snapshot_age_seconds": age_seconds,
                    "collected_at": str(status.get("collected_at") or "").strip(),
                    "reasons": reasons,
                    "warnings": warnings,
                }
            )
            continue
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else []):
            if not isinstance(gpu, dict):
                continue
            gpu_index = str(gpu.get("index") if gpu.get("index") is not None else "auto")
            if requested_gpu_index and requested_gpu_index not in {"auto", gpu_index}:
                rejected_count += 1
                continue
            memory_free_mib = safe_int(gpu.get("memory_free_mib"), 0)
            gpu_state = str(gpu.get("state") or "").strip()
            gpu_util = safe_int(gpu.get("gpu_util"), 0)
            process_count = process_count_by_gpu.get(gpu_index, 0)
            candidate_status = workspace_scheduler_candidate_status(
                mode="gpu",
                gpu_state=gpu_state,
                memory_free_mib=memory_free_mib,
                min_free_memory_mib=min_free_memory_mib,
                host=host,
            )
            score = workspace_scheduler_score(
                mode="gpu",
                status_value=candidate_status,
                memory_free_mib=memory_free_mib,
                gpu_state=gpu_state,
                gpu_util=gpu_util,
                process_count=process_count,
                host=host,
                age_seconds=age_seconds,
            )
            reasons, warnings = workspace_scheduler_reasons(
                mode="gpu",
                candidate_status=candidate_status,
                memory_free_mib=memory_free_mib,
                min_free_memory_mib=min_free_memory_mib,
                gpu_state=gpu_state,
                gpu_util=gpu_util,
                process_count=process_count,
                host=host,
                age_seconds=age_seconds,
            )
            candidates.append(
                {
                    "id": f"{server_id}:{gpu_index}",
                    "status": candidate_status,
                    "mode": "gpu",
                    "score": score,
                    "server_id": server_id,
                    "server_name": server_name,
                    "gpu_index": gpu_index,
                    "gpu_name": str(gpu.get("name") or f"GPU {gpu_index}").strip(),
                    "gpu_state": gpu_state,
                    "memory_free_mib": memory_free_mib,
                    "memory_total_mib": safe_int(gpu.get("memory_total_mib"), 0),
                    "gpu_util": gpu_util,
                    "process_count": process_count,
                    "host": host,
                    "snapshot_age_seconds": age_seconds,
                    "collected_at": str(status.get("collected_at") or "").strip(),
                    "reasons": reasons,
                    "warnings": warnings,
                }
            )

    candidates.sort(
        key=lambda item: (
            workspace_status_priority(str(item.get("status") or "draft")),
            safe_int(item.get("score"), 0),
            safe_int(item.get("memory_free_mib"), 0),
        ),
        reverse=True,
    )
    selected = candidates[0] if candidates else {}
    ready_count = sum(1 for item in candidates if str(item.get("status") or "") == "ready")
    if not online_statuses:
        status = "blocked"
    elif selected and str(selected.get("status") or "") == "ready":
        status = "ready"
    elif candidates:
        status = "warning"
    else:
        status = "blocked"
    return {
        "status": status,
        "mode": mode,
        "policy": policy,
        "requested_server_id": requested_server_id or "auto",
        "requested_gpu_index": requested_gpu_index or ("cpu" if cpu_mode else "auto"),
        "min_free_memory_mib": min_free_memory_mib,
        "selected": copy.deepcopy(selected),
        "candidates": copy.deepcopy(candidates[:8]),
        "candidate_count": len(candidates),
        "ready_count": ready_count,
        "rejected_count": rejected_count,
        "summary": (
            f"{ready_count}/{len(candidates)} 个候选可用 · "
            f"{'CPU 模式' if cpu_mode else f'最小显存 {min_free_memory_mib // 1024} GiB'}"
        ),
        "next_action": "刷新单机或调整 gpu_policy/server_id/min_free_memory_gib" if status != "ready" else "调度目标可写入执行包",
    }

def workspace_scheduler_values_from_selection(scheduler: dict[str, Any]) -> dict[str, Any]:
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    if not selected:
        return {
            "server_id": "",
            "gpu_index": "",
            "gpu_policy": "",
            "min_free_memory_gib": "",
            "mode": str(scheduler.get("mode") or "").strip(),
            "status": str(scheduler.get("status") or "draft").strip(),
        }
    mode = str(selected.get("mode") or scheduler.get("mode") or "gpu").strip().lower()
    cpu_mode = mode == "cpu" or str(scheduler.get("policy") or "").strip().lower() in {"cpu", "none", "no_gpu"}
    policy = str(scheduler.get("policy") or ("cpu" if cpu_mode else "auto")).strip().lower() or ("cpu" if cpu_mode else "auto")
    server_id = str(selected.get("server_id") or "").strip()
    gpu_index = "none" if cpu_mode else str(selected.get("gpu_index") or "").strip()
    min_free_memory_gib = ""
    if not cpu_mode:
        requested_min_mib = safe_int(scheduler.get("min_free_memory_mib"), 0)
        if requested_min_mib > 0:
            min_free_memory_gib = str(max(requested_min_mib // 1024, 1))
        else:
            memory_free_mib = safe_int(selected.get("memory_free_mib"), 0)
            if memory_free_mib:
                min_free_memory_gib = str(max(memory_free_mib // 1024 - 2, 1))
    return {
        "server_id": server_id,
        "gpu_index": gpu_index,
        "gpu_policy": policy if cpu_mode else "auto",
        "min_free_memory_gib": min_free_memory_gib,
        "mode": "cpu" if cpu_mode else "gpu",
        "status": str(scheduler.get("status") or selected.get("status") or "draft").strip(),
        "score": safe_int(selected.get("score"), 0),
    }

def workspace_scheduler_values_from_candidate(
    candidate: dict[str, Any] | None,
    scheduler: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {}
    scheduler = scheduler if isinstance(scheduler, dict) else {}
    server_id = str(candidate.get("server_id") or candidate.get("serverId") or "").strip()
    if not server_id:
        return {}
    raw_mode = str(candidate.get("mode") or "").strip().lower()
    raw_policy = str(candidate.get("gpu_policy") or candidate.get("policy") or scheduler.get("policy") or "").strip().lower()
    raw_gpu_index = str(
        candidate.get("gpu_index")
        if candidate.get("gpu_index") is not None
        else candidate.get("gpuIndex")
        if candidate.get("gpuIndex") is not None
        else ""
    ).strip()
    cpu_mode = (
        raw_mode in {"cpu", "none", "no_gpu"}
        or raw_policy in {"cpu", "none", "no_gpu"}
        or raw_gpu_index in {"cpu", "none", "no_gpu"}
    )
    policy = "cpu" if cpu_mode else (raw_policy if raw_policy not in {"cpu", "none", "no_gpu"} else "") or "auto"
    gpu_index = "none" if cpu_mode else raw_gpu_index or "auto"
    min_free_memory_gib = ""
    if not cpu_mode:
        requested_min_gib = safe_int(candidate.get("min_free_memory_gib") or candidate.get("minFreeMemoryGib"), 0)
        if requested_min_gib > 0:
            min_free_memory_gib = str(requested_min_gib)
        else:
            requested_min_mib = safe_int(candidate.get("min_free_memory_mib") or scheduler.get("min_free_memory_mib"), 0)
            if requested_min_mib > 0:
                min_free_memory_gib = str(max(requested_min_mib // 1024, 1))
            else:
                memory_free_mib = safe_int(candidate.get("memory_free_mib") or candidate.get("memoryFreeMib"), 0)
                if memory_free_mib:
                    min_free_memory_gib = str(max(memory_free_mib // 1024 - 2, 1))
    return {
        "server_id": server_id,
        "gpu_index": gpu_index,
        "gpu_policy": policy,
        "min_free_memory_gib": min_free_memory_gib,
        "mode": "cpu" if cpu_mode else "gpu",
        "status": str(candidate.get("status") or scheduler.get("status") or "draft").strip(),
        "score": safe_int(candidate.get("score"), 0),
    }

def derive_workspace_scheduler_values(
    workspace: dict[str, Any],
    statuses: list[dict[str, Any]],
) -> dict[str, Any]:
    gpu_config = workspace_node_config_by_kind(workspace, "gpu.allocate")
    run_config = workspace_node_config_by_kind(workspace, "run.command")
    gpu_policy = str(run_config.get("gpu_policy") or gpu_config.get("gpu_policy") or "auto").strip().lower() or "auto"
    requested_server_id = str(run_config.get("server_id") or gpu_config.get("server_id") or "auto").strip() or "auto"
    requested_gpu_index = str(run_config.get("gpu_index") or gpu_config.get("gpu_index") or "").strip()
    min_free_memory_gib = safe_int(run_config.get("min_free_memory_gib") or gpu_config.get("min_free_memory_gib"), 0)
    scheduler = derive_workspace_resource_scheduler(
        statuses,
        gpu_policy=gpu_policy,
        requested_server_id=requested_server_id,
        requested_gpu_index=requested_gpu_index,
        min_free_memory_gib=min_free_memory_gib,
    )
    values = workspace_scheduler_values_from_selection(scheduler)
    values["scheduler"] = scheduler
    return values

def apply_workspace_config_value(
    config: dict[str, Any],
    key: str,
    value: Any,
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    if value in (None, ""):
        return
    if not force and str(config.get(key) or "").strip():
        return
    config[key] = value
    applied.append({"field": key, "label": label, "value": value})

def apply_workspace_scheduler_config_value(
    config: dict[str, Any],
    key: str,
    value: Any,
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    if value in (None, ""):
        return
    text_value = str(value).strip()
    current = str(config.get(key) or "").strip()
    replace_default_auto = key in {"server_id", "gpu_policy", "gpu_index"} and current == "auto" and text_value != "auto"
    if not force and current and not replace_default_auto:
        return
    if current == text_value:
        return
    config[key] = value
    applied.append({"field": key, "label": label, "value": value, "source": "scheduler"})

def workspace_mutable_node_config_by_kind(workspace: dict[str, Any], kind: str) -> dict[str, Any]:
    for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []):
        if not isinstance(node, dict) or str(node.get("kind") or "").strip() != kind:
            continue
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        node["config"] = config
        return config
    return {}
