from __future__ import annotations

import json
from typing import Any

from ...orchestration.workspace_mutations import apply_artifact_write, apply_workflow_edit
from ..registry import TOOL_SIDE_EFFECTS, ToolSideEffect, tool_side_effect
from .artifacts import execute_artifact_read
from .helpers import split_values
from .web_search import execute_web_search


def execute_tool(context: Any, tool_id: str, arguments: dict[str, Any]) -> str:
    arguments = arguments if isinstance(arguments, dict) else {}
    workspace_snapshot = context.workspace

    if tool_id == "workflow.plan":
        nodes = context.workflow_nodes()
        return json.dumps(
            {
                "status": "planned" if nodes else "draft",
                "workspace_id": str(workspace_snapshot.get("id") or "").strip(),
                "workspace_name": str(workspace_snapshot.get("name") or "").strip(),
                "node_count": len(nodes),
                "nodes": nodes,
                "run_command": context.configured_run_command(),
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "web.search":
        return json.dumps(execute_web_search(context, arguments), ensure_ascii=False, indent=2)

    if tool_id == "repo.clone":
        runtime_result = context.submit_controlled_job(tool_id, arguments)
        if runtime_result:
            return json.dumps(runtime_result, ensure_ascii=False, indent=2)
        source = context.source_payload()
        repo_url = str(arguments.get("repo_url") or (source["repo_urls"][0] if source["repo_urls"] else "")).strip()
        workspace_dir = str(arguments.get("workspace_dir") or source.get("workspace_dir") or "").strip()
        return json.dumps(
            {
                "status": "ready" if repo_url and workspace_dir else "draft",
                "repo_url": repo_url,
                "workspace_dir": workspace_dir,
                "dry_run": True,
                "message": "已生成克隆计划，等待工作流节点提交实际任务。" if repo_url else "等待 repo_url。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id in {"env.prepare", "env.create"}:
        runtime_result = context.submit_controlled_job(tool_id, arguments)
        if runtime_result:
            return json.dumps(runtime_result, ensure_ascii=False, indent=2)
        config = context.node_config("env.prepare")
        env = workspace_snapshot.get("env") if isinstance(workspace_snapshot.get("env"), dict) else {}
        source = context.source_payload()
        command = str(arguments.get("command") or arguments.get("setup_command") or config.get("setup_command") or "").strip()
        env_name = str(arguments.get("env_name") or config.get("env_name") or env.get("name") or "").strip()
        return json.dumps(
            {
                "status": "ready" if command else "draft",
                "tool": tool_id,
                "plan_only": True,
                "dry_run": True,
                "command": command,
                "env_name": env_name,
                "workspace_dir": str(arguments.get("workspace_dir") or config.get("workspace_dir") or source.get("workspace_dir") or "").strip(),
                "message": "已生成环境任务；当前上下文未启用受控 runtime，未入队。" if command else "等待 setup_command 或 command。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "gpu.inspect":
        min_free_mib = int(float(arguments.get("min_free_mib") or 0))
        candidates = context.gpu_candidates(min_free_mib=min_free_mib, server_id=str(arguments.get("server_id") or "").strip())
        return json.dumps(
            {
                "status": "inspected" if context.statuses else "draft",
                "server_count": len(context.statuses),
                "gpu_count": len(candidates),
                "idle_count": len([item for item in candidates if item["eligible"]]),
                "candidates": candidates[:12],
                "selected": candidates[0] if candidates else context.automation_selected_gpu(),
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "gpu.allocate":
        min_free_mib = int(float(arguments.get("min_free_mib") or 0))
        if not min_free_mib:
            min_free_gib = float(arguments.get("min_free_memory_gib") or context.node_config("gpu.allocate").get("min_free_memory_gib") or 0)
            min_free_mib = int(min_free_gib * 1024)
        config = context.node_config("gpu.allocate")
        server_id = str(arguments.get("server_id") or config.get("server_id") or "").strip()
        candidates = context.gpu_candidates(min_free_mib=min_free_mib, server_id=server_id)
        selected = next((item for item in candidates if item["eligible"]), None)
        if not selected and not candidates:
            scheduler_selected = context.automation_selected_gpu()
            selected = scheduler_selected if scheduler_selected else None
        runtime_result = context.bind_gpu_allocation({**arguments, "selected": selected, "min_free_mib": min_free_mib})
        if runtime_result:
            return json.dumps(runtime_result, ensure_ascii=False, indent=2)
        return json.dumps(
            {
                "status": "allocated" if selected else "blocked",
                "selected": selected,
                "candidate_count": len(candidates),
                "min_free_mib": min_free_mib,
                "plan_only": True,
                "dry_run": True,
                "message": "已选出候选 GPU，等待受控 runtime 绑定到 run.command。" if selected else "没有满足条件的 GPU 候选。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "dataset.find":
        return json.dumps(context.execute_dataset_find(arguments), ensure_ascii=False, indent=2)

    if tool_id == "repo.search":
        config = context.node_config("dataset.find")
        source = context.source_payload()
        query = str(arguments.get("query") or config.get("query") or source.get("goal_text") or "").strip()
        roots = split_values(arguments.get("data_roots") or config.get("data_roots"))
        hints = split_values(arguments.get("dataset_hints") or config.get("dataset_hints"))
        for value in source["references"]:
            if value not in roots and (value.startswith("/") or value.startswith("./") or "data" in value.lower()):
                roots.append(value)
            elif value not in hints:
                hints.append(value)
        return json.dumps(
            {
                "status": "ready" if roots or hints or query else "draft",
                "query": query,
                "data_roots": roots,
                "dataset_hints": hints,
                "message": "数据线索已收集，可回填 dataset.find。" if roots or hints else "等待数据集名称、路径或参考链接。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "dir.scan":
        return json.dumps(context.execute_dir_scan(arguments), ensure_ascii=False, indent=2)

    if tool_id in {"env.inspect", "env.infer"}:
        env = workspace_snapshot.get("env") if isinstance(workspace_snapshot.get("env"), dict) else {}
        infer_config = context.node_config("env.infer")
        prepare_config = context.node_config("env.prepare")
        manifests = split_values(arguments.get("manifest_paths") or infer_config.get("manifest_paths"))
        setup_command = str(arguments.get("setup_command") or prepare_config.get("setup_command") or "").strip()
        return json.dumps(
            {
                "status": "ready" if manifests or setup_command else "draft",
                "env_name": str(env.get("name") or infer_config.get("env_name") or prepare_config.get("env_name") or "").strip(),
                "env_manager": str(env.get("manager") or prepare_config.get("env_manager") or "conda").strip(),
                "python_version": str(env.get("python") or infer_config.get("python_version") or "").strip(),
                "manifest_paths": manifests,
                "setup_command": setup_command,
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "job.run":
        runtime_result = context.submit_controlled_job(tool_id, arguments)
        if runtime_result:
            return json.dumps(runtime_result, ensure_ascii=False, indent=2)
        run_config = context.node_config("run.command")
        command = str(arguments.get("command") or run_config.get("run_command") or "").strip()
        return json.dumps(
            {
                "status": "ready" if command else "draft",
                "plan_only": True,
                "dry_run": True,
                "command": command,
                "server_id": str(arguments.get("server_id") or run_config.get("server_id") or "").strip(),
                "gpu_index": str(arguments.get("gpu_index") or run_config.get("gpu_index") or "").strip(),
                "message": "已生成任务提交包；当前上下文未启用受控 runtime，未入队。" if command else "等待 run.command。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "host.exec":
        runtime_result = context.submit_controlled_job(tool_id, arguments)
        if runtime_result:
            return json.dumps(runtime_result, ensure_ascii=False, indent=2)
        command = str(arguments.get("command") or arguments.get("cmd") or "").strip()
        return json.dumps(
            {
                "status": "ready" if command else "draft",
                "plan_only": True,
                "dry_run": True,
                "command": command,
                "server_id": str(arguments.get("server_id") or "").strip(),
                "gpu_index": "none",
                "message": "已生成主机命令计划；当前上下文未启用受控 runtime，未入队。" if command else "等待 command。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "execution.package":
        package = context.execution_package_payload()
        return json.dumps(
            {
                "status": "ready" if package["ready_to_execute"] else package["status"] or "draft",
                "workspace_id": str(workspace_snapshot.get("id") or "").strip(),
                "workspace_name": str(workspace_snapshot.get("name") or "").strip(),
                "package": package,
                "message": "执行包已就绪，可按工作流提交。" if package["ready_to_execute"] else "执行包仍有缺口，请查看 missing/backfill/readiness。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "log.read":
        workspace_id = str(workspace_snapshot.get("id") or "").strip()
        related_jobs = [job for job in context.jobs if context.job_workspace_id(job) == workspace_id]
        related_jobs.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
        latest = related_jobs[0] if related_jobs else {}
        return json.dumps(
            {
                "status": "found" if latest else "draft",
                "job_id": str(latest.get("id") or "").strip(),
                "job_status": str(latest.get("status") or "").strip(),
                "log_path": str(latest.get("log_path") or "").strip(),
                "message": "找到最近任务日志入口。" if latest else "当前工作台还没有关联任务日志。",
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_id == "artifact.read":
        return json.dumps(execute_artifact_read(context, arguments), ensure_ascii=False, indent=2)

    if tool_id == "artifact.write":
        try:
            result = apply_artifact_write(
                workspace_snapshot,
                node_id=str(arguments.get("node_id") or "").strip(),
                node_kind=str(arguments.get("node_kind") or "").strip(),
                label=str(arguments.get("label") or arguments.get("title") or "").strip(),
                path=str(arguments.get("path") or arguments.get("content_path") or "").strip(),
                content=str(arguments.get("content") or arguments.get("text") or "").strip(),
                output_key=str(arguments.get("output_key") or "").strip(),
                artifact_type=str(arguments.get("type") or arguments.get("artifact_type") or "note").strip(),
            )
            return json.dumps({"status": "written", **result}, ensure_ascii=False, indent=2)
        except ValueError as exc:
            return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

    if tool_id == "workflow.edit":
        patch = arguments.get("config")
        if not isinstance(patch, dict):
            patch = arguments.get("patch") if isinstance(arguments.get("patch"), dict) else {}
        try:
            result = apply_workflow_edit(
                workspace_snapshot,
                node_id=str(arguments.get("node_id") or "").strip(),
                node_kind=str(arguments.get("node_kind") or "").strip(),
                config_patch=patch,
            )
            return json.dumps({"status": "updated", **result}, ensure_ascii=False, indent=2)
        except ValueError as exc:
            return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

    if tool_id == "report.write":
        try:
            result = apply_artifact_write(
                workspace_snapshot,
                node_id=str(arguments.get("node_id") or "").strip(),
                node_kind=str(arguments.get("node_kind") or "eval.report").strip(),
                label=str(arguments.get("label") or arguments.get("title") or "report").strip(),
                path=str(arguments.get("path") or arguments.get("report_path") or "").strip(),
                content=str(arguments.get("content") or arguments.get("text") or arguments.get("report") or "").strip(),
                output_key=str(arguments.get("output_key") or "eval_report").strip(),
                artifact_type="report",
            )
            return json.dumps({"status": "written", **result}, ensure_ascii=False, indent=2)
        except ValueError as exc:
            return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

    if tool_id == "chat.write":
        message = arguments.get("message", "")
        return json.dumps({"status": "written", "message": message}, ensure_ascii=False, indent=2)

    side_effect = tool_side_effect(tool_id)
    meta = TOOL_SIDE_EFFECTS.get(str(tool_id or "").strip(), {})
    implemented = bool(meta.get("implemented"))
    if side_effect != ToolSideEffect.READ and not implemented:
        return json.dumps(
            {
                "status": "simulated",
                "tool": tool_id,
                "side_effect": side_effect.value,
                "arguments": arguments,
                "message": f"Tool '{tool_id}' is not implemented yet; returning simulated payload.",
            },
            ensure_ascii=False,
            indent=2,
        )
    return json.dumps(
        {
            "status": "simulated",
            "tool": tool_id,
            "arguments": arguments,
            "message": f"Tool '{tool_id}' executed (simulated)",
        },
        ensure_ascii=False,
        indent=2,
    )
