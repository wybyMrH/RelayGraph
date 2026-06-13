from __future__ import annotations

from ._deps import *  # noqa: F403
from ...infra.shell_pkg.jobs import conda_bootstrap


def workspace_execution_bundle_step(
    step_id: str,
    label: str,
    command: str,
    status: str,
    detail: str,
    *,
    node_kind: str = "",
    node_id: str = "",
    cwd: str = "",
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(step_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "command": compact_workspace_command(command, limit=260),
        "detail": str(detail or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "cwd": str(cwd or "").strip(),
        "env": {str(key): str(value) for key, value in (env or {}).items() if str(value).strip()},
    }

def workspace_execution_bundle_missing_item(
    field: str,
    label: str,
    status: str,
    action: str,
    *,
    node_kind: str = "",
    node_id: str = "",
    button_label: str = "",
    button_action: str = "",
    target_id: str = "",
    tab: str = "home",
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    action_name = str(button_action or ("select-execution-node" if node_id else "advance-workspace-automation")).strip()
    fix_action = {
        "label": str(button_label or "处理缺项").strip(),
        "action": action_name,
        "title": str(action or "").strip(),
        "detail": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "target_id": str(target_id or "workspaceExecutionBoard").strip(),
        "tab": str(tab or "home").strip(),
    }
    return {
        "field": str(field or "").strip(),
        "label": str(label or field or "").strip(),
        "status": normalized,
        "action": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "fix_action": fix_action,
    }

def workspace_checkout_command(source: dict[str, Any], workspace_dir: str) -> str:
    repo_url = str(source.get("repo_url") or "").strip()
    repo_ref = str(source.get("repo_ref") or "").strip()
    if not repo_url or not workspace_dir:
        return ""
    parent_dir = os.path.dirname(workspace_dir.rstrip("/")) or "."
    clone_name = os.path.basename(workspace_dir.rstrip("/")) or workspace_dir.rstrip("/")
    parts = ["git", "clone"]
    if repo_ref:
        parts.extend(["--branch", shlex.quote(repo_ref)])
    parts.extend([shlex.quote(repo_url), shlex.quote(clone_name)])
    return f"mkdir -p {shlex.quote(parent_dir)} && cd {shlex.quote(parent_dir)} && " + " ".join(parts)

def workspace_script_export_line(key: str, value: Any) -> str:
    normalized_key = re.sub(r"[^A-Za-z0-9_]", "_", str(key or "").strip().upper())
    if not normalized_key or normalized_key[0].isdigit():
        normalized_key = f"RELAYGRAPH_{normalized_key or 'VALUE'}"
    return f"export {normalized_key}={shlex.quote(str(value))}"

def workspace_execution_bundle_command_script(
    target: dict[str, Any],
    steps: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    delivery_contract: dict[str, Any],
    *,
    ready_to_execute: bool,
) -> dict[str, Any]:
    env_name = str(target.get("env_name") or "").strip()
    env_manager = str(target.get("env_manager") or "conda").strip().lower() or "conda"
    workspace_dir = str(target.get("workspace_dir") or "").strip()
    server_id = str(target.get("server_id") or "auto").strip() or "auto"
    gpu_index = str(target.get("gpu_index") or "auto").strip() or "auto"
    gpu_policy = str(target.get("gpu_policy") or "auto").strip() or "auto"
    mode = str(target.get("mode") or delivery_contract.get("mode") or "reproduce").strip() or "reproduce"
    label = str(target.get("label") or delivery_contract.get("label") or "自动复现/部署").strip()
    blocked = [
        {
            "field": str(item.get("field") or "").strip(),
            "label": str(item.get("label") or item.get("field") or "").strip(),
            "status": str(item.get("status") or "warning").strip(),
            "action": str(item.get("action") or "").strip(),
        }
        for item in missing
        if isinstance(item, dict) and str(item.get("status") or "") == "blocked"
    ]
    warnings = [
        {
            "field": str(item.get("field") or "").strip(),
            "label": str(item.get("label") or item.get("field") or "").strip(),
            "status": str(item.get("status") or "warning").strip(),
            "action": str(item.get("action") or "").strip(),
        }
        for item in missing
        if isinstance(item, dict) and str(item.get("status") or "") != "blocked"
    ]
    lines: list[str] = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# RelayGraph execution bundle",
        f"# mode: {mode} · {label}",
        f"# server: {server_id}",
        f"# gpu: {gpu_index} · policy={gpu_policy}",
    ]
    if workspace_dir:
        lines.append(workspace_script_export_line("RELAYGRAPH_WORKSPACE_DIR", workspace_dir))
    lines.append(workspace_script_export_line("RELAYGRAPH_SERVER_ID", server_id))
    lines.append(workspace_script_export_line("RELAYGRAPH_GPU_POLICY", gpu_policy))
    if env_name:
        lines.append(workspace_script_export_line("RELAYGRAPH_ENV_NAME", env_name))
    if gpu_index and gpu_index != "auto" and gpu_policy.lower() not in {"cpu", "none", "no_gpu"}:
        lines.append(workspace_script_export_line("CUDA_VISIBLE_DEVICES", gpu_index))
    elif gpu_policy.lower() in {"cpu", "none", "no_gpu"}:
        lines.append("unset CUDA_VISIBLE_DEVICES")
    if blocked or warnings:
        lines.extend(["", "# Missing inputs"])
        for item in [*blocked, *warnings]:
            field = item["field"] or item["label"] or "unknown"
            action = item["action"] or "等待补齐"
            lines.append(f"# - {field}: {action}")
    if env_name:
        lines.extend(["", "# Environment activation"])
        if env_manager == "conda":
            lines.append(conda_bootstrap(env_name))
        elif env_manager == "venv":
            env_path = shlex.quote(env_name)
            lines.extend(
                [
                    f"if [ -f {env_path}/bin/activate ]; then",
                    f"  . {env_path}/bin/activate",
                    'elif [ -n "${RELAYGRAPH_WORKSPACE_DIR:-}" ] && [ -f "$RELAYGRAPH_WORKSPACE_DIR/.venv/bin/activate" ]; then',
                    '  . "$RELAYGRAPH_WORKSPACE_DIR/.venv/bin/activate"',
                    "fi",
                ]
            )
        else:
            lines.append(f"# env_manager={env_manager}; activate {shlex.quote(env_name)} if your runner requires it.")
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "step").strip()
        label_text = str(step.get("label") or step_id).strip()
        status = str(step.get("status") or "draft").strip()
        command = str(step.get("command") or "").strip()
        cwd = str(step.get("cwd") or "").strip()
        env_values = step.get("env") if isinstance(step.get("env"), dict) else {}
        detail = str(step.get("detail") or "").strip()
        lines.extend(["", f"# Step: {label_text} ({step_id})", f"# status: {status}"])
        if cwd:
            lines.append(f"cd {shlex.quote(cwd)}")
        for key, value in env_values.items():
            value_text = str(value or "").strip()
            if value_text:
                lines.append(workspace_script_export_line(key, value_text))
        if command:
            lines.append(command)
        else:
            lines.append(f"# TODO {step_id}: {detail or '等待命令生成'}")
    text = "\n".join(lines).strip() + "\n"
    return {
        "shell": "bash",
        "status": "ready" if ready_to_execute and not blocked else "blocked" if blocked else "warning" if warnings else "draft",
        "ready": bool(ready_to_execute and not blocked),
        "text": text,
        "lines": lines,
        "blocked": blocked,
        "warnings": warnings,
        "summary": f"{len([step for step in steps if isinstance(step, dict)])} 个步骤 · {len(blocked)} 阻塞 · {len(warnings)} 提示",
    }

def workspace_execution_package_manifest(
    workspace: dict[str, Any],
    intent: dict[str, str],
    delivery_contract: dict[str, Any],
    target: dict[str, Any],
    steps: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    command_script: dict[str, Any],
    *,
    commands: dict[str, Any],
    paths: dict[str, Any],
    evidence: dict[str, Any],
    scheduler: dict[str, Any],
    dataset_discovery: dict[str, Any] | None = None,
    deployment_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    candidates = scheduler.get("candidates") if isinstance(scheduler.get("candidates"), list) else []
    dataset_plan = dataset_discovery if isinstance(dataset_discovery, dict) else {}
    deploy_plan = deployment_plan if isinstance(deployment_plan, dict) else {}
    return {
        "schema": "relaygraph.execution_package.v1",
        "workspace": {
            "id": str(workspace.get("id") or "").strip(),
            "name": str(workspace.get("name") or "").strip(),
            "template_id": str(workspace.get("template_id") or "").strip(),
            "template_name": str(workspace.get("template_name") or "").strip(),
        },
        "intent": copy.deepcopy(intent),
        "status": str(command_script.get("status") or "").strip(),
        "ready_to_execute": bool(command_script.get("ready")),
        "delivery_contract": copy.deepcopy(delivery_contract),
        "deployment_plan": copy.deepcopy(deploy_plan),
        "target": copy.deepcopy(target),
        "commands": copy.deepcopy(commands),
        "paths": copy.deepcopy(paths),
        "dataset_discovery": {
            "status": str(dataset_plan.get("status") or "").strip(),
            "summary": str(dataset_plan.get("summary") or "").strip(),
            "queries": copy.deepcopy(dataset_plan.get("queries") if isinstance(dataset_plan.get("queries"), list) else []),
            "local_roots": copy.deepcopy(dataset_plan.get("local_roots") if isinstance(dataset_plan.get("local_roots"), list) else []),
            "source_refs": copy.deepcopy(dataset_plan.get("source_refs") if isinstance(dataset_plan.get("source_refs"), list) else []),
            "expected_layout": str(dataset_plan.get("expected_layout") or "").strip(),
            "next_action": copy.deepcopy(dataset_plan.get("next_action") if isinstance(dataset_plan.get("next_action"), dict) else {}),
        },
        "steps": copy.deepcopy(steps),
        "missing": copy.deepcopy(missing),
        "evidence": copy.deepcopy(evidence),
        "scheduler": {
            "status": str(scheduler.get("status") or "").strip(),
            "mode": str(scheduler.get("mode") or "").strip(),
            "policy": str(scheduler.get("policy") or "").strip(),
            "summary": str(scheduler.get("summary") or "").strip(),
            "selected": copy.deepcopy(selected),
            "candidate_count": len(candidates),
        },
        "command_script": {
            "shell": str(command_script.get("shell") or "bash").strip(),
            "status": str(command_script.get("status") or "").strip(),
            "ready": bool(command_script.get("ready")),
            "summary": str(command_script.get("summary") or "").strip(),
            "text": str(command_script.get("text") or ""),
        },
    }

def workspace_execution_bundle_step_for_node(bundle: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    steps = bundle.get("steps") if isinstance(bundle.get("steps"), list) else []
    node_id = str(node.get("id") or "").strip()
    kind = str(node.get("kind") or "").strip()
    step_id_by_kind = {
        "repo.clone": "checkout",
        "path.resolve": "checkout",
        "env.infer": "setup",
        "env.prepare": "setup",
        "gpu.allocate": "run",
        "run.command": "run",
        "artifact.collect": "collect",
        "eval.report": "report",
    }
    return next(
        (
            step for step in steps
            if isinstance(step, dict)
            and (
                (node_id and str(step.get("node_id") or "").strip() == node_id)
                or (kind and str(step.get("node_kind") or "").strip() == kind)
                or str(step.get("id") or "").strip() == step_id_by_kind.get(kind, "")
            )
        ),
        {},
    )

def workspace_execution_bundle_job_metadata(automation: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
    bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
    if not bundle:
        return {}
    command_script = bundle.get("command_script") if isinstance(bundle.get("command_script"), dict) else {}
    step = workspace_execution_bundle_step_for_node(bundle, node)
    script_meta = {
        "shell": str(command_script.get("shell") or "bash").strip(),
        "status": str(command_script.get("status") or "").strip(),
        "ready": bool(command_script.get("ready")),
        "summary": str(command_script.get("summary") or "").strip(),
    }
    metadata: dict[str, Any] = {
        "status": str(bundle.get("status") or "").strip(),
        "ready_to_execute": bool(bundle.get("ready_to_execute")),
        "target": copy.deepcopy(bundle.get("target") if isinstance(bundle.get("target"), dict) else {}),
        "script": script_meta,
    }
    if step:
        metadata["step"] = {
            "id": str(step.get("id") or "").strip(),
            "label": str(step.get("label") or "").strip(),
            "status": str(step.get("status") or "").strip(),
            "node_kind": str(step.get("node_kind") or "").strip(),
            "node_id": str(step.get("node_id") or "").strip(),
            "cwd": str(step.get("cwd") or "").strip(),
            "env": copy.deepcopy(step.get("env") if isinstance(step.get("env"), dict) else {}),
        }
    if str(node.get("kind") or "").strip() == "run.command" and str(command_script.get("text") or "").strip():
        metadata["command_script"] = {
            **script_meta,
            "text": str(command_script.get("text") or ""),
        }
    return metadata

def workspace_scheduler_binding_metadata(
    automation: dict[str, Any] | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ..cockpit.scheduler import workspace_scheduler_values_from_selection

    automation = automation if isinstance(automation, dict) else {}
    config = config if isinstance(config, dict) else {}
    resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
    scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    values = workspace_scheduler_values_from_selection(scheduler) if scheduler else {}

    fallback_policy = str(config.get("gpu_policy") or "").strip().lower()
    fallback_gpu_index = str(config.get("gpu_index") if config.get("gpu_index") is not None else "").strip()
    fallback_server_id = str(config.get("server_id") or "").strip()
    cpu_mode = (
        str(values.get("mode") or selected.get("mode") or "").strip().lower() == "cpu"
        or str(values.get("gpu_policy") or fallback_policy).strip().lower() in {"cpu", "none", "no_gpu"}
        or fallback_gpu_index in {"cpu", "none", "no_gpu"}
    )
    gpu_index = str(values.get("gpu_index") or fallback_gpu_index or ("none" if cpu_mode else "auto")).strip()
    server_id = str(values.get("server_id") or selected.get("server_id") or fallback_server_id or "auto").strip() or "auto"
    min_free_memory_gib = str(values.get("min_free_memory_gib") or config.get("min_free_memory_gib") or "").strip()
    selected_host = selected.get("host") if isinstance(selected.get("host"), dict) else {}
    compact_selected = {
        "id": str(selected.get("id") or "").strip(),
        "status": str(selected.get("status") or "").strip(),
        "mode": str(selected.get("mode") or values.get("mode") or ("cpu" if cpu_mode else "gpu")).strip(),
        "score": safe_int(selected.get("score") if selected.get("score") is not None else values.get("score"), 0),
        "server_id": str(selected.get("server_id") or server_id).strip(),
        "server_name": str(selected.get("server_name") or "").strip(),
        "gpu_index": str(selected.get("gpu_index") if selected.get("gpu_index") is not None else gpu_index).strip(),
        "gpu_name": str(selected.get("gpu_name") or "").strip(),
        "gpu_state": str(selected.get("gpu_state") or "").strip(),
        "memory_free_mib": safe_int(selected.get("memory_free_mib"), 0),
        "memory_total_mib": safe_int(selected.get("memory_total_mib"), 0),
        "gpu_util": safe_int(selected.get("gpu_util"), 0),
        "process_count": safe_int(selected.get("process_count"), 0),
        "snapshot_age_seconds": safe_int(selected.get("snapshot_age_seconds"), 0),
        "collected_at": str(selected.get("collected_at") or "").strip(),
    }
    return {
        "status": str(scheduler.get("status") or values.get("status") or "draft").strip(),
        "mode": "cpu" if cpu_mode else str(values.get("mode") or scheduler.get("mode") or selected.get("mode") or "gpu").strip(),
        "policy": str(values.get("gpu_policy") or scheduler.get("policy") or fallback_policy or ("cpu" if cpu_mode else "auto")).strip(),
        "server_id": server_id,
        "gpu_index": "none" if cpu_mode else gpu_index,
        "min_free_memory_gib": min_free_memory_gib,
        "summary": str(scheduler.get("summary") or resource.get("summary") or "").strip(),
        "candidate_count": safe_int(scheduler.get("candidate_count"), 0),
        "ready_count": safe_int(scheduler.get("ready_count"), 0),
        "requested_server_id": str(scheduler.get("requested_server_id") or "").strip(),
        "requested_gpu_index": str(scheduler.get("requested_gpu_index") or "").strip(),
        "selected": compact_selected,
        "host": copy.deepcopy(selected_host),
        "reasons": copy.deepcopy(selected.get("reasons") if isinstance(selected.get("reasons"), list) else []),
        "warnings": copy.deepcopy(selected.get("warnings") if isinstance(selected.get("warnings"), list) else []),
    }

def workspace_execution_bundle_result(automation: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
    bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
    if not bundle:
        return {}
    command_script = bundle.get("command_script") if isinstance(bundle.get("command_script"), dict) else {}
    package_manifest = bundle.get("package_manifest") if isinstance(bundle.get("package_manifest"), dict) else {}
    return {
        "status": str(bundle.get("status") or "").strip(),
        "ready_to_execute": bool(bundle.get("ready_to_execute")),
        "target": copy.deepcopy(bundle.get("target") if isinstance(bundle.get("target"), dict) else {}),
        "script": {
            "shell": str(command_script.get("shell") or "bash").strip(),
            "status": str(command_script.get("status") or "").strip(),
            "ready": bool(command_script.get("ready")),
            "summary": str(command_script.get("summary") or "").strip(),
        },
        "package_manifest": copy.deepcopy(package_manifest),
        "job_count": len(jobs),
        "job_ids": [str(job.get("id") or "").strip() for job in jobs if isinstance(job, dict) and str(job.get("id") or "").strip()],
    }
