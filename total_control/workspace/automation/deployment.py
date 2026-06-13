from __future__ import annotations

from ._deps import *  # noqa: F403
from .helpers import compact_contract_items


def workspace_delivery_contract(
    workspace: dict[str, Any],
    intent: dict[str, str],
    *,
    run_command: str = "",
    setup_command: str = "",
    artifact_paths: list[str] | None = None,
    metric_paths: list[str] | None = None,
) -> dict[str, Any]:
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    references = inputs.get("references") if isinstance(inputs.get("references"), list) else []
    context_blocks = inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else []
    goal_text = str(inputs.get("goal_text") or workspace.get("brief") or "").strip()
    mode = str(intent.get("mode") or "reproduce")
    criteria: list[str] = []
    criteria.extend(context_blocks)
    if mode in {"reproduce", "mixed"}:
        criteria.extend(
            [
                "记录可复现命令、依赖安装方式、数据路径和 GPU/服务器选择。",
                "收集指标、日志、checkpoint 或输出样例，能说明结果是否达到预期。",
            ]
        )
    if mode in {"deploy", "mixed"}:
        criteria.extend(
            [
                "给出服务启动命令、端口/API/入口说明和最小健康检查方式。",
                "保留部署日志、配置路径、回滚或停止方式，避免只留下一个后台进程。",
            ]
        )
    if run_command:
        criteria.append(f"核心命令可执行：{run_command}")
    if setup_command:
        criteria.append(f"环境准备可复用：{setup_command}")
    artifact_values = compact_contract_items([*(artifact_paths or []), *(metric_paths or [])], limit=4)
    deliverables = compact_contract_items(
        [
            *(artifact_paths or []),
            *(metric_paths or []),
            "运行日志",
            "执行报告",
            "复跑命令与环境摘要",
        ],
        limit=6,
    )
    safety_checks = compact_contract_items(
        [
            "先跑安全发现链，再提交完整运行或部署命令。",
            "运行前确认 workspace_dir、run_command、server/GPU、env 和 artifact_paths。",
            "长任务必须落到 tmux/job 队列，保留日志路径。",
            "部署模式需要有健康检查或 smoke test，避免只看进程存在。",
        ],
        limit=5,
    )
    criteria = compact_contract_items(criteria, limit=6)
    status = "ready" if run_command and (artifact_values or criteria) else "warning" if goal_text or criteria else "draft"
    return {
        "mode": mode,
        "label": str(intent.get("label") or "自动复现/部署"),
        "status": status,
        "goal": compact_workspace_command(goal_text, limit=220),
        "acceptance_criteria": criteria,
        "deliverables": deliverables,
        "safety_checks": safety_checks,
        "reference_count": len(references),
        "context_count": len(context_blocks),
        "summary": f"{len(criteria)} 条验收项 · {len(deliverables)} 个交付物 · {len(safety_checks)} 条安全检查",
    }

def workspace_deployment_health_path(workspace: dict[str, Any], run_command: str) -> str:
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    text = " ".join(
        [
            str(inputs.get("goal_text") or ""),
            " ".join(str(item or "") for item in (inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else [])),
            " ".join(str(item or "") for item in (inputs.get("references") if isinstance(inputs.get("references"), list) else [])),
            str(source.get("idea_text") or ""),
            str(workspace.get("brief") or ""),
            str(run_command or ""),
        ]
    )
    matches = re.findall(r"(?<![A-Za-z0-9_])/(?:api/)?(?:health|ready|readiness|live|liveness|ping|status)(?:/[A-Za-z0-9_.-]+)?", text, flags=re.IGNORECASE)
    if matches:
        return matches[0]
    return "/health"

def workspace_deployment_service_kind(run_command: str) -> str:
    lower = str(run_command or "").lower()
    if "docker compose" in lower or "docker-compose" in lower:
        return "docker-compose"
    if "uvicorn" in lower:
        return "asgi"
    if "gunicorn" in lower:
        return "gunicorn"
    if "streamlit" in lower:
        return "streamlit"
    if "gradio" in lower:
        return "gradio"
    if "flask run" in lower:
        return "flask"
    if "vite" in lower or "npm run dev" in lower or "npm run start" in lower or "pnpm" in lower:
        return "web"
    if "serve" in lower or "server" in lower or " app.py" in lower or lower.startswith("python app.py"):
        return "service"
    return "command"

def workspace_deployment_port(run_command: str) -> str:
    text = str(run_command or "")
    patterns = [
        r"(?:--port|-p)\s+([0-9]{2,5})",
        r"(?:PORT|port)=([0-9]{2,5})",
        r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):([0-9]{2,5})",
        r"\s-p\s+[0-9.]*:([0-9]{2,5})(?::|/|\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""

