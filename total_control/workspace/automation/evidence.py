from __future__ import annotations

from ._deps import *  # noqa: F403


def workspace_evidence_item(
    label: str,
    value: str,
    *,
    status: str = "planned",
    source: str = "",
    node_kind: str = "",
) -> dict[str, Any]:
    return {
        "label": str(label or "").strip(),
        "value": str(value or "").strip(),
        "status": str(status or "planned").strip() or "planned",
        "source": str(source or "").strip(),
        "node_kind": str(node_kind or "").strip(),
    }

def workspace_add_evidence_item(
    group: dict[str, Any],
    item: dict[str, Any],
    seen: set[tuple[str, str, str]],
    *,
    limit: int = 8,
) -> None:
    value = str(item.get("value") or "").strip()
    if not value:
        return
    key = (
        str(item.get("label") or "").strip(),
        value,
        str(item.get("node_kind") or "").strip(),
    )
    if key in seen:
        return
    seen.add(key)
    group["count"] = safe_int(group.get("count"), 0) + 1
    if len(group["items"]) < limit:
        group["items"].append(item)

def derive_workspace_automation_evidence(execution: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {
        "paths": {"id": "paths", "label": "路径", "title": "路径证据", "count": 0, "items": []},
        "dataset": {"id": "dataset", "label": "数据集", "title": "数据证据", "count": 0, "items": []},
        "env": {"id": "env", "label": "环境", "title": "环境证据", "count": 0, "items": []},
        "gpu": {"id": "gpu", "label": "GPU", "title": "资源证据", "count": 0, "items": []},
        "run": {"id": "run", "label": "运行入口", "title": "运行入口证据", "count": 0, "items": []},
        "artifact": {"id": "artifact", "label": "产物", "title": "产物证据", "count": 0, "items": []},
        "metric": {"id": "metric", "label": "指标", "title": "指标证据", "count": 0, "items": []},
    }
    seen: set[tuple[str, str, str]] = set()
    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    artifact_label_groups = {
        "工作目录": "paths",
        "项目文档": "paths",
        "数据根目录": "paths",
        "输出目录": "paths",
        "候选数据根": "dataset",
        "候选数据集": "dataset",
        "数据集线索": "dataset",
        "检索词": "dataset",
        "数据来源线索": "dataset",
        "数据结构要求": "dataset",
        "环境清单": "env",
        "产物路径": "artifact",
        "指标路径": "artifact",
        "最近日志": "artifact",
        "远端日志": "artifact",
    }
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_kind = str(node.get("kind") or "").strip()
        artifacts = node.get("artifacts") if isinstance(node.get("artifacts"), list) else []
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            label = str(artifact.get("label") or artifact.get("source") or "").strip()
            group_id = artifact_label_groups.get(label)
            if not group_id:
                continue
            value = str(artifact.get("resolved_path") or artifact.get("path") or "").strip()
            workspace_add_evidence_item(
                groups[group_id],
                workspace_evidence_item(
                    label,
                    value,
                    status=str(artifact.get("status") or "planned"),
                    source=str(artifact.get("source") or ""),
                    node_kind=node_kind,
                ),
                seen,
            )
        resources = node.get("resources") if isinstance(node.get("resources"), dict) else {}
        if node_kind in {"env.infer", "repo.inspect"}:
            setup = str(resources.get("setup_suggestion") or "").strip()
            if setup:
                workspace_add_evidence_item(
                    groups["env"],
                    workspace_evidence_item("安装建议", setup, status="found", source="resource", node_kind=node_kind),
                    seen,
                )
            for manifest in (resources.get("found_manifests") if isinstance(resources.get("found_manifests"), list) else []):
                workspace_add_evidence_item(
                    groups["env"],
                    workspace_evidence_item("清单文件", str(manifest), status="found", source="resource", node_kind=node_kind),
                    seen,
                )
        if node_kind in {"repo.inspect", "run.command"}:
            run_suggestion = str(resources.get("run_suggestion") or "").strip()
            if run_suggestion:
                workspace_add_evidence_item(
                    groups["run"],
                    workspace_evidence_item("运行命令候选", run_suggestion, status="found", source="resource", node_kind=node_kind),
                    seen,
                )
        if node_kind == "gpu.allocate":
            server_id = str(resources.get("server_id") or "").strip()
            gpu_index = str(resources.get("gpu_index") or "").strip()
            gpu_policy = str(resources.get("gpu_policy") or "").strip()
            if server_id or gpu_index or gpu_policy:
                workspace_add_evidence_item(
                    groups["gpu"],
                    workspace_evidence_item(
                        "调度计划",
                        f"server={server_id or 'auto'} · gpu={gpu_index or gpu_policy or 'auto'}",
                        status="planned",
                        source="resource",
                        node_kind=node_kind,
                    ),
                    seen,
                )
        metrics = resources.get("metrics") if isinstance(resources.get("metrics"), list) else []
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            key = str(metric.get("label") or metric.get("key") or "metric").strip()
            value = str(metric.get("value") or "").strip()
            if not value:
                continue
            workspace_add_evidence_item(
                groups["metric"],
                workspace_evidence_item(
                    key,
                    f"{key}={value}",
                    status=str(metric.get("status") or "found"),
                    source=str(metric.get("source") or "log"),
                    node_kind=node_kind,
                ),
                seen,
            )
            for gpu in (resources.get("gpu_snapshot") if isinstance(resources.get("gpu_snapshot"), list) else []):
                if not isinstance(gpu, dict):
                    continue
                workspace_add_evidence_item(
                    groups["gpu"],
                    workspace_evidence_item(
                        "GPU 快照",
                        f"{gpu.get('index', '')} · {gpu.get('name', '')} · {gpu.get('memory_free', '')} free · {gpu.get('utilization', '')}",
                        status="found",
                        source="resource",
                        node_kind=node_kind,
                    ),
                    seen,
                )
    evidence = []
    for group in groups.values():
        count = safe_int(group.get("count"), 0)
        group["status"] = "ready" if count else "draft"
        group["detail"] = f"{count} 条证据" if count else "等待自动发现"
        evidence.append(group)
    return evidence

def workspace_group_evidence_by_kind(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for group in evidence:
        if not isinstance(group, dict):
            continue
        group_label = str(group.get("label") or group.get("id") or "证据").strip()
        for item in (group.get("items") if isinstance(group.get("items"), list) else []):
            if not isinstance(item, dict):
                continue
            kind = str(item.get("node_kind") or "").strip()
            if not kind:
                continue
            grouped.setdefault(kind, []).append(
                {
                    "group": group_label,
                    "label": str(item.get("label") or item.get("source") or "发现").strip(),
                    "value": str(item.get("value") or "").strip(),
                    "status": str(item.get("status") or "found").strip(),
                }
            )
    return grouped

def workspace_evidence_group(evidence: list[dict[str, Any]], group_id: str) -> dict[str, Any]:
    return next(
        (
            item for item in evidence
            if isinstance(item, dict) and str(item.get("id") or "") == group_id
        ),
        {"id": group_id, "count": 0, "items": []},
    )
