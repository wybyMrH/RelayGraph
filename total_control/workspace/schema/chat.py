from __future__ import annotations

import copy
import re
import uuid
from typing import Any

from ...constants import *  # noqa: F403
from ...utils import *  # noqa: F403
from ..errors import WorkspaceWorkflowReadinessError
from ..execution.agent_trace import normalize_agent_execution_trace
from .agents_tools import normalize_workspace_tool


def normalize_workspace_context_reflection(
    value: Any,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    summary = str(current.get("summary") or current.get("text") or previous.get("summary") or "").strip()
    if not summary:
        return {}
    status = str(current.get("status") or previous.get("status") or "suggested").strip().lower()
    if status not in {"suggested", "accepted", "dismissed"}:
        status = "suggested"
    source = current.get("source") if isinstance(current.get("source"), dict) else previous.get("source") if isinstance(previous.get("source"), dict) else {}
    confidence = safe_float(current.get("confidence") if current.get("confidence") is not None else previous.get("confidence"), 0.0)
    if confidence < 0:
        confidence = 0.0
    if confidence > 1:
        confidence = 1.0
    return {
        "id": str(current.get("id") or previous.get("id") or f"ctxref-{uuid.uuid4().hex[:8]}").strip(),
        "summary": summary[:500],
        "status": status,
        "confidence": round(confidence, 2),
        "source": {
            "type": str(source.get("type") or "chat").strip() or "chat",
            "message_id": str(source.get("message_id") or "").strip(),
            "user_message_id": str(source.get("user_message_id") or "").strip(),
            "agent_execution_id": str(source.get("agent_execution_id") or "").strip(),
        },
        "created_at": str(current.get("created_at") or previous.get("created_at") or now_iso()).strip() or now_iso(),
        "accepted_at": str(current.get("accepted_at") or previous.get("accepted_at") or "").strip(),
        "accepted_context_block": str(current.get("accepted_context_block") or previous.get("accepted_context_block") or "").strip(),
        "dismissed_at": str(current.get("dismissed_at") or previous.get("dismissed_at") or "").strip(),
        "dismissed_reason": str(current.get("dismissed_reason") or previous.get("dismissed_reason") or "").strip()[:240],
    }



def normalize_workspace_chat_message(
    value: Any,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    role = str(current.get("role") or previous.get("role") or "user").strip().lower()
    if role not in {"system", "user", "assistant"}:
        role = "user"
    text = str(current.get("text") or previous.get("text") or "").strip()
    status = str(current.get("status") or previous.get("status") or "completed").strip().lower()
    if status not in {"pending", "streaming", "completed", "failed"}:
        status = "completed"
    return {
        "id": str(current.get("id") or previous.get("id") or f"chat-{uuid.uuid4().hex[:8]}").strip(),
        "role": role,
        "text": text,
        "status": status,
        "error": str(current.get("error") or previous.get("error") or "").strip(),
        "agent_id": safe_id(str(current.get("agent_id") or previous.get("agent_id") or ""))
        if str(current.get("agent_id") or previous.get("agent_id") or "").strip()
        else "",
        "agent_name": str(current.get("agent_name") or previous.get("agent_name") or "").strip(),
        "agent_execution": normalize_agent_execution_trace(
            current.get("agent_execution"),
            existing=previous.get("agent_execution") if isinstance(previous.get("agent_execution"), dict) else None,
        ),
        "context_reflection": normalize_workspace_context_reflection(
            current.get("context_reflection"),
            existing=previous.get("context_reflection") if isinstance(previous.get("context_reflection"), dict) else None,
        ),
        "created_at": str(current.get("created_at") or previous.get("created_at") or now_iso()).strip() or now_iso(),
        "updated_at": str(current.get("updated_at") or previous.get("updated_at") or current.get("created_at") or previous.get("created_at") or now_iso()).strip() or now_iso(),
    }

def normalize_workspace_chat(
    value: Any,
    *,
    existing: Any = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id: dict[str, dict[str, Any]] = {}
    for item in previous_list:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            previous_by_id[str(item.get("id") or "").strip()] = item
    raw_items = value if isinstance(value, list) else previous_list
    messages: list[dict[str, Any]] = []
    for item in raw_items[-200:]:
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        message = normalize_workspace_chat_message(item, existing=existing_item)
        if not message["text"] and message.get("status") not in {"pending", "streaming"}:
            continue
        messages.append(message)
    return messages[-200:]

def make_workspace_chat_message(
    role: str,
    text: str,
    *,
    agent_id: str = "",
    agent_name: str = "",
    status: str = "completed",
    error: str = "",
) -> dict[str, Any]:
    return normalize_workspace_chat_message(
        {
            "role": role,
            "text": text,
            "status": status,
            "error": error,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    )

def workspace_agent_name(workspace: dict[str, Any], agent_id: str) -> str:
    target = str(agent_id or "").strip()
    if not target:
        return ""
    agents = workspace.get("agents") if isinstance(workspace.get("agents"), list) else []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        if str(agent.get("id") or "").strip() == target:
            return str(agent.get("name") or target).strip() or target
    return target

def workspace_source_brief(workspace: dict[str, Any]) -> str:
    brief = str(workspace.get("brief") or "").strip()
    if brief:
        return brief
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    return (
        str(source.get("idea_text") or "").strip()
        or str(source.get("paper_url") or "").strip()
        or str(source.get("repo_url") or "").strip()
    )

def build_workspace_chat_reply(
    workspace: dict[str, Any],
    user_text: str,
    *,
    agent_id: str = "",
) -> str:
    lines: list[str] = []
    agent_name = workspace_agent_name(workspace, agent_id)
    if agent_name:
        lines.append(f"已记录到 {agent_name} 的上下文。")
    brief = workspace_source_brief(workspace)
    if brief:
        first_line = brief.splitlines()[0].strip()
        if first_line:
            lines.append(f"当前项目目标：{first_line[:120]}")
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    flow = [str(node.get("title") or node.get("kind") or "").strip() for node in nodes if isinstance(node, dict)]
    flow = [item for item in flow if item]
    if flow:
        lines.append(f"现有工作流：{' -> '.join(flow[:4])}{' ...' if len(flow) > 4 else ''}")
    next_node = next(
        (
            node for node in nodes
            if isinstance(node, dict) and str(node.get("status") or "draft") in {"draft", "ready", "running", "blocked"}
        ),
        nodes[0] if nodes else {},
    )
    if isinstance(next_node, dict) and next_node:
        node_name = str(next_node.get("title") or next_node.get("kind") or "").strip()
        if node_name:
            lines.append(f"建议先检查节点：{node_name}")
    user_line = user_text.splitlines()[0].strip()
    if user_line:
        lines.append(f"你的新输入已归档：{user_line[:120]}")
    lines.append("外部模型调用还未接入，这里先保存对话、agent 路由和项目上下文。")
    return "\n".join(lines)

def workspace_agent_by_id(workspace: dict[str, Any], agent_id: str) -> dict[str, Any] | None:
    target = str(agent_id or "").strip()
    if not target:
        return None
    agents = workspace.get("agents") if isinstance(workspace.get("agents"), list) else []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        if str(agent.get("id") or "").strip() == target:
            return agent
    return None

def workspace_tool_index(workspace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tools = workspace.get("tools") if isinstance(workspace.get("tools"), list) else []
    indexed: dict[str, dict[str, Any]] = {}
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            continue
        normalized = normalize_workspace_tool(tool, index=index, existing=tool)
        tool_id = str(normalized.get("id") or "").strip()
        if tool_id and tool_id not in indexed:
            indexed[tool_id] = normalized
    return indexed

def workspace_agent_focus_node(
    workspace: dict[str, Any],
    agent: dict[str, Any],
    *,
    requested_node_kind: str = "",
) -> dict[str, Any] | None:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    target_kind = str(requested_node_kind or "").strip()
    if target_kind:
        for node in nodes:
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == target_kind:
                return node

    agent_id = str(agent.get("id") or "").strip()
    if agent_id:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
            if str(handler.get("agent_id") or "").strip() == agent_id:
                return node

    role = str(agent.get("role") or "").strip().lower()
    role_hints = {
        "planner": ["source.repo", "source.paper", "source.idea", "research.search"],
        "researcher": ["research.search", "dataset.find", "source.paper", "source.idea"],
        "repo_scout": ["repo.clone", "path.resolve", "repo.inspect", "source.repo"],
        "gpu_scout": ["gpu.allocate", "run.command", "env.prepare"],
        "env_builder": ["env.infer", "env.prepare", "repo.inspect"],
        "runner": ["run.command"],
        "evaluator": ["artifact.collect", "eval.report", "run.command"],
        "watcher": ["run.command", "gpu.allocate", "eval.report"],
        "reporter": ["eval.report", "artifact.collect", "notify.user"],
    }
    for kind in role_hints.get(role, []):
        for node in nodes:
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == kind:
                return node

    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("status") or "draft").strip() in {"draft", "ready", "running", "blocked"}:
            return node

    return next((node for node in nodes if isinstance(node, dict)), None)

def build_workspace_agent_debug(
    workspace: dict[str, Any],
    agent: dict[str, Any],
    *,
    input_text: str = "",
    requested_node_kind: str = "",
    requested_tool_ids: list[str] | None = None,
) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    model = workspace.get("model") if isinstance(workspace.get("model"), dict) else {}
    chat = workspace.get("chat") if isinstance(workspace.get("chat"), list) else []
    tool_map = workspace_tool_index(workspace)
    requested_tool_set = {
        str(item or "").strip()
        for item in (requested_tool_ids or [])
        if str(item or "").strip()
    }
    allowed_tool_ids = [
        tool_id
        for tool_id in parse_tag_list(agent.get("tools", []))
        if tool_id in tool_map and (not requested_tool_set or tool_id in requested_tool_set)
    ]
    allowed_tools = [tool_map[tool_id] for tool_id in allowed_tool_ids]
    focus_node = workspace_agent_focus_node(
        workspace,
        agent,
        requested_node_kind=requested_node_kind,
    )
    brief = workspace_source_brief(workspace)
    source_summary = (
        str(source.get("repo_url") or "").strip()
        or str(source.get("paper_url") or "").strip()
        or str(source.get("idea_text") or "").strip()
        or brief
    )
    routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
    workspace_profile_id = str(model.get("provider_profile_id") or "").strip()
    agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
    effective_profile_id = workspace_profile_id
    profile_source = "workspace_default" if workspace_profile_id else "unconfigured"
    if routing_mode == "agent_override" and agent_profile_id:
        effective_profile_id = agent_profile_id
        profile_source = "agent_override"

    focus_title = ""
    focus_kind = ""
    focus_summary = ""
    focus_status = ""
    focus_handler = {}
    if isinstance(focus_node, dict):
        focus_title = str(focus_node.get("title") or focus_node.get("kind") or "").strip()
        focus_kind = str(focus_node.get("kind") or "").strip()
        focus_status = str(focus_node.get("status") or "").strip()
        focus_summary = str((focus_node.get("config") or {}).get("goal") or "").strip()
        if not focus_summary:
            focus_summary = str((focus_node.get("config") or {}).get("run_command") or "").strip()
        if not focus_summary:
            focus_summary = str((focus_node.get("config") or {}).get("questions") or "").strip()
        focus_handler = focus_node.get("handler") if isinstance(focus_node.get("handler"), dict) else {}

    input_line = str(input_text or "").strip().splitlines()[0].strip() if str(input_text or "").strip() else ""
    role = str(agent.get("role") or "").strip().lower()
    plan: list[str] = []
    if input_line:
        plan.append(f"先吸收本轮输入：{input_line[:120]}")
    if focus_title:
        plan.append(f"聚焦节点“{focus_title}”，先明确这个节点当前缺什么输入、要交付什么输出。")
    role_plan_map = {
        "planner": "把当前目标拆成节点、交接说明和需要人工确认的检查点。",
        "researcher": "先检索论文、候选仓库、依赖说明和运行方式，再回写可执行线索。",
        "repo_scout": "优先读仓库入口、依赖文件、配置目录和 README，确认真正的运行入口。",
        "gpu_scout": "先判断哪台主机和哪块 GPU 适合当前任务，再补工作目录和资源提示。",
        "env_builder": "优先核对环境管理方式、Python 版本和安装命令，减少首次运行失败。",
        "runner": "把节点配置转成真实任务，先保证命令、目录、环境和 GPU 策略都闭合。",
        "evaluator": "围绕日志、指标和产物路径整理评估结果，并补出最终结论。",
        "watcher": "盯住日志、失败信号和资源异常，及时把风险和错误回推给用户。",
        "reporter": "把过程、结论、风险和下一步建议整理成可交付摘要。",
    }
    if role_plan_map.get(role):
        plan.append(role_plan_map[role])
    tool_categories = list(dict.fromkeys(str(tool.get("category") or "general") for tool in allowed_tools))
    category_hints = {
        "research": "如需补资料，优先用检索类工具拉齐 repo、论文和 issue 线索。",
        "repo": "仓库类工具可以帮助确认入口、目录结构和默认参数。",
        "env": "环境类工具适合先补 conda / venv、安装依赖和 Python 版本。",
        "gpu": "GPU 类工具适合先看利用率、显存和资源分配策略。",
        "run": "运行类工具适合把当前步骤正式送进任务队列。",
        "artifact": "产物类工具适合把结果整理回项目上下文或报告。",
        "notify": "通知类工具适合把阶段结果或异常同步给用户。",
        "workflow": "工作流类工具适合继续编辑节点或调整交接关系。",
        "chat": "对话类工具适合把本轮理解和结论写回项目上下文。",
    }
    for category in tool_categories:
        hint = category_hints.get(category)
        if hint and hint not in plan:
            plan.append(hint)
    if not plan:
        plan.append("先检查项目目标、工作流节点和当前 agent 边界，再决定下一步。")

    warnings: list[str] = []
    if agent.get("enabled") is False:
        warnings.append("这个 agent 当前处于停用状态。")
    if not str(agent.get("prompt") or "").strip():
        warnings.append("这个 agent 还没有提示词，调试结果只能基于角色和工具边界推断。")
    if not allowed_tools:
        warnings.append("这个 agent 目前没有可用工具。")
    if routing_mode != "agent_override" and agent_profile_id and not workspace_profile_id:
        warnings.append("项目路由还是 workspace_default，agent 上的模型覆盖暂时不会生效。")
    if requested_tool_set and not allowed_tools:
        warnings.append("请求调试的工具与当前 agent allowlist 没有交集。")
    if not focus_node:
        warnings.append("当前没有找到合适的聚焦节点。")

    next_actions: list[str] = []
    if not str(input_text or "").strip():
        next_actions.append("补一段更具体的调试输入，让 agent 有明确本轮任务。")
    if not str(agent.get("prompt") or "").strip():
        next_actions.append("先补提示词，明确该角色应该产出什么。")
    if not allowed_tools:
        next_actions.append("先给这个 agent 绑定至少一类工具。")
    if not effective_profile_id:
        next_actions.append("给项目或 agent 配一个 Provider Profile。")
    if isinstance(focus_node, dict):
        handler_agent_id = str(focus_handler.get("agent_id") or "").strip()
        if handler_agent_id and handler_agent_id != str(agent.get("id") or "").strip():
            next_actions.append("如果要让这个 agent 真接手当前节点，记得把节点绑定到它。")
        if focus_kind == "run.command" and not str((focus_node.get("config") or {}).get("run_command") or "").strip():
            next_actions.append("当前运行节点还没有命令，先补 run_command。")

    prompt_lines = [
        f"角色：{str(agent.get('name') or agent.get('id') or '').strip()} ({str(agent.get('role') or '').strip()})",
        str(agent.get("prompt") or "").strip(),
        f"项目目标：{brief}" if brief else "",
        f"当前聚焦节点：{focus_title} ({focus_kind})" if focus_title and focus_kind else "",
        f"输入摘要：{input_line}" if input_line else "",
    ]
    assigned_nodes = []
    for node in workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        if str(handler.get("agent_id") or "").strip() != str(agent.get("id") or "").strip():
            continue
        assigned_nodes.append(
            {
                "id": str(node.get("id") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or "").strip(),
                "kind": str(node.get("kind") or "").strip(),
                "status": str(node.get("status") or "").strip(),
            }
        )

    return {
        "workspace_id": str(workspace.get("id") or "").strip(),
        "workspace_name": str(workspace.get("name") or "").strip(),
        "generated_at": now_iso(),
        "agent": {
            "id": str(agent.get("id") or "").strip(),
            "name": str(agent.get("name") or "").strip(),
            "role": str(agent.get("role") or "").strip(),
            "enabled": bool(agent.get("enabled", True)),
            "provider_profile_id": agent_profile_id,
        },
        "input_text": str(input_text or "").strip(),
        "prompt_preview": "\n".join([line for line in prompt_lines if line]).strip(),
        "allowed_tools": allowed_tools,
        "assigned_nodes": assigned_nodes[:8],
        "focus_node": {
            "id": str(focus_node.get("id") or "").strip() if isinstance(focus_node, dict) else "",
            "title": focus_title,
            "kind": focus_kind,
            "status": focus_status,
            "summary": focus_summary,
            "handler_mode": str(focus_handler.get("mode") or "").strip(),
            "handler_agent_id": str(focus_handler.get("agent_id") or "").strip(),
        },
        "context": {
            "source_type": str(source.get("type") or "").strip(),
            "source_summary": source_summary,
            "brief": brief,
            "workspace_dir": str(workspace.get("workspace_dir") or "").strip(),
            "reference_count": len(workspace.get("references")) if isinstance(workspace.get("references"), list) else 0,
            "node_count": len(workspace.get("nodes")) if isinstance(workspace.get("nodes"), list) else 0,
            "chat_message_count": len(chat),
        },
        "model": {
            "routing_mode": routing_mode,
            "workspace_profile_id": workspace_profile_id,
            "agent_profile_id": agent_profile_id,
            "effective_profile_id": effective_profile_id,
            "source": profile_source,
            "chat_agent_id": str(model.get("chat_agent_id") or "").strip(),
        },
        "plan": plan[:6],
        "next_actions": next_actions[:5],
        "warnings": warnings[:5],
    }
