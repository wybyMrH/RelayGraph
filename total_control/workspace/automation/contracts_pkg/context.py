"""Auto-split from contracts.py — context."""

from __future__ import annotations

from .._deps import *  # noqa: F403
from ...schema.agents_tools import normalize_workspace_agents, normalize_workspace_tools
from ...schema.recipe import normalize_workspace_model
from ..core import workspace_status_priority
from ..evidence import workspace_group_evidence_by_kind
from ..run_plan import workspace_node_required_tool_id, workspace_run_node_phase, workspace_run_phase_label
from ..topology import workspace_model_route_for_agent
from .io import workspace_io_contract_for_kind, workspace_io_input_mapping


def workspace_node_workflow_contract_metadata(workspace: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
        if isinstance(item, dict)
    ]
    node_id = str(node.get("id") or "").strip()
    index = next(
        (
            idx for idx, item in enumerate(nodes)
            if str(item.get("id") or "").strip() == node_id
        ),
        0,
    )
    kind = str(node.get("kind") or "").strip()
    contract = workspace_io_contract_for_kind(kind, index)
    input_mapping = workspace_io_input_mapping(node, contract, index)
    next_node = nodes[index + 1] if index + 1 < len(nodes) and isinstance(nodes[index + 1], dict) else {}
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    tools = normalize_workspace_tools(workspace.get("tools"))
    tool_index = {str(tool.get("id") or "").strip(): tool for tool in tools if isinstance(tool, dict)}
    agents = normalize_workspace_agents(workspace.get("agents"), tool_ids=list(tool_index.keys()))
    agent_index = {str(agent.get("id") or "").strip(): agent for agent in agents if isinstance(agent, dict)}
    agent_id = str(handler.get("agent_id") or "").strip()
    agent = agent_index.get(agent_id, {})
    agent_tool_ids = parse_tag_list(agent.get("tools", []) if agent else [])
    required_tool_id = workspace_node_required_tool_id(kind)
    tool_ids = list(dict.fromkeys([*(agent_tool_ids[:3]), *([required_tool_id] if required_tool_id else [])]))
    model = normalize_workspace_model(workspace.get("model"), existing=workspace.get("model"))
    route = workspace_model_route_for_agent(model, agent if agent else None)
    handoff = str(handler.get("handoff") or "").strip()
    if not handoff:
        handoff = (
            f"交给 {str(next_node.get('title') or next_node.get('kind') or '下游节点').strip()}"
            if next_node
            else "交给报告/归档"
        )
    return {
        "node_id": node_id,
        "node_kind": kind,
        "input_mapping": input_mapping,
        "inputs": list(input_mapping.keys()),
        "output_key": str(node.get("output_key") or contract.get("output_key") or f"step_{index + 1}").strip(),
        "context": {
            "input_key": "$input",
            "outputs_key": "$context.outputs",
            "previous_key": "$prev.output",
        },
        "handoff": handoff,
        "next_node_id": str(next_node.get("id") or "").strip(),
        "next_node_title": str(next_node.get("title") or next_node.get("kind") or "最终报告").strip(),
        "agent": {
            "id": agent_id,
            "name": str(handler.get("name") or (agent.get("name") if agent else "") or "未指派 Agent").strip(),
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

def workspace_context_ref_value(data: Any, path: str) -> Any:
    current = data
    for part in [item for item in str(path or "").split(".") if item]:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None
    return current

def workspace_context_value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True

def workspace_input_data_for_context(workspace: dict[str, Any]) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    payload = copy.deepcopy(inputs)
    payload.setdefault("goal_text", str(inputs.get("goal_text") or workspace.get("brief") or source.get("idea_text") or "").strip())
    payload.setdefault("repo_url", str(source.get("repo_url") or "").strip())
    payload.setdefault("paper_url", str(source.get("paper_url") or "").strip())
    payload.setdefault("workspace_dir", str(workspace.get("workspace_dir") or "").strip())
    payload.setdefault("source_mode", str(inputs.get("source_mode") or source.get("type") or "idea").strip())
    return payload

def workspace_context_input_summary(input_data: dict[str, Any]) -> dict[str, Any]:
    repo_urls = input_data.get("repo_urls") if isinstance(input_data.get("repo_urls"), list) else []
    paper_urls = input_data.get("paper_urls") if isinstance(input_data.get("paper_urls"), list) else []
    references = input_data.get("references") if isinstance(input_data.get("references"), list) else []
    context_blocks = input_data.get("context_blocks") if isinstance(input_data.get("context_blocks"), list) else []
    keys = [
        key for key, value in input_data.items()
        if workspace_context_value_present(value)
    ]
    return {
        "source_mode": str(input_data.get("source_mode") or "idea"),
        "key_count": len(keys),
        "keys": keys[:12],
        "repo_count": len(repo_urls) + (1 if str(input_data.get("repo_url") or "").strip() else 0),
        "paper_count": len(paper_urls) + (1 if str(input_data.get("paper_url") or "").strip() else 0),
        "reference_count": len(references),
        "context_count": len(context_blocks),
        "goal_present": bool(str(input_data.get("goal_text") or "").strip()),
    }

def workspace_context_mapping_status(
    source: str,
    *,
    input_data: dict[str, Any],
    output_state: dict[str, dict[str, Any]],
    previous_output: dict[str, Any] | None,
) -> dict[str, str]:
    ref = str(source or "").strip()
    if not ref:
        return {"status": "draft", "detail": "等待来源"}
    if ref == "$input":
        return {
            "status": "ready" if workspace_context_value_present(input_data) else "draft",
            "detail": "启动输入",
        }
    if ref.startswith("$input."):
        value = workspace_context_ref_value(input_data, ref[len("$input."):])
        return {
            "status": "ready" if workspace_context_value_present(value) else "draft",
            "detail": "启动输入字段" if workspace_context_value_present(value) else "启动输入缺字段",
        }
    if ref == "$prev.output" or ref.startswith("$prev.output."):
        if previous_output and previous_output.get("produced"):
            return {"status": str(previous_output.get("status") or "ready"), "detail": str(previous_output.get("output_key") or "上一节点输出")}
        return {"status": "draft", "detail": "等待上一节点输出"}
    if ref == "$context":
        return {"status": "ready" if output_state else "draft", "detail": "工作流上下文"}
    if ref.startswith("$context.outputs."):
        key = ref[len("$context.outputs."):].split(".", 1)[0]
        state = output_state.get(key)
        if state and state.get("produced"):
            return {"status": str(state.get("status") or "ready"), "detail": f"{key} 已写入 context.outputs"}
        if state:
            status = str(state.get("status") or "draft")
            return {"status": status, "detail": f"{key} 尚未产生"}
        return {"status": "draft", "detail": f"{key} 尚无上游输出"}
    if ref.startswith("$context."):
        return {"status": "ready" if output_state else "draft", "detail": "上下文引用"}
    return {"status": "ready", "detail": "固定值或配置值"}

def derive_workspace_execution_context(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    workflow_contract: dict[str, Any],
) -> dict[str, Any]:
    input_data = workspace_input_data_for_context(workspace)
    input_summary = workspace_context_input_summary(input_data)
    contract_nodes = workflow_contract.get("nodes") if isinstance(workflow_contract.get("nodes"), list) else []
    execution_nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    execution_by_id = {
        str(node.get("id") or "").strip(): node
        for node in execution_nodes
        if isinstance(node, dict)
    }
    execution_by_kind: dict[str, dict[str, Any]] = {}
    for node in execution_nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind and kind not in execution_by_kind:
            execution_by_kind[kind] = node

    output_state: dict[str, dict[str, Any]] = {}
    previous_output: dict[str, Any] | None = None
    step_results: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    for index, contract_node in enumerate(contract_nodes):
        if not isinstance(contract_node, dict):
            continue
        node_id = str(contract_node.get("id") or contract_node.get("node_id") or "").strip()
        kind = str(contract_node.get("kind") or contract_node.get("node_kind") or "").strip()
        execution_node = execution_by_id.get(node_id) or execution_by_kind.get(kind) or {}
        status = str(execution_node.get("status") or contract_node.get("status") or "draft").strip() or "draft"
        job_status = str(execution_node.get("job_status") or "").strip()
        job_id = str(execution_node.get("job_id") or "").strip()
        output_key = str(contract_node.get("output_key") or f"step_{index + 1}").strip()
        input_mapping = contract_node.get("input_mapping") if isinstance(contract_node.get("input_mapping"), dict) else {}
        static_input_refs = {
            str(item.get("name") or "").strip(): item
            for item in (contract_node.get("input_refs") if isinstance(contract_node.get("input_refs"), list) else [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }
        resolved_inputs: list[dict[str, str]] = []
        for key, value in input_mapping.items():
            name = str(key or "").strip()
            if not name:
                continue
            source = str(value or "").strip()
            static_state = static_input_refs.get(name, {})
            if static_state and str(static_state.get("status") or "") in {"blocked", "failed"}:
                source_state = {
                    "status": str(static_state.get("status") or "blocked"),
                    "detail": str(static_state.get("detail") or "输入映射断开"),
                }
            else:
                source_state = workspace_context_mapping_status(
                    source,
                    input_data=input_data,
                    output_state=output_state,
                    previous_output=previous_output,
                )
            resolved_inputs.append(
                {
                    "name": name,
                    "source": source,
                    "status": source_state["status"],
                    "detail": source_state["detail"],
                    "source_type": str(static_state.get("source_type") or "").strip(),
                    "upstream_output_key": str(static_state.get("upstream_output_key") or "").strip(),
                    "upstream_node_id": str(static_state.get("upstream_node_id") or "").strip(),
                }
            )
        input_blocked_count = len([item for item in resolved_inputs if item["status"] in {"blocked", "failed"}])
        input_waiting_count = len([item for item in resolved_inputs if item["status"] in {"draft", "warning", "pending"}])
        if input_blocked_count:
            input_status = "blocked"
        elif input_waiting_count:
            input_status = "warning"
        elif resolved_inputs:
            input_status = "ready"
        else:
            input_status = "draft"

        produced = status == "done" or job_status == "done"
        if status in {"failed", "stopped"} or job_status in {"failed", "stopped"}:
            output_status = "failed"
        elif status in {"running", "queued"} or job_status in {"running", "queued", "starting", "blocked"}:
            output_status = "running"
        elif produced:
            output_status = "ready"
        elif input_status == "blocked":
            output_status = "blocked"
        else:
            output_status = "draft"
        artifact_count = len(execution_node.get("artifacts") if isinstance(execution_node.get("artifacts"), list) else [])
        resources = execution_node.get("resources") if isinstance(execution_node.get("resources"), dict) else {}
        trace = execution_node.get("trace") if isinstance(execution_node.get("trace"), list) else []
        agent = contract_node.get("agent") if isinstance(contract_node.get("agent"), dict) else {}
        model = contract_node.get("model") if isinstance(contract_node.get("model"), dict) else {}
        tools = contract_node.get("tools") if isinstance(contract_node.get("tools"), list) else []
        output_item = {
            "key": output_key,
            "node_id": node_id,
            "node_kind": kind,
            "title": str(contract_node.get("title") or execution_node.get("title") or kind).strip(),
            "status": output_status,
            "produced": produced,
            "job_id": job_id,
            "artifact_count": artifact_count,
            "resource_key_count": len(resources),
            "handoff": str(contract_node.get("handoff") or "").strip(),
            "next_node_id": str(contract_node.get("next_node_id") or "").strip(),
            "next_node_title": str(contract_node.get("next_node_title") or "最终报告").strip(),
        }
        outputs.append(output_item)
        output_state[output_key] = output_item
        previous_output = output_item
        step_results.append(
            {
                "step_order": safe_int(contract_node.get("index"), index + 1),
                "node_id": node_id,
                "node_kind": kind,
                "title": str(contract_node.get("title") or execution_node.get("title") or kind).strip(),
                "status": status,
                "input_status": input_status,
                "input_waiting_count": input_waiting_count,
                "input_blocked_count": input_blocked_count,
                "input_mapping": input_mapping,
                "resolved_inputs": resolved_inputs,
                "output_key": output_key,
                "output_status": output_status,
                "output_produced": produced,
                "job_id": job_id,
                "job_status": job_status,
                "run_count": safe_int(execution_node.get("run_count"), 0),
                "trace_count": len(trace),
                "artifact_count": artifact_count,
                "resource_key_count": len(resources),
                "agent": {
                    "id": str(agent.get("id") or execution_node.get("agent_id") or "").strip(),
                    "name": str(agent.get("name") or execution_node.get("agent_name") or "未指派 Agent").strip(),
                    "role": str(agent.get("role") or "").strip(),
                },
                "tools": tools[:6],
                "model": model,
                "error": str(execution_node.get("error") or "").strip(),
            }
        )

    done_count = len([item for item in step_results if str(item.get("status") or "") == "done"])
    running_count = len([item for item in step_results if str(item.get("status") or "") in {"running", "queued"}])
    failed_count = len([item for item in step_results if str(item.get("status") or "") in {"failed", "stopped"}])
    blocked_count = len([item for item in step_results if str(item.get("input_status") or "") == "blocked"])
    produced_count = len([item for item in outputs if item.get("produced")])
    if failed_count:
        status = "failed"
    elif running_count:
        status = "running"
    elif blocked_count:
        status = "blocked"
    elif produced_count == len(outputs) and outputs:
        status = "ready"
    elif step_results:
        status = "warning"
    else:
        status = "draft"
    return {
        "status": status,
        "summary": f"{len(step_results)} 步 · {produced_count}/{len(outputs)} 个输出已产生 · {running_count} 运行 · {failed_count} 失败",
        "context": {
            "input_key": "$input",
            "outputs_key": "$context.outputs",
            "previous_key": "$prev.output",
        },
        "input_data": input_summary,
        "outputs": outputs,
        "step_results": step_results,
        "totals": {
            "step_count": len(step_results),
            "output_count": len(outputs),
            "produced_output_count": produced_count,
            "done_count": done_count,
            "running_count": running_count,
            "failed_count": failed_count,
            "blocked_input_count": blocked_count,
            "total_tokens_used": 0,
        },
    }
