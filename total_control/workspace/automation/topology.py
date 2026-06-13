from __future__ import annotations

from ._deps import *  # noqa: F403
from .run_plan import workspace_node_required_tool_id, workspace_run_node_phase, workspace_run_phase_label
from ..schema.agents_tools import normalize_workspace_agents, normalize_workspace_tools
from ..schema.recipe import normalize_workspace_model


def workspace_model_route_for_agent(model: dict[str, Any], agent: dict[str, Any] | None) -> dict[str, str]:
    routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
    workspace_profile_id = str(model.get("provider_profile_id") or "").strip()
    agent_profile_id = str((agent or {}).get("provider_profile_id") or "").strip()
    if routing_mode == "agent_override" and agent_profile_id:
        return {
            "status": "ready",
            "routing_mode": routing_mode,
            "source": "agent_override",
            "effective_profile_id": agent_profile_id,
            "workspace_profile_id": workspace_profile_id,
            "agent_profile_id": agent_profile_id,
            "label": "Agent 覆盖",
        }
    if workspace_profile_id:
        return {
            "status": "ready",
            "routing_mode": routing_mode,
            "source": "workspace_default",
            "effective_profile_id": workspace_profile_id,
            "workspace_profile_id": workspace_profile_id,
            "agent_profile_id": agent_profile_id,
            "label": "项目默认",
        }
    return {
        "status": "warning",
        "routing_mode": routing_mode,
        "source": "unconfigured",
        "effective_profile_id": "",
        "workspace_profile_id": workspace_profile_id,
        "agent_profile_id": agent_profile_id,
        "label": "未配置 Profile",
    }

