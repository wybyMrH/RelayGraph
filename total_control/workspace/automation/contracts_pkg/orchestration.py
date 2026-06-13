"""Auto-split from contracts.py — orchestration."""

from __future__ import annotations

from .._deps import *  # noqa: F403
from ...schema.agents_tools import normalize_workspace_agents, normalize_workspace_tools
from ...schema.recipe import normalize_workspace_model
from ..core import workspace_status_priority
from ..evidence import workspace_group_evidence_by_kind
from ..run_plan import workspace_node_required_tool_id, workspace_run_node_phase, workspace_run_phase_label
from ..topology import workspace_model_route_for_agent
def workspace_orchestration_gap_matches_node(gap: dict[str, Any], node: dict[str, Any]) -> bool:
    gap_node_id = str(gap.get("node_id") or "").strip()
    gap_node_kind = str(gap.get("node_kind") or "").strip()
    gap_agent_id = str(gap.get("agent_id") or "").strip()
    gap_tool_id = str(gap.get("tool_id") or "").strip()
    node_agent = node.get("agent") if isinstance(node.get("agent"), dict) else {}
    node_tools = node.get("tools") if isinstance(node.get("tools"), list) else []
    if gap_node_id and gap_node_id == str(node.get("id") or "").strip():
        return True
    if gap_node_kind and gap_node_kind == str(node.get("kind") or "").strip():
        return True
    if gap_agent_id and gap_agent_id == str(node_agent.get("id") or "").strip():
        return True
    if gap_tool_id and any(gap_tool_id == str(tool.get("id") or "").strip() for tool in node_tools if isinstance(tool, dict)):
        return True
    return False

def workspace_orchestration_status(statuses: list[str], *, default: str = "draft") -> str:
    values = [str(status or "").strip() for status in statuses if str(status or "").strip()]
    if not values:
        return default
    return min(values, key=workspace_status_priority)

