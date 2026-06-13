from __future__ import annotations

from ._deps import *  # noqa: F403


def workspace_run_node_phase(kind: str) -> str:
    if kind in {"repo.clone", "source.repo", "source.paper", "source.idea"}:
        return "source"
    if kind in {"path.resolve", "repo.inspect", "dataset.find", "env.infer", "gpu.allocate"}:
        return "discover"
    if kind == "env.prepare":
        return "setup"
    if kind == "run.command":
        return "run"
    if kind == "artifact.collect":
        return "collect"
    if kind == "eval.report":
        return "report"
    return "other"

def workspace_run_phase_label(phase: str) -> str:
    return {
        "source": "来源",
        "discover": "发现",
        "setup": "环境",
        "run": "运行",
        "collect": "收集",
        "report": "报告",
        "other": "其他",
    }.get(phase, phase)

def workspace_node_required_tool_id(kind: str) -> str:
    return {
        "repo.clone": "repo.clone",
        "path.resolve": "path.resolve",
        "repo.inspect": "repo.inspect",
        "dataset.find": "dataset.find",
        "env.infer": "env.infer",
        "env.prepare": "env.prepare",
        "gpu.allocate": "gpu.allocate",
        "run.command": "job.run",
        "artifact.collect": "artifact.collect",
        "eval.report": "report.write",
    }.get(str(kind or "").strip(), "")

def workspace_node_command_summary_for_plan(workspace: dict[str, Any], node: dict[str, Any]) -> tuple[str, str]:
    kind = str(node.get("kind") or "").strip()
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    if kind == "repo.clone":
        repo_url = str(config.get("repo_url") or source.get("repo_url") or "").strip()
        return (repo_url or "等待仓库地址", "ready" if repo_url else "blocked")
    if kind == "path.resolve":
        values = workspace_config_values(config.get("data_roots")) + workspace_config_values(config.get("output_roots"))
        detail = " · ".join([workspace_dir or "未设工作目录", f"{len(values)} 条路径线索"])
        return (detail, "ready" if workspace_dir or values else "warning")
    if kind == "repo.inspect":
        return (workspace_dir or "等待工作目录", "ready" if workspace_dir else "warning")
    if kind == "dataset.find":
        query = str(config.get("query") or workspace.get("brief") or source.get("repo_url") or source.get("paper_url") or "").strip()
        hints = len(workspace_config_values(config.get("dataset_hints")) + workspace_config_values(config.get("data_roots")))
        return (query or f"{hints} 条数据线索" or "等待数据线索", "ready" if query or hints else "warning")
    if kind == "env.infer":
        manifest_paths = workspace_config_values(config.get("manifest_paths") or "requirements.txt, pyproject.toml, environment.yml, setup.py")
        return (", ".join(manifest_paths[:4]) or "等待环境清单", "ready" if workspace_dir or manifest_paths else "warning")
    if kind == "env.prepare":
        command = str(config.get("setup_command") or "").strip()
        return (compact_workspace_command(command) if command else "缺 setup_command", "ready" if command else "blocked")
    if kind == "gpu.allocate":
        server_id = str(config.get("server_id") or "auto").strip() or "auto"
        gpu_policy = str(config.get("gpu_policy") or "auto").strip() or "auto"
        gpu_index = str(config.get("gpu_index") or "").strip()
        min_free = str(config.get("min_free_memory_gib") or "").strip()
        gpu_text = f" · gpu={gpu_index}" if gpu_index else ""
        return (f"server={server_id} · policy={gpu_policy}{gpu_text}" + (f" · min={min_free}GiB" if min_free else ""), "ready")
    if kind == "run.command":
        command = str(config.get("run_command") or "").strip()
        return (compact_workspace_command(command) if command else "缺 run_command", "ready" if command else "blocked")
    if kind == "artifact.collect":
        paths = workspace_config_values(config.get("artifact_paths") or "runs\noutputs\ncheckpoints\nlogs")
        metrics = workspace_config_values(config.get("metric_paths"))
        return (f"{len(paths)} 条产物路径 · {len(metrics)} 条指标路径", "ready" if paths or metrics else "warning")
    if kind == "eval.report":
        command = str(config.get("report_command") or "").strip()
        metrics = workspace_config_values(config.get("metric_paths"))
        if command:
            return (compact_workspace_command(command), "ready")
        return (f"缺 report_command · {len(metrics)} 条指标路径", "blocked")
    command = str(config.get("command") or config.get("goal") or "").strip()
    return (compact_workspace_command(command) if command else "没有命令摘要", "warning")