def workspace_agent_topology_gap(
    gap_type: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    phase: str = "",
    node_id: str = "",
    node_kind: str = "",
    agent_id: str = "",
    tool_id: str = "",
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "type": str(gap_type or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "phase": str(phase or "").strip(),
        "node_id": str(node_id or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "agent_id": str(agent_id or "").strip(),
        "tool_id": str(tool_id or "").strip(),
    }

def workspace_topology_status(gaps: list[dict[str, Any]]) -> str:
    statuses = {str(item.get("status") or "") for item in gaps if isinstance(item, dict)}
    if statuses.intersection({"blocked", "failed"}):
        return "blocked"
    if statuses.intersection({"warning", "draft"}):
        return "warning"
    return "ready"

def derive_workspace_agent_topology(workspace: dict[str, Any], run_plan: dict[str, Any]) -> dict[str, Any]:
    tools = normalize_workspace_tools(workspace.get("tools"))
    tool_index = {
        str(tool.get("id") or "").strip(): tool
        for tool in tools
        if isinstance(tool, dict) and str(tool.get("id") or "").strip()
    }
    agents = normalize_workspace_agents(workspace.get("agents"), tool_ids=list(tool_index.keys()))
    agent_index = {
        str(agent.get("id") or "").strip(): agent
        for agent in agents
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    model = normalize_workspace_model(workspace.get("model"), existing=workspace.get("model"))
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    plan_nodes = {
        str(item.get("id") or "").strip(): item
        for item in (run_plan.get("nodes") if isinstance(run_plan.get("nodes"), list) else [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    phase_order = ["source", "discover", "setup", "run", "collect", "report", "other"]
    stage_index: dict[str, dict[str, Any]] = {}
    stage_agent_ids: dict[str, set[str]] = {}
    stage_tool_ids: dict[str, set[str]] = {}
    assigned_agent_ids: set[str] = set()
    required_tool_ids: set[str] = set()
    topology_gaps: list[dict[str, Any]] = []
    missing_agent_count = 0

    def stage_for_phase(phase: str) -> dict[str, Any]:
        phase_id = phase if phase in phase_order else "other"
        if phase_id not in stage_index:
            stage_index[phase_id] = {
                "id": phase_id,
                "label": workspace_run_phase_label(phase_id),
                "status": "ready",
                "node_count": 0,
                "assigned_node_count": 0,
                "node_kinds": [],
                "nodes": [],
                "agents": [],
                "tools": [],
                "model_profiles": [],
                "gaps": [],
            }
            stage_agent_ids[phase_id] = set()
            stage_tool_ids[phase_id] = set()
        return stage_index[phase_id]

    def add_gap(stage: dict[str, Any], gap: dict[str, Any]) -> None:
        stage["gaps"].append(gap)
        topology_gaps.append(gap)

    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            continue
        phase = workspace_run_node_phase(kind)
        stage = stage_for_phase(phase)
        phase_id = str(stage["id"])
        plan_node = plan_nodes.get(str(node.get("id") or "").strip(), {})
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        mode = str(handler.get("mode") or "agent").strip() or "agent"
        agent_id = str(handler.get("agent_id") or plan_node.get("agent_id") or "").strip()
        agent = agent_index.get(agent_id)
        required_tool_id = workspace_node_required_tool_id(kind)
        if required_tool_id:
            required_tool_ids.add(required_tool_id)
            stage_tool_ids[phase_id].add(required_tool_id)
        stage["node_count"] = safe_int(stage.get("node_count"), 0) + 1
        if kind not in stage["node_kinds"]:
            stage["node_kinds"].append(kind)
        if len(stage["nodes"]) < 8:
            stage["nodes"].append(
                {
                    "id": str(node.get("id") or "").strip(),
                    "kind": kind,
                    "title": str(node.get("title") or kind).strip(),
                    "status": str(plan_node.get("status") or "warning").strip(),
                    "agent_id": agent_id,
                    "agent_name": str(handler.get("name") or (agent.get("name") if agent else "") or plan_node.get("agent_name") or "").strip(),
                    "required_tool_id": required_tool_id,
                }
            )

        if mode != "human" and not agent_id:
            missing_agent_count += 1
            add_gap(
                stage,
                workspace_agent_topology_gap(
                    "missing_agent",
                    "blocked",
                    "节点缺 Agent",
                    f"{str(node.get('title') or kind).strip()} 没有绑定执行 Agent。",
                    "在配置中心把节点绑定到对应 Agent。",
                    phase=phase_id,
                    node_id=str(node.get("id") or "").strip(),
                    node_kind=kind,
                ),
            )
            continue
        if not agent_id:
            continue
        if not agent:
            add_gap(
                stage,
                workspace_agent_topology_gap(
                    "unknown_agent",
                    "blocked",
                    "Agent 不在实例快照里",
                    f"{agent_id} 没有对应的 Agent 定义。",
                    "恢复默认 Agent 或重新选择节点执行者。",
                    phase=phase_id,
                    node_id=str(node.get("id") or "").strip(),
                    node_kind=kind,
                    agent_id=agent_id,
                ),
            )
            continue

        stage["assigned_node_count"] = safe_int(stage.get("assigned_node_count"), 0) + 1
        assigned_agent_ids.add(agent_id)
        if agent_id not in stage_agent_ids[phase_id]:
            stage_agent_ids[phase_id].add(agent_id)
            agent_tool_ids = parse_tag_list(agent.get("tools", []))
            valid_tools = [tool_index[tool_id] for tool_id in agent_tool_ids if tool_id in tool_index]
            enabled_tools = [tool for tool in valid_tools if tool.get("enabled", True)]
            route = workspace_model_route_for_agent(model, agent)
            stage["agents"].append(
                {
                    "id": agent_id,
                    "name": str(agent.get("name") or agent_id).strip(),
                    "role": str(agent.get("role") or "").strip(),
                    "enabled": bool(agent.get("enabled", True)),
                    "tool_count": len(valid_tools),
                    "enabled_tool_count": len(enabled_tools),
                    "tools": [
                        {
                            "id": str(tool.get("id") or "").strip(),
                            "label": str(tool.get("label") or tool.get("id") or "").strip(),
                            "category": str(tool.get("category") or "general").strip(),
                            "enabled": bool(tool.get("enabled", True)),
                        }
                        for tool in valid_tools[:8]
                    ],
                    "model": route,
                }
            )
            if not agent.get("enabled", True):
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "agent_disabled",
                        "blocked",
                        "Agent 已停用",
                        f"{str(agent.get('name') or agent_id).strip()} 已绑定到节点但处于停用状态。",
                        "启用 Agent 或把节点交给其他 Agent。",
                        phase=phase_id,
                        agent_id=agent_id,
                    ),
                )
            if not valid_tools:
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "agent_without_tools",
                        "warning",
                        "Agent 没有可用工具",
                        f"{str(agent.get('name') or agent_id).strip()} 的工具 allowlist 为空或全都不存在。",
                        "给 Agent 绑定对应工具，至少覆盖它负责的节点动作。",
                        phase=phase_id,
                        agent_id=agent_id,
                    ),
                )

        if required_tool_id:
            agent_tool_ids = parse_tag_list(agent.get("tools", []))
            required_tool = tool_index.get(required_tool_id)
            if required_tool_id not in agent_tool_ids:
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "required_tool_unbound",
                        "blocked",
                        "关键工具未授权",
                        f"{str(agent.get('name') or agent_id).strip()} 负责 {kind}，但 allowlist 没有 {required_tool_id}。",
                        "把关键工具加入该 Agent，或重新分配节点。",
                        phase=phase_id,
                        node_id=str(node.get("id") or "").strip(),
                        node_kind=kind,
                        agent_id=agent_id,
                        tool_id=required_tool_id,
                    ),
                )
            elif not required_tool:
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "tool_missing",
                        "blocked",
                        "工具定义缺失",
                        f"{required_tool_id} 不在当前实例工具表里。",
                        "恢复默认工具或在工具注册里补齐定义。",
                        phase=phase_id,
                        node_id=str(node.get("id") or "").strip(),
                        node_kind=kind,
                        agent_id=agent_id,
                        tool_id=required_tool_id,
                    ),
                )
            elif not required_tool.get("enabled", True):
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "tool_disabled",
                        "blocked",
                        "关键工具已停用",
                        f"{str(required_tool.get('label') or required_tool_id).strip()} 已停用。",
                        "启用工具或换一个可执行工具。",
                        phase=phase_id,
                        node_id=str(node.get("id") or "").strip(),
                        node_kind=kind,
                        agent_id=agent_id,
                        tool_id=required_tool_id,
                    ),
                )

    stages = [stage_index[phase] for phase in phase_order if phase in stage_index]
    for stage in stages:
        phase_id = str(stage.get("id") or "")
        for tool_id in sorted(stage_tool_ids.get(phase_id, set())):
            tool = tool_index.get(tool_id)
            stage["tools"].append(
                {
                    "id": tool_id,
                    "label": str((tool or {}).get("label") or tool_id).strip(),
                    "category": str((tool or {}).get("category") or "general").strip(),
                    "enabled": bool((tool or {}).get("enabled", bool(tool))),
                }
            )
        ready_profiles = [
            str(agent.get("model", {}).get("effective_profile_id") or "").strip()
            for agent in stage.get("agents", [])
            if isinstance(agent, dict)
        ]
        ready_profiles = [item for item in ready_profiles if item]
        stage["model_profiles"] = list(dict.fromkeys(ready_profiles))
        if stage.get("agents") and not ready_profiles:
            add_gap(
                stage,
                workspace_agent_topology_gap(
                    "model_profile",
                    "warning",
                    "AI Profile 未配置",
                    f"{str(stage.get('label') or phase_id)} 阶段的 Agent 还没有有效模型路由。",
                    "给项目设置默认 Provider Profile，或启用 agent_override 并给 Agent 单独配置。",
                    phase=phase_id,
                ),
            )
        stage["status"] = workspace_topology_status(stage.get("gaps") if isinstance(stage.get("gaps"), list) else [])

    enabled_tools = [tool for tool in tools if tool.get("enabled", True)]
    enabled_agents = [agent for agent in agents if agent.get("enabled", True)]
    tool_gap_count = len([
        gap for gap in topology_gaps
        if str(gap.get("type") or "") in {"required_tool_unbound", "tool_missing", "tool_disabled", "agent_without_tools"}
    ])
    effective_profile_count = len({
        str(agent.get("model", {}).get("effective_profile_id") or "").strip()
        for stage in stages
        for agent in (stage.get("agents") if isinstance(stage.get("agents"), list) else [])
        if isinstance(agent, dict) and str(agent.get("model", {}).get("effective_profile_id") or "").strip()
    })
    layers = {
        "agent": {
            "label": "Agent",
            "status": "blocked" if missing_agent_count or any(str(gap.get("type") or "") in {"unknown_agent", "agent_disabled"} for gap in topology_gaps) else "ready" if assigned_agent_ids else "warning",
            "total_count": len(agents),
            "enabled_count": len(enabled_agents),
            "assigned_count": len(assigned_agent_ids),
            "missing_count": missing_agent_count,
        },
        "tool": {
            "label": "Tool",
            "status": "blocked" if tool_gap_count else "ready" if required_tool_ids else "warning",
            "total_count": len(tools),
            "enabled_count": len(enabled_tools),
            "required_count": len(required_tool_ids),
            "gap_count": tool_gap_count,
        },
        "ai": {
            "label": "AI",
            "status": "ready" if effective_profile_count else "warning" if assigned_agent_ids else "draft",
            "routing_mode": str(model.get("routing_mode") or "workspace_default"),
            "workspace_profile_id": str(model.get("provider_profile_id") or "").strip(),
            "effective_profile_count": effective_profile_count,
            "chat_agent_id": str(model.get("chat_agent_id") or "").strip(),
        },
    }
    status = workspace_topology_status(topology_gaps)
    return {
        "status": status,
        "summary": f"{len(stages)} 个阶段 · {len(assigned_agent_ids)} 个 Agent · {len(required_tool_ids)} 个关键工具 · {len(topology_gaps)} 个缺口",
        "stage_count": len(stages),
        "agent_count": len(assigned_agent_ids),
        "required_tool_count": len(required_tool_ids),
        "gap_count": len(topology_gaps),
        "layers": layers,
        "stages": stages,
        "gaps": topology_gaps[:12],
    }
