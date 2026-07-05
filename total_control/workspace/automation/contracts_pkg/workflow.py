"""Auto-split from contracts.py — workflow."""

from __future__ import annotations

from .._deps import *  # noqa: F403
from ...schema.agents_tools import normalize_workspace_agents, normalize_workspace_tools
from ...schema.recipe import normalize_workspace_model
from ..core import workspace_status_priority
from ..evidence import workspace_group_evidence_by_kind
from ..run_plan import workspace_node_required_tool_id, workspace_run_node_phase, workspace_run_phase_label
from ..topology import workspace_model_route_for_agent
from .io import (
    workspace_apply_auto_input_mapping_fallbacks,
    workspace_contract_input_refs,
    workspace_contract_output_key_for_node,
    workspace_has_explicit_input_mapping,
    workspace_io_contract_for_kind,
    workspace_io_input_mapping,
    workspace_node_config_signal,
    workspace_required_input_names,
    workspace_unmapped_required_inputs,
)


def derive_workspace_workflow_contract(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    evidence: list[dict[str, Any]],
    resource_orchestration: dict[str, Any],
    run_plan: dict[str, Any],
    agent_topology: dict[str, Any],
) -> dict[str, Any]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    execution_nodes = {
        str(item.get("id") or ""): item
        for item in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else [])
        if isinstance(item, dict)
    }
    plan_nodes = {
        str(item.get("id") or ""): item
        for item in (run_plan.get("nodes") if isinstance(run_plan.get("nodes"), list) else [])
        if isinstance(item, dict)
    }
    resource_items = {
        str(item.get("node_kind") or ""): item
        for item in (resource_orchestration.get("items") if isinstance(resource_orchestration.get("items"), list) else [])
        if isinstance(item, dict) and str(item.get("node_kind") or "").strip()
    }
    evidence_by_kind = workspace_group_evidence_by_kind(evidence)
    tools = normalize_workspace_tools(workspace.get("tools"))
    tool_index = {str(tool.get("id") or "").strip(): tool for tool in tools if isinstance(tool, dict)}
    agents = normalize_workspace_agents(workspace.get("agents"), tool_ids=list(tool_index.keys()))
    agent_index = {str(agent.get("id") or "").strip(): agent for agent in agents if isinstance(agent, dict)}
    model = normalize_workspace_model(workspace.get("model"), existing=workspace.get("model"))
    output_catalog: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or node.get("kind") or f"node-{index}").strip()
        output_key = workspace_contract_output_key_for_node(node, index)
        if output_key and output_key not in output_catalog:
            output_catalog[output_key] = {
                "output_key": output_key,
                "node_id": node_id,
                "index": index,
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or f"节点 {index + 1}").strip(),
            }

    contract_nodes: list[dict[str, Any]] = []
    previous_outputs: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        contract = workspace_io_contract_for_kind(kind, index)
        node_id = str(node.get("id") or kind or f"node-{index}").strip()
        execution_node = execution_nodes.get(node_id, {})
        plan_node = plan_nodes.get(node_id, {})
        resource_item = resource_items.get(kind, {})
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        agent_id = str(handler.get("agent_id") or execution_node.get("agent_id") or plan_node.get("agent_id") or "").strip()
        agent = agent_index.get(agent_id, {})
        agent_tool_ids = parse_tag_list(agent.get("tools", []) if agent else [])
        required_tool_id = workspace_node_required_tool_id(kind)
        tool_ids = list(dict.fromkeys([*(agent_tool_ids[:3]), *([required_tool_id] if required_tool_id else [])]))
        route = workspace_model_route_for_agent(model, agent if agent else None)
        next_node = nodes[index + 1] if index + 1 < len(nodes) and isinstance(nodes[index + 1], dict) else {}
        input_mapping = workspace_io_input_mapping(node, contract, index)
        required_inputs = workspace_required_input_names(contract)
        input_refs = workspace_contract_input_refs(input_mapping, index, output_catalog, previous_outputs)
        has_explicit_mapping = workspace_has_explicit_input_mapping(node)
        if not has_explicit_mapping:
            workspace_apply_auto_input_mapping_fallbacks(input_mapping, input_refs)
        unmapped_required_inputs = (
            workspace_unmapped_required_inputs(input_mapping, contract)
            if has_explicit_mapping
            else []
        )
        missing_inputs = [
            ref for ref in input_refs
            if str(ref.get("status") or "") in {"blocked", "failed"}
        ]
        if unmapped_required_inputs:
            missing_inputs = [*missing_inputs, *copy.deepcopy(unmapped_required_inputs)]
        waiting_inputs = [
            ref for ref in input_refs
            if str(ref.get("status") or "") in {"draft", "warning", "pending"}
        ]
        evidence_items = evidence_by_kind.get(kind, [])
        raw_status = str(resource_item.get("status") or plan_node.get("status") or execution_node.get("status") or "draft").strip()
        if missing_inputs:
            status = "blocked"
            input_status = "blocked"
        elif waiting_inputs:
            status = raw_status if raw_status in {"blocked", "failed"} else "warning"
            input_status = "warning"
        elif input_refs:
            status = raw_status
            input_status = "ready"
        else:
            status = raw_status
            input_status = "draft"
        evidence_label = ""
        if evidence_items:
            first = evidence_items[0]
            evidence_label = f"{first.get('group', '')} · {first.get('label', '')}".strip(" ·")
            if len(evidence_items) > 1:
                evidence_label += f" +{len(evidence_items) - 1}"
        elif str(resource_item.get("value") or "").strip():
            evidence_label = str(resource_item.get("value") or "").strip()
        else:
            evidence_label = str(contract.get("evidence") or "等待证据").strip()
        contract_nodes.append(
            {
                "id": node_id,
                "index": len(contract_nodes) + 1,
                "kind": kind,
                "title": str(node.get("title") or kind or f"节点 {index + 1}").strip(),
                "phase": workspace_run_node_phase(kind),
                "phase_label": workspace_run_phase_label(workspace_run_node_phase(kind)),
                "status": status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft", "pending"} else "warning",
                "inputs": required_inputs or list(input_mapping.keys()),
                "required_inputs": required_inputs,
                "optional_inputs": [
                    str(item or "").strip()
                    for item in (contract.get("optional_inputs") if isinstance(contract.get("optional_inputs"), list) else [])
                    if str(item or "").strip()
                ],
                "mapped_inputs": list(input_mapping.keys()),
                "input_mapping": input_mapping,
                "input_refs": input_refs,
                "input_status": input_status,
                "missing_inputs": copy.deepcopy(missing_inputs),
                "unmapped_required_inputs": copy.deepcopy(unmapped_required_inputs),
                "input_gap_count": len(missing_inputs),
                "output_key": workspace_contract_output_key_for_node(node, index),
                "context": {
                    "input_key": "$input",
                    "outputs_key": "$context.outputs",
                    "previous_key": "$prev.output",
                },
                "evidence": evidence_label,
                "evidence_count": len(evidence_items),
                "config_signal": workspace_node_config_signal(node),
                "handoff": str(handler.get("handoff") or resource_item.get("action") or "").strip(),
                "next_node_id": str(next_node.get("id") or "").strip(),
                "next_node_title": str(next_node.get("title") or next_node.get("kind") or "最终报告").strip(),
                "agent": {
                    "id": agent_id,
                    "name": str(handler.get("name") or (agent.get("name") if agent else "") or execution_node.get("agent_name") or "未指派 Agent").strip(),
                    "role": str((agent.get("role") if agent else "") or "").strip(),
                    "enabled": bool(agent.get("enabled", True)) if agent else False,
                },
                "tools": [
                    {
                        "id": tool_id,
                        "label": str((tool_index.get(tool_id) or {}).get("label") or tool_id).strip(),
                        "enabled": bool((tool_index.get(tool_id) or {}).get("enabled", bool(tool_index.get(tool_id)))),
                    }
                    for tool_id in tool_ids
                    if tool_id
                ],
                "model": route,
            }
        )
        output_key = str(contract_nodes[-1].get("output_key") or "").strip()
        if output_key:
            previous_outputs[output_key] = {
                "output_key": output_key,
                "node_id": node_id,
                "index": index,
                "kind": kind,
                "title": str(node.get("title") or kind or f"节点 {index + 1}").strip(),
            }

    mapped_count = sum(1 for item in contract_nodes if item.get("input_mapping") and item.get("output_key"))
    blocked_count = sum(1 for item in contract_nodes if str(item.get("status") or "") in {"blocked", "failed"})
    ready_count = sum(1 for item in contract_nodes if str(item.get("status") or "") in {"ready", "done"})
    input_gap_count = sum(safe_int(item.get("input_gap_count"), 0) for item in contract_nodes)
    if blocked_count:
        status = "blocked"
    elif mapped_count < len(contract_nodes):
        status = "warning"
    else:
        status = "ready"
    return {
        "status": status,
        "summary": f"{mapped_count}/{len(contract_nodes)} 节点有输入/输出契约 · {ready_count} 就绪 · {blocked_count} 阻塞 · {input_gap_count} 输入断点",
        "node_count": len(contract_nodes),
        "mapped_count": mapped_count,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "input_gap_count": input_gap_count,
        "context": {
            "input_key": "$input",
            "outputs_key": "$context.outputs",
            "previous_key": "$prev.output",
        },
        "nodes": contract_nodes,
    }