def derive_workspace_run_plan(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    execution_nodes = {
        str(item.get("id") or ""): item
        for item in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else [])
        if isinstance(item, dict)
    }
    plan_nodes: list[dict[str, Any]] = []
    phase_counts: dict[str, int] = {}
    hard_gate_ids = {"starter_chain", "agents", "run"}
    blocking_items = [
        check for check in checks
        if isinstance(check, dict)
        and str(check.get("id") or "") in hard_gate_ids
        and str(check.get("status") or "") in {"blocked", "failed"}
    ]
    warning_items = [
        check for check in checks
        if isinstance(check, dict)
        and str(check.get("id") or "") not in hard_gate_ids
        and str(check.get("status") or "") in {"blocked", "failed", "warning", "draft"}
    ]
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            continue
        phase = workspace_run_node_phase(kind)
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        summary, status = workspace_node_command_summary_for_plan(workspace, node)
        runtime = execution_nodes.get(str(node.get("id") or ""), {})
        plan_nodes.append(
            {
                "index": len(plan_nodes) + 1,
                "id": str(node.get("id") or "").strip(),
                "kind": kind,
                "title": str(node.get("title") or node.get("kind") or "").strip(),
                "phase": phase,
                "phase_label": workspace_run_phase_label(phase),
                "status": status,
                "summary": summary,
                "agent_id": str(handler.get("agent_id") or runtime.get("agent_id") or "").strip(),
                "agent_name": str(handler.get("name") or runtime.get("agent_name") or "").strip(),
                "last_job_id": str(runtime.get("job_id") or "").strip(),
                "last_job_status": str(runtime.get("job_status") or "").strip(),
                "depends_on_previous": len(plan_nodes) > 0,
            }
        )
    for node in plan_nodes:
        if node["status"] in {"blocked", "failed"}:
            blocking_items.append(
                {
                    "id": node["id"],
                    "label": node["title"],
                    "status": "blocked",
                    "title": node["title"],
                    "detail": node["summary"],
                    "action": "先运行自动发现、应用体检建议或补齐节点配置。",
                    "node_kind": node["kind"],
                }
            )
        elif node["status"] in {"warning", "draft"}:
            warning_items.append(
                {
                    "id": node["id"],
                    "label": node["title"],
                    "status": node["status"],
                    "title": node["title"],
                    "detail": node["summary"],
                    "action": "可以先运行自动发现补齐证据。",
                    "node_kind": node["kind"],
                }
            )
    status = "blocked" if blocking_items else "warning" if warning_items else "ready"
    phase_order = ["source", "discover", "setup", "run", "collect", "report", "other"]
    phases = [
        {
            "id": phase,
            "label": workspace_run_phase_label(phase),
            "count": phase_counts.get(phase, 0),
        }
        for phase in phase_order
        if phase_counts.get(phase, 0)
    ]
    return {
        "status": status,
        "node_count": len(plan_nodes),
        "phases": phases,
        "nodes": plan_nodes,
        "blocking": blocking_items,
        "warnings": warning_items,
        "summary": f"{len(plan_nodes)} 个可执行节点 · {len(phases)} 个阶段 · {len(blocking_items)} 个阻塞项 · {len(warning_items)} 个提示",
    }