def workspace_deployment_host(run_command: str) -> str:
    text = str(run_command or "")
    match = re.search(r"--host\s+([^\s]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(?:HOST|host)=([^\s]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "127.0.0.1"

def workspace_deployment_stop_command(run_command: str, service_kind: str) -> str:
    command = str(run_command or "").strip()
    if not command:
        return ""
    if service_kind == "docker-compose":
        return "docker compose down || docker-compose down"
    try:
        tokens = shlex.split(command, posix=True) if command else []
    except ValueError:
        tokens = []
    process_hint = " ".join(tokens[:3]) if tokens else command[:80]
    return f"pkill -f {shlex.quote(process_hint)}"

def workspace_deployment_plan(
    workspace: dict[str, Any],
    intent: dict[str, str],
    *,
    run_command: str = "",
    workspace_dir: str = "",
    target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = str(intent.get("mode") or "reproduce").strip() or "reproduce"
    service_kind = workspace_deployment_service_kind(run_command)
    relevant = mode in {"deploy", "mixed"} or service_kind not in {"command"}
    port = workspace_deployment_port(run_command)
    host = workspace_deployment_host(run_command)
    health_path = workspace_deployment_health_path(workspace, run_command) if relevant else ""
    health_url = f"http://127.0.0.1:{port}{health_path}" if port and health_path else ""
    smoke_command = f"curl -fsS {shlex.quote(health_url)}" if health_url else ""
    observe_commands = compact_contract_items(
        [
            f"ss -ltnp | grep ':{port}' || true" if port else "",
            smoke_command,
            "docker compose ps || docker-compose ps" if service_kind == "docker-compose" else "",
        ],
        limit=4,
    )
    stop_command = workspace_deployment_stop_command(run_command, service_kind) if relevant else ""
    missing: list[dict[str, str]] = []
    if relevant and not run_command:
        missing.append({"field": "run_command", "label": "服务启动命令", "status": "blocked", "action": "补 run.command，例如 uvicorn/gunicorn/docker compose。"})
    if relevant and not workspace_dir:
        missing.append({"field": "workspace_dir", "label": "部署目录", "status": "warning", "action": "补 workspace_dir，便于部署命令、日志和停止命令可复用。"})
    if relevant and service_kind != "docker-compose" and not port:
        missing.append({"field": "port", "label": "服务端口", "status": "warning", "action": "在目标或命令里补 --port/PORT，才能生成健康检查。"})
    if relevant and port and not health_path:
        missing.append({"field": "health_path", "label": "健康检查路径", "status": "warning", "action": "补 /health、/ready、/ping 或 smoke test 路径。"})
    blocked = any(str(item.get("status") or "") == "blocked" for item in missing)
    status = "blocked" if blocked else "warning" if missing and relevant else "ready" if relevant and run_command else "draft"
    target_info = target if isinstance(target, dict) else {}
    first_missing = missing[0] if missing else {}
    first_field = str(first_missing.get("field") or "").strip()
    run_node = workspace_node_by_kind(workspace, "run.command")
    path_node = workspace_node_by_kind(workspace, "path.resolve") or workspace_node_by_kind(workspace, "repo.clone")
    next_node_id = (
        str(path_node.get("id") or "").strip()
        if first_field == "workspace_dir" and path_node
        else str(run_node.get("id") or "").strip()
        if run_node
        else ""
    )
    return {
        "schema": "relaygraph.deployment_plan.v1",
        "relevant": bool(relevant),
        "status": status,
        "mode": mode,
        "service_kind": service_kind,
        "workspace_dir": str(workspace_dir or "").strip(),
        "server_id": str(target_info.get("server_id") or "auto").strip() or "auto",
        "gpu_policy": str(target_info.get("gpu_policy") or "auto").strip() or "auto",
        "host": host,
        "port": port,
        "health_path": health_path,
        "health_url": health_url,
        "start_command": compact_workspace_command(run_command, limit=220),
        "smoke_test_command": smoke_command,
        "observe_commands": observe_commands,
        "stop_command": stop_command,
        "missing": missing,
        "summary": "非部署目标" if not relevant else f"{service_kind} · {port or '端口待定'} · {health_path or '健康检查待定'}",
        "next_action": {
            "label": "补部署入口" if blocked else "补健康检查" if missing else "验证部署",
            "action": "select-execution-node" if blocked or missing else "run-selected-workspace",
            "status": status,
            "title": "部署计划待补齐" if blocked or missing else "部署计划可验证",
            "detail": str((missing[0] if missing else {}).get("action") or "运行服务后执行 smoke test，并保留观察/停止命令。"),
            "node_id": next_node_id,
        },
    }