def derive_workspace_orchestration_contract(
    agent_topology: dict[str, Any],
    workflow_contract: dict[str, Any],
) -> dict[str, Any]:
    layers = agent_topology.get("layers") if isinstance(agent_topology.get("layers"), dict) else {}
    topology_stages = agent_topology.get("stages") if isinstance(agent_topology.get("stages"), list) else []
    contract_nodes = workflow_contract.get("nodes") if isinstance(workflow_contract.get("nodes"), list) else []
    gaps = agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else []
    stage_index = {
        str(stage.get("id") or "").strip(): stage
        for stage in topology_stages
        if isinstance(stage, dict) and str(stage.get("id") or "").strip()
    }
    lanes: dict[str, dict[str, Any]] = {}
    phase_order = ["source", "discover", "setup", "run", "collect", "report", "other"]

    def lane_for_phase(phase: str) -> dict[str, Any]:
        phase_id = phase if phase in phase_order else "other"
        if phase_id not in lanes:
            stage = stage_index.get(phase_id, {})
            lanes[phase_id] = {
                "id": phase_id,
                "label": str(stage.get("label") or workspace_run_phase_label(phase_id)).strip(),
                "status": str(stage.get("status") or "draft").strip(),
                "node_count": 0,
                "ready_count": 0,
                "blocked_count": 0,
                "agent_count": len(stage.get("agents") if isinstance(stage.get("agents"), list) else []),
                "tool_count": len(stage.get("tools") if isinstance(stage.get("tools"), list) else []),
                "model_profile_count": len(stage.get("model_profiles") if isinstance(stage.get("model_profiles"), list) else []),
                "nodes": [],
                "gaps": [
                    copy.deepcopy(gap)
                    for gap in (stage.get("gaps") if isinstance(stage.get("gaps"), list) else [])
                    if isinstance(gap, dict)
                ][:5],
            }
        return lanes[phase_id]

    for node in contract_nodes:
        if not isinstance(node, dict):
            continue
        phase = str(node.get("phase") or "other").strip() or "other"
        lane = lane_for_phase(phase)
        node_gaps = [
            copy.deepcopy(gap)
            for gap in gaps
            if isinstance(gap, dict) and workspace_orchestration_gap_matches_node(gap, node)
        ][:3]
        input_gaps = []
        for ref in (node.get("missing_inputs") if isinstance(node.get("missing_inputs"), list) else []):
            if not isinstance(ref, dict):
                continue
            input_gaps.append(
                {
                    "type": "input_mapping",
                    "status": str(ref.get("status") or "blocked").strip(),
                    "title": f"输入断点：{str(ref.get('name') or 'input').strip()}",
                    "detail": str(ref.get("detail") or "").strip(),
                    "action": "检查 input_mapping 或上游 output_key。",
                    "node_id": str(node.get("id") or "").strip(),
                    "node_kind": str(node.get("kind") or "").strip(),
                    "phase": phase,
                    "field": str(ref.get("name") or "").strip(),
                    "source": str(ref.get("source") or "").strip(),
                    "upstream_output_key": str(ref.get("upstream_output_key") or "").strip(),
                }
            )
        node_gaps = [*input_gaps, *node_gaps][:3]
        agent = node.get("agent") if isinstance(node.get("agent"), dict) else {}
        model = node.get("model") if isinstance(node.get("model"), dict) else {}
        tools = node.get("tools") if isinstance(node.get("tools"), list) else []
        node_status = workspace_orchestration_status(
            [
                str(node.get("status") or "draft"),
                *[str(gap.get("status") or "warning") for gap in node_gaps if isinstance(gap, dict)],
                "warning" if not str(agent.get("id") or "").strip() else "ready",
                "warning" if not str(model.get("effective_profile_id") or "").strip() else "ready",
            ],
            default="draft",
        )
        if node_status in {"ready", "done"}:
            lane["ready_count"] = safe_int(lane.get("ready_count"), 0) + 1
        if node_status in {"blocked", "failed"}:
            lane["blocked_count"] = safe_int(lane.get("blocked_count"), 0) + 1
        lane["node_count"] = safe_int(lane.get("node_count"), 0) + 1
        lane["nodes"].append(
            {
                "id": str(node.get("id") or "").strip(),
                "index": safe_int(node.get("index"), len(lane["nodes"]) + 1),
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or "节点").strip(),
                "status": node_status,
                "input_count": len(node.get("inputs") if isinstance(node.get("inputs"), list) else []),
                "input_status": str(node.get("input_status") or "draft").strip(),
                "input_gap_count": safe_int(node.get("input_gap_count"), 0),
                "missing_inputs": copy.deepcopy(node.get("missing_inputs") if isinstance(node.get("missing_inputs"), list) else []),
                "output_key": str(node.get("output_key") or "").strip(),
                "handoff": str(node.get("handoff") or "").strip(),
                "next_node_title": str(node.get("next_node_title") or "最终报告").strip(),
                "agent": {
                    "id": str(agent.get("id") or "").strip(),
                    "name": str(agent.get("name") or "未指派 Agent").strip(),
                    "role": str(agent.get("role") or "").strip(),
                    "enabled": bool(agent.get("enabled", False)),
                },
                "tools": [
                    {
                        "id": str(tool.get("id") or "").strip(),
                        "label": str(tool.get("label") or tool.get("id") or "").strip(),
                        "enabled": bool(tool.get("enabled", False)),
                    }
                    for tool in tools
                    if isinstance(tool, dict)
                ][:5],
                "model": {
                    "label": str(model.get("label") or model.get("source") or "未配置 Profile").strip(),
                    "source": str(model.get("source") or "").strip(),
                    "effective_profile_id": str(model.get("effective_profile_id") or "").strip(),
                    "status": str(model.get("status") or "warning").strip(),
                },
                "gaps": node_gaps,
                "next_action": str((node_gaps[0] if node_gaps else {}).get("action") or node.get("handoff") or "").strip(),
            }
        )

    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        phase = str(gap.get("phase") or "").strip()
        if not phase:
            continue
        lane = lane_for_phase(phase)
        if not any(str(existing.get("title") or existing.get("type") or "") == str(gap.get("title") or gap.get("type") or "") for existing in lane.get("gaps", [])):
            lane["gaps"].append(copy.deepcopy(gap))

    lane_items = [lanes[phase] for phase in phase_order if phase in lanes]
    for lane in lane_items:
        lane_statuses = [
            str(lane.get("status") or "draft"),
            *[str(node.get("status") or "draft") for node in (lane.get("nodes") if isinstance(lane.get("nodes"), list) else [])],
            *[str(gap.get("status") or "warning") for gap in (lane.get("gaps") if isinstance(lane.get("gaps"), list) else []) if isinstance(gap, dict)],
        ]
        lane["status"] = workspace_orchestration_status(lane_statuses, default="draft")
        lane["summary"] = (
            f"{safe_int(lane.get('node_count'), 0)} 节点 · "
            f"{safe_int(lane.get('agent_count'), 0)} Agent · "
            f"{safe_int(lane.get('tool_count'), 0)} 工具 · "
            f"{safe_int(lane.get('model_profile_count'), 0)} Profile"
        )
        lane["gaps"] = (lane.get("gaps") if isinstance(lane.get("gaps"), list) else [])[:5]

    all_node_statuses = [
        str(node.get("status") or "draft")
        for lane in lane_items
        for node in (lane.get("nodes") if isinstance(lane.get("nodes"), list) else [])
        if isinstance(node, dict)
    ]
    status = workspace_orchestration_status(
        [str(agent_topology.get("status") or "draft"), str(workflow_contract.get("status") or "draft"), *all_node_statuses],
        default="draft",
    )
    ready_nodes = sum(1 for status_value in all_node_statuses if status_value in {"ready", "done"})
    blocked_nodes = sum(1 for status_value in all_node_statuses if status_value in {"blocked", "failed"})
    next_gap = next(
        (
            gap for gap in gaps
            if isinstance(gap, dict) and str(gap.get("status") or "") in {"failed", "blocked", "warning", "draft"}
        ),
        {},
    )
    return {
        "status": status,
        "summary": f"{len(lane_items)} 个阶段车道 · {ready_nodes}/{len(all_node_statuses)} 节点闭环 · {blocked_nodes} 阻塞 · {len(gaps)} 缺口",
        "lane_count": len(lane_items),
        "node_count": len(all_node_statuses),
        "ready_node_count": ready_nodes,
        "blocked_node_count": blocked_nodes,
        "layers": copy.deepcopy(layers),
        "lanes": lane_items,
        "gaps": copy.deepcopy(gaps[:12]),
        "next_action": {
            "status": str(next_gap.get("status") or status).strip(),
            "title": str(next_gap.get("title") or "编排契约已形成").strip(),
            "detail": str(next_gap.get("detail") or workflow_contract.get("summary") or "").strip(),
            "action": str(next_gap.get("action") or "按当前执行包继续推进。").strip(),
            "phase": str(next_gap.get("phase") or "").strip(),
            "node_id": str(next_gap.get("node_id") or "").strip(),
            "node_kind": str(next_gap.get("node_kind") or "").strip(),
        },
    }
