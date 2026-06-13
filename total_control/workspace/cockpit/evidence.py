"""Cockpit — evidence helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .helpers import workspace_payload_bool, workspace_backfill_request_matches
from .scheduler import (
    apply_workspace_config_value,
    workspace_mutable_node_config_by_kind,
    workspace_scheduler_values_from_selection,
)
from ..execution import workspace_config_values, workspace_node_config_by_kind
from ..automation.advance import derive_workspace_automation_state

def apply_workspace_evidence_config_value(
    config: dict[str, Any],
    key: str,
    value: Any,
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    before = len(applied)
    apply_workspace_config_value(config, key, value, applied, label, force=force)
    for item in applied[before:]:
        item["source"] = "evidence"

def merge_workspace_evidence_config_values(
    config: dict[str, Any],
    key: str,
    values: list[str],
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    if not cleaned:
        return

    current = [] if force else workspace_config_values(config.get(key))
    merged = list(current)
    changed_values: list[str] = []
    existing = set(current)
    for value in cleaned:
        if value in existing:
            continue
        existing.add(value)
        merged.append(value)
        changed_values.append(value)
    if not changed_values and not force:
        return
    new_value = "\n".join(cleaned if force else merged)
    if str(config.get(key) or "").strip() == new_value:
        return
    config[key] = new_value
    applied.append(
        {
            "field": key,
            "label": label,
            "value": "\n".join(changed_values or cleaned),
            "source": "evidence",
        }
    )

def workspace_discovery_evidence_values(execution: dict[str, Any]) -> dict[str, Any]:
    dataset_candidates: list[str] = []
    data_roots: list[str] = []
    output_roots: list[str] = []
    artifact_paths: list[str] = []
    metric_paths: list[str] = []
    found_manifests: list[str] = []
    setup_suggestion = ""
    run_suggestion = ""
    gpu_server_id = ""

    def append_unique(items: list[str], value: Any) -> None:
        text = str(value or "").strip()
        if text and text not in items:
            items.append(text)

    for node in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        resources = node.get("resources") if isinstance(node.get("resources"), dict) else {}
        if kind in {"env.infer", "repo.inspect"}:
            setup_suggestion = str(resources.get("setup_suggestion") or setup_suggestion or "").strip()
            run_suggestion = str(resources.get("run_suggestion") or run_suggestion or "").strip()
            for manifest in (resources.get("found_manifests") if isinstance(resources.get("found_manifests"), list) else []):
                append_unique(found_manifests, manifest)
        elif kind == "run.command":
            run_suggestion = str(resources.get("run_suggestion") or run_suggestion or "").strip()
        elif kind == "gpu.allocate":
            server_id = str(resources.get("server_id") or "").strip()
            if server_id and server_id != "auto":
                gpu_server_id = server_id

        for artifact in (node.get("artifacts") if isinstance(node.get("artifacts"), list) else []):
            if not isinstance(artifact, dict) or str(artifact.get("source") or "").strip() != "log":
                continue
            label = str(artifact.get("label") or "").strip()
            status = str(artifact.get("status") or "").strip()
            value = str(artifact.get("resolved_path") or artifact.get("path") or "").strip()
            if not value:
                continue
            if label == "候选数据集" and status == "found":
                append_unique(dataset_candidates, value)
                parent = str(Path(value).expanduser().parent)
                append_unique(data_roots, parent)
            elif label in {"候选数据根", "数据根目录"} and status == "found":
                append_unique(data_roots, value)
            elif label == "输出目录":
                append_unique(output_roots, value)
                if status == "found":
                    append_unique(artifact_paths, value)
            elif label == "产物路径":
                append_unique(artifact_paths, value)
            elif label == "指标路径":
                append_unique(metric_paths, value)
            elif label == "环境清单" and status == "found":
                append_unique(found_manifests, artifact.get("path") or value)

    return {
        "dataset_candidates": dataset_candidates,
        "data_roots": data_roots,
        "output_roots": output_roots,
        "artifact_paths": artifact_paths,
        "metric_paths": metric_paths,
        "found_manifests": found_manifests,
        "setup_suggestion": setup_suggestion,
        "run_suggestion": run_suggestion,
        "gpu_server_id": gpu_server_id,
    }

def workspace_evidence_backfill_item(
    workspace: dict[str, Any],
    node_kind: str,
    field: str,
    label: str,
    values: list[str] | str,
    *,
    mode: str = "append",
) -> dict[str, Any]:
    config = workspace_node_config_by_kind(workspace, node_kind)
    candidate_values = (
        [str(value or "").strip() for value in values]
        if isinstance(values, list)
        else [str(values or "").strip()]
    )
    candidate_values = [value for value in candidate_values if value]
    current_values = workspace_config_values(config.get(field)) if isinstance(config, dict) else []
    current_text = str(config.get(field) or "").strip() if isinstance(config, dict) else ""
    existing = set(current_values)
    new_values = [value for value in candidate_values if value not in existing]
    if not config:
        status = "blocked"
        action = f"缺少 {node_kind} 节点，无法回填 {field}。"
    elif not candidate_values:
        status = "draft"
        action = "等待安全发现产生可用证据。"
    elif mode == "replace" and current_text and current_text != candidate_values[0]:
        status = "warning"
        action = "已有人工/模板值；自动回填默认不会覆盖，强制回填才会替换。"
    elif mode == "replace" and current_text == candidate_values[0]:
        status = "done"
        action = "证据已经写入该字段。"
    elif mode == "replace" and field in {"server_id", "gpu_policy", "gpu_index"} and current_text == "auto":
        status = "ready"
        action = "回填会替换默认自动值。"
    elif mode == "replace":
        status = "ready"
        action = "回填证据会写入当前空字段。"
    elif new_values:
        status = "ready"
        action = "回填证据会追加新值，不覆盖已有值。"
    else:
        status = "done"
        action = "候选证据已经存在于该字段。"
    return {
        "node_kind": node_kind,
        "field": field,
        "label": label,
        "status": status,
        "mode": mode,
        "current": "\n".join(current_values) if current_values else current_text,
        "value": "\n".join(new_values or candidate_values),
        "candidate_count": len(candidate_values),
        "new_count": len(new_values) if mode != "replace" else (0 if status == "done" else len(candidate_values)),
        "action": action,
    }

def derive_workspace_evidence_backfill_plan(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    resource_orchestration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = workspace_discovery_evidence_values(execution)
    items = [
        workspace_evidence_backfill_item(workspace, "path.resolve", "data_roots", "发现数据根", values["data_roots"]),
        workspace_evidence_backfill_item(workspace, "path.resolve", "output_roots", "发现输出目录", values["output_roots"]),
        workspace_evidence_backfill_item(workspace, "dataset.find", "data_roots", "发现数据候选根", values["data_roots"]),
        workspace_evidence_backfill_item(workspace, "dataset.find", "dataset_hints", "发现数据集线索", values["dataset_candidates"]),
        workspace_evidence_backfill_item(workspace, "env.infer", "manifest_paths", "发现环境清单", values["found_manifests"]),
        workspace_evidence_backfill_item(workspace, "env.prepare", "setup_command", "发现环境安装命令", values["setup_suggestion"], mode="replace"),
        workspace_evidence_backfill_item(workspace, "run.command", "run_command", "发现运行命令", values["run_suggestion"], mode="replace"),
        workspace_evidence_backfill_item(workspace, "artifact.collect", "artifact_paths", "发现产物路径", values["artifact_paths"]),
        workspace_evidence_backfill_item(workspace, "artifact.collect", "metric_paths", "发现指标路径", values["metric_paths"]),
        workspace_evidence_backfill_item(workspace, "eval.report", "metric_paths", "发现报告指标路径", values["metric_paths"]),
    ]
    scheduler = (
        resource_orchestration.get("scheduler")
        if isinstance(resource_orchestration, dict) and isinstance(resource_orchestration.get("scheduler"), dict)
        else {}
    )
    scheduler_values = workspace_scheduler_values_from_selection(scheduler) if scheduler else {}
    scheduler_server_id = str(scheduler_values.get("server_id") or "").strip()
    scheduler_gpu_index = str(scheduler_values.get("gpu_index") or "").strip()
    scheduler_gpu_policy = str(scheduler_values.get("gpu_policy") or "").strip()
    scheduler_min_free = str(scheduler_values.get("min_free_memory_gib") or "").strip()
    if scheduler_server_id:
        scheduler_items = [
            ("gpu.allocate", "server_id", "调度目标服务器", scheduler_server_id),
            ("gpu.allocate", "gpu_policy", "调度 GPU 策略", scheduler_gpu_policy),
            ("gpu.allocate", "gpu_index", "调度 GPU 编号", scheduler_gpu_index),
            ("run.command", "server_id", "调度运行服务器", scheduler_server_id),
            ("run.command", "gpu_policy", "调度运行 GPU 策略", scheduler_gpu_policy),
            ("run.command", "gpu_index", "调度运行 GPU 编号", scheduler_gpu_index),
        ]
        if scheduler_min_free:
            scheduler_items.extend(
                [
                    ("gpu.allocate", "min_free_memory_gib", "调度最低空闲显存", scheduler_min_free),
                    ("run.command", "min_free_memory_gib", "调度最低空闲显存", scheduler_min_free),
                ]
            )
        items.extend(
            [
                workspace_evidence_backfill_item(workspace, node_kind, field, label, value, mode="replace")
                for node_kind, field, label, value in scheduler_items
                if str(value or "").strip()
            ]
        )
    gpu_server_id = str(values.get("gpu_server_id") or "").strip()
    if gpu_server_id and not scheduler_server_id:
        items.extend(
            [
                workspace_evidence_backfill_item(workspace, "gpu.allocate", "server_id", "发现调度服务器", gpu_server_id, mode="replace"),
                workspace_evidence_backfill_item(workspace, "gpu.allocate", "gpu_policy", "发现 GPU 策略", "auto", mode="replace"),
                workspace_evidence_backfill_item(workspace, "run.command", "server_id", "发现运行服务器", gpu_server_id, mode="replace"),
                workspace_evidence_backfill_item(workspace, "run.command", "gpu_policy", "发现 GPU 策略", "auto", mode="replace"),
            ]
        )
    ready_items = [item for item in items if str(item.get("status") or "") == "ready"]
    done_items = [item for item in items if str(item.get("status") or "") == "done"]
    blocked_items = [item for item in items if str(item.get("status") or "") == "blocked"]
    warning_items = [item for item in items if str(item.get("status") or "") == "warning"]
    if blocked_items:
        status = "blocked"
    elif ready_items:
        status = "ready"
    elif warning_items:
        status = "warning"
    elif done_items:
        status = "done"
    else:
        status = "draft"
    return {
        "status": status,
        "summary": f"{len(ready_items)} 项可回填 · {len(done_items)} 项已存在 · {len(warning_items)} 项需确认 · {len(blocked_items)} 项阻塞",
        "items": items,
        "ready_count": len(ready_items),
        "done_count": len(done_items),
        "warning_count": len(warning_items),
        "blocked_count": len(blocked_items),
        "next_action": ready_items[0] if ready_items else warning_items[0] if warning_items else blocked_items[0] if blocked_items else {},
    }

def apply_workspace_discovery_evidence_to_payload(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
    *,
    force: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated = copy.deepcopy(workspace)
    applied: list[dict[str, Any]] = []
    execution = derive_workspace_execution_state(updated, jobs)
    values = workspace_discovery_evidence_values(execution)
    dataset_candidates = values["dataset_candidates"]
    data_roots = values["data_roots"]
    output_roots = values["output_roots"]
    artifact_paths = values["artifact_paths"]
    metric_paths = values["metric_paths"]
    found_manifests = values["found_manifests"]
    setup_suggestion = values["setup_suggestion"]
    run_suggestion = values["run_suggestion"]
    gpu_server_id = values["gpu_server_id"]

    path_config = workspace_mutable_node_config_by_kind(updated, "path.resolve")
    if path_config:
        merge_workspace_evidence_config_values(path_config, "data_roots", data_roots, applied, "发现数据根", force=force)
        merge_workspace_evidence_config_values(path_config, "output_roots", output_roots, applied, "发现输出目录", force=force)

    dataset_config = workspace_mutable_node_config_by_kind(updated, "dataset.find")
    if dataset_config:
        merge_workspace_evidence_config_values(dataset_config, "data_roots", data_roots, applied, "发现数据候选根", force=force)
        merge_workspace_evidence_config_values(dataset_config, "dataset_hints", dataset_candidates, applied, "发现数据集线索", force=force)

    env_infer_config = workspace_mutable_node_config_by_kind(updated, "env.infer")
    if env_infer_config:
        merge_workspace_evidence_config_values(env_infer_config, "manifest_paths", found_manifests, applied, "发现环境清单", force=force)

    env_prepare_config = workspace_mutable_node_config_by_kind(updated, "env.prepare")
    if env_prepare_config and setup_suggestion:
        apply_workspace_evidence_config_value(
            env_prepare_config,
            "setup_command",
            setup_suggestion,
            applied,
            "发现环境安装命令",
            force=force,
        )

    run_config = workspace_mutable_node_config_by_kind(updated, "run.command")
    if run_config and run_suggestion:
        apply_workspace_evidence_config_value(
            run_config,
            "run_command",
            run_suggestion,
            applied,
            "发现运行命令",
            force=force,
        )

    artifact_config = workspace_mutable_node_config_by_kind(updated, "artifact.collect")
    if artifact_config:
        merge_workspace_evidence_config_values(artifact_config, "artifact_paths", artifact_paths, applied, "发现产物路径", force=force)
        merge_workspace_evidence_config_values(artifact_config, "metric_paths", metric_paths, applied, "发现指标路径", force=force)

    eval_config = workspace_mutable_node_config_by_kind(updated, "eval.report")
    if eval_config:
        merge_workspace_evidence_config_values(eval_config, "metric_paths", metric_paths, applied, "发现报告指标路径", force=force)

    if gpu_server_id:
        for kind, label in (("gpu.allocate", "发现调度服务器"), ("run.command", "发现运行服务器")):
            config = workspace_mutable_node_config_by_kind(updated, kind)
            if config:
                apply_workspace_evidence_config_value(config, "server_id", gpu_server_id, applied, label, force=force)
                apply_workspace_evidence_config_value(config, "gpu_policy", "auto", applied, "发现 GPU 策略", force=force)

    if applied:
        updated["updated_at"] = now_iso()
    return updated, applied

def apply_workspace_evidence_backfill_item_to_payload(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
    requested_item: dict[str, Any],
    *,
    statuses: list[dict[str, Any]] | None = None,
    force: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated = copy.deepcopy(workspace)
    execution = derive_workspace_execution_state(updated, jobs)
    if statuses is not None:
        automation = derive_workspace_automation_state(updated, execution, statuses)
        plan = (
            automation.get("evidence_backfill")
            if isinstance(automation.get("evidence_backfill"), dict)
            else {}
        )
    else:
        plan = derive_workspace_evidence_backfill_plan(updated, execution)
    plan_items = plan.get("items") if isinstance(plan.get("items"), list) else []
    item = next(
        (
            candidate for candidate in plan_items
            if isinstance(candidate, dict) and workspace_backfill_request_matches(candidate, requested_item)
        ),
        None,
    )
    if not item:
        raise ValueError("backfill item not found")
    status = str(item.get("status") or "").strip()
    if status in {"blocked", "draft", "failed"}:
        raise ValueError(str(item.get("action") or "this backfill item is not ready"))
    node_kind = str(item.get("node_kind") or "").strip()
    field = str(item.get("field") or "").strip()
    label = str(item.get("label") or field or "证据回填").strip()
    mode = str(item.get("mode") or "append").strip()
    value = str(item.get("value") or "").strip()
    if not node_kind or not field or not value:
        raise ValueError("backfill item is missing node kind, field or value")
    config = workspace_mutable_node_config_by_kind(updated, node_kind)
    if not config:
        raise ValueError(f"missing {node_kind} node")

    applied: list[dict[str, Any]] = []
    if mode == "replace":
        apply_workspace_evidence_config_value(config, field, value, applied, label, force=force)
    else:
        merge_workspace_evidence_config_values(config, field, workspace_config_values(value), applied, label, force=force)
    for applied_item in applied:
        applied_item["node_kind"] = node_kind
        applied_item["mode"] = mode
        applied_item["source"] = "evidence"
    if applied:
        updated["updated_at"] = now_iso()
    return updated, applied
