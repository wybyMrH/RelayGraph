from __future__ import annotations

import copy
from typing import Any

from ...constants_pkg.workspace_nodes import WORKSPACE_NODE_LIBRARY
from ...utils import parse_tag_list, safe_id, safe_int
from ...workspace.automation import (
    derive_workspace_workflow_contract,
    workspace_io_contract_for_kind,
    workspace_node_required_tool_id,
)
from ...workspace.schema import (
    build_template_snapshot,
    collect_template_agent_ids,
    workflow_template_topology_preview,
)


def build_workflow_template_validation_payload(
    template: dict[str, Any],
    raw_payload: dict[str, Any],
    *,
    agent_definitions: list[Any],
    tool_definitions: list[Any],
    provider_profiles: list[Any],
) -> dict[str, Any]:
    nodes = template.get("nodes") if isinstance(template.get("nodes"), list) else []
    links = raw_payload.get("links") if isinstance(raw_payload.get("links"), list) else template.get("links")
    links = links if isinstance(links, list) else []
    model = template.get("model") if isinstance(template.get("model"), dict) else {}
    agent_index = {
        str(agent.get("id") or "").strip(): agent
        for agent in agent_definitions
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    tool_index = {
        str(tool.get("id") or "").strip(): tool
        for tool in tool_definitions
        if isinstance(tool, dict) and str(tool.get("id") or "").strip()
    }
    provider_ids = {
        str(profile.get("id") or "").strip()
        for profile in provider_profiles
        if isinstance(profile, dict) and str(profile.get("id") or "").strip()
    }
    raw_nodes = raw_payload.get("nodes") if isinstance(raw_payload.get("nodes"), list) else []
    raw_nodes_by_id = {
        str(item.get("id") or "").strip(): item
        for item in raw_nodes
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    issues: list[dict[str, Any]] = []
    output_key_mismatch_nodes: set[str] = set()

    def add_issue(
        severity: str,
        kind: str,
        code: str,
        message: str,
        **extra: Any,
    ) -> None:
        issue = {
            "severity": severity,
            "kind": kind,
            "code": code,
            "message": message,
        }
        issue.update({key: value for key, value in extra.items() if value not in (None, "")})
        issues.append(issue)

    if not nodes:
        add_issue("blocking", "template", "no_nodes", "模板没有节点，无法创建可执行实例。")

    node_ids: set[str] = set()
    output_keys: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            add_issue("blocking", "node", "invalid_node", "模板节点不是对象。", index=index)
            continue
        node_id = str(node.get("id") or "").strip()
        kind = str(node.get("kind") or "").strip()
        title = str(node.get("title") or kind or f"节点 {index + 1}").strip()
        if not node_id:
            add_issue("blocking", "node", "missing_node_id", f"{title} 缺少节点 ID。", index=index)
        elif node_id in node_ids:
            add_issue("blocking", "node", "duplicate_node_id", f"节点 ID {node_id} 重复。", node_id=node_id)
        else:
            node_ids.add(node_id)
        if kind and kind not in WORKSPACE_NODE_LIBRARY:
            add_issue("warning", "node", "custom_node_kind", f"{title} 使用自定义节点类型 {kind}。", node_id=node_id)

        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        mode = str(handler.get("mode") or "human").strip().lower() or "human"
        agent_id = str(handler.get("agent_id") or "").strip()
        if mode != "human":
            if not agent_id:
                add_issue("blocking", "agent", "missing_agent", f"{title} 是 {mode} 节点，但没有绑定 Agent。", node_id=node_id)
            else:
                agent = agent_index.get(agent_id)
                if not agent:
                    add_issue("blocking", "agent", "unknown_agent", f"{title} 绑定的 Agent {agent_id} 不存在。", node_id=node_id, agent_id=agent_id)
                elif agent.get("enabled") is False:
                    severity = "blocking" if mode == "agent" else "warning"
                    add_issue(severity, "agent", "disabled_agent", f"{title} 绑定的 Agent {agent.get('name') or agent_id} 已停用。", node_id=node_id, agent_id=agent_id)
                elif mode == "agent":
                    for tool_id in parse_tag_list(agent.get("tools", [])):
                        tool = tool_index.get(tool_id)
                        if not tool:
                            add_issue("warning", "tool", "unknown_agent_tool", f"Agent {agent.get('name') or agent_id} 的工具 {tool_id} 不在工具注册表。", node_id=node_id, agent_id=agent_id, tool_id=tool_id)
                        elif tool.get("enabled") is False:
                            add_issue("warning", "tool", "disabled_agent_tool", f"Agent {agent.get('name') or agent_id} 的工具 {tool.get('label') or tool_id} 已停用。", node_id=node_id, agent_id=agent_id, tool_id=tool_id)

        required_tool_id = workspace_node_required_tool_id(kind)
        if required_tool_id:
            tool = tool_index.get(required_tool_id)
            if not tool:
                add_issue("blocking", "tool", "missing_required_tool", f"{title} 需要工具 {required_tool_id}，但工具注册表里不存在。", node_id=node_id, tool_id=required_tool_id)
            elif tool.get("enabled") is False:
                add_issue("blocking", "tool", "disabled_required_tool", f"{title} 需要的工具 {tool.get('label') or required_tool_id} 已停用。", node_id=node_id, tool_id=required_tool_id)

        raw_node = raw_nodes_by_id.get(node_id) if node_id else None
        if not raw_node and index < len(raw_nodes) and isinstance(raw_nodes[index], dict):
            raw_node = raw_nodes[index]
        raw_handler = raw_node.get("handler") if isinstance(raw_node, dict) and isinstance(raw_node.get("handler"), dict) else {}
        raw_node_output_key = str(raw_node.get("output_key") or "").strip() if isinstance(raw_node, dict) else ""
        raw_handler_output_key = str(raw_handler.get("output_key") or "").strip()
        if raw_node_output_key and raw_handler_output_key and raw_node_output_key != raw_handler_output_key:
            output_key_mismatch_nodes.add(node_id)
            add_issue(
                "blocking",
                "contract",
                "output_key_mismatch",
                f"{title} 的 node.output_key={raw_node_output_key} 与 handler.output_key={raw_handler_output_key} 不一致。",
                node_id=node_id,
                output_key=raw_node_output_key,
                handler_output_key=raw_handler_output_key,
            )

        node_output_key = str(node.get("output_key") or "").strip()
        handler_output_key = str(handler.get("output_key") or "").strip()
        if node_id not in output_key_mismatch_nodes and node_output_key and handler_output_key and node_output_key != handler_output_key:
            add_issue(
                "blocking",
                "contract",
                "output_key_mismatch",
                f"{title} 的 node.output_key={node_output_key} 与 handler.output_key={handler_output_key} 不一致。",
                node_id=node_id,
                output_key=node_output_key,
                handler_output_key=handler_output_key,
            )
        output_key = str(
            node_output_key
            or handler_output_key
            or workspace_io_contract_for_kind(kind, index).get("output_key")
            or ""
        ).strip()
        if output_key:
            previous = output_keys.get(output_key)
            if previous:
                add_issue(
                    "blocking",
                    "contract",
                    "duplicate_output_key",
                    f"{title} 的 output_key {output_key} 与上游节点重复。",
                    node_id=node_id,
                    upstream_node_id=previous.get("node_id"),
                    output_key=output_key,
                )
            else:
                output_keys[output_key] = {"node_id": node_id, "index": index}

    seen_edges: set[tuple[str, str]] = set()
    for link in links:
        if not isinstance(link, dict):
            add_issue("blocking", "link", "invalid_link", "模板链路不是对象。")
            continue
        from_id = str(link.get("from") or "").strip()
        to_id = str(link.get("to") or "").strip()
        if not from_id or not to_id:
            add_issue("blocking", "link", "incomplete_link", "模板链路缺少 from/to。")
            continue
        if from_id not in node_ids or to_id not in node_ids:
            add_issue("blocking", "link", "dangling_link", f"链路 {from_id} -> {to_id} 指向不存在的节点。", from_node_id=from_id, to_node_id=to_id)
            continue
        edge = (from_id, to_id)
        if edge in seen_edges:
            add_issue("warning", "link", "duplicate_link", f"链路 {from_id} -> {to_id} 重复。", from_node_id=from_id, to_node_id=to_id)
        seen_edges.add(edge)

    chat_agent_id = str(model.get("chat_agent_id") or "").strip()
    if chat_agent_id and chat_agent_id not in agent_index:
        add_issue("warning", "model", "unknown_chat_agent", f"默认对话 Agent {chat_agent_id} 不存在。", agent_id=chat_agent_id)
    provider_profile_id = str(model.get("provider_profile_id") or "").strip()
    if provider_profile_id and provider_profile_id not in provider_ids:
        add_issue("warning", "model", "unknown_provider_profile", f"默认 Provider Profile {provider_profile_id} 不存在。", provider_profile_id=provider_profile_id)
    routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
    used_agent_ids = collect_template_agent_ids(nodes, model)
    for agent_id in used_agent_ids:
        agent = agent_index.get(agent_id)
        if not agent:
            continue
        agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
        if agent_profile_id and agent_profile_id not in provider_ids:
            add_issue(
                "warning",
                "model",
                "unknown_agent_provider_profile",
                f"Agent {agent.get('name') or agent_id} 指向的 Provider Profile {agent_profile_id} 不存在。",
                agent_id=agent_id,
                provider_profile_id=agent_profile_id,
            )
        if routing_mode == "agent_override" and not agent_profile_id:
            add_issue(
                "warning",
                "model",
                "agent_override_without_profile",
                f"Agent {agent.get('name') or agent_id} 未设置 Provider 覆盖，会回落到模板默认路由。",
                agent_id=agent_id,
            )

    snapshot = build_template_snapshot(template, agent_definitions, tool_definitions)
    contract = derive_workspace_workflow_contract(
        {
            "nodes": copy.deepcopy(nodes),
            "links": copy.deepcopy(template.get("links") if isinstance(template.get("links"), list) else []),
            "agents": copy.deepcopy(snapshot.get("agents") if isinstance(snapshot.get("agents"), list) else []),
            "tools": copy.deepcopy(snapshot.get("tools") if isinstance(snapshot.get("tools"), list) else []),
            "model": copy.deepcopy(model),
        },
        {},
        [],
        {},
        {},
        {},
    )
    for contract_node in contract.get("nodes") if isinstance(contract.get("nodes"), list) else []:
        if not isinstance(contract_node, dict):
            continue
        for ref in contract_node.get("missing_inputs") if isinstance(contract_node.get("missing_inputs"), list) else []:
            if not isinstance(ref, dict):
                continue
            code = str(ref.get("code") or "blocked_input_mapping").strip()
            add_issue(
                "blocking",
                "contract",
                code,
                f"{contract_node.get('title') or contract_node.get('id')} 的输入 {ref.get('name') or ''} 未能解析：{ref.get('detail') or ''}",
                node_id=str(contract_node.get("id") or "").strip(),
                source=str(ref.get("source") or "").strip(),
                input_name=str(ref.get("name") or "").strip(),
                upstream_node_id=str(ref.get("upstream_node_id") or "").strip(),
                upstream_output_key=str(ref.get("upstream_output_key") or "").strip(),
            )

    blocking_count = sum(1 for issue in issues if issue.get("severity") == "blocking")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    status = "blocked" if blocking_count else "warning" if warning_count else "ready"
    return {
        "status": status,
        "summary": f"{len(nodes)} 个节点 · {blocking_count} 个阻塞 · {warning_count} 个警告 · {safe_int(contract.get('mapped_count'), 0)}/{safe_int(contract.get('node_count'), 0)} 节点有输入/输出契约 · {safe_int(contract.get('input_gap_count'), 0)} 输入断点",
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "issue_count": len(issues),
        "node_count": len(nodes),
        "agent_count": len(snapshot.get("agents") if isinstance(snapshot.get("agents"), list) else []),
        "tool_count": len(snapshot.get("tools") if isinstance(snapshot.get("tools"), list) else []),
        "contract": contract,
        "issues": issues,
    }


def build_workflow_template_preview_payload(
    template: dict[str, Any],
    validation: dict[str, Any],
    raw_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract_nodes = validation.get("contract", {}).get("nodes") if isinstance(validation.get("contract"), dict) else []
    contract_by_id = {
        str(item.get("id") or "").strip(): item
        for item in contract_nodes
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    issues = validation.get("issues") if isinstance(validation.get("issues"), list) else []
    output_conflicts_by_node: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        if not isinstance(issue, dict) or str(issue.get("code") or "").strip() not in {"duplicate_output_key", "output_key_mismatch"}:
            continue
        node_id = str(issue.get("node_id") or "").strip()
        if not node_id:
            continue
        code = str(issue.get("code") or "").strip()
        output_conflicts_by_node.setdefault(node_id, []).append(
            {
                "code": code,
                "output_key": str(issue.get("output_key") or "").strip(),
                "handler_output_key": str(issue.get("handler_output_key") or "").strip(),
                "upstream_node_id": str(issue.get("upstream_node_id") or "").strip(),
                "message": str(issue.get("message") or "").strip(),
            }
        )
    reserved_output_keys = {
        str(item.get("output_key") or "").strip()
        for item in contract_nodes
        if isinstance(item, dict) and str(item.get("output_key") or "").strip()
    }

    def unique_output_key(seed: str, index: int) -> str:
        base = safe_id(seed) or f"step_{index + 1}"
        candidate = f"{base}_{index + 1}"
        suffix = 2
        while candidate in reserved_output_keys:
            candidate = f"{base}_{index + 1}_{suffix}"
            suffix += 1
        reserved_output_keys.add(candidate)
        return candidate

    seen_outputs: dict[str, dict[str, Any]] = {}
    preview_nodes: list[dict[str, Any]] = []
    for index, node in enumerate(template.get("nodes") if isinstance(template.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        contract = contract_by_id.get(node_id, {})
        repair_actions: list[dict[str, Any]] = []
        missing_inputs = contract.get("missing_inputs") if isinstance(contract.get("missing_inputs"), list) else []
        for ref in missing_inputs:
            if not isinstance(ref, dict):
                continue
            input_name = str(ref.get("name") or "").strip()
            if not input_name:
                continue
            source = str(ref.get("source") or "").strip()
            code = str(ref.get("code") or "").strip()
            upstream_output_key = str(ref.get("upstream_output_key") or "").strip()
            if upstream_output_key and upstream_output_key in seen_outputs:
                value = f"$context.outputs.{upstream_output_key}"
            elif code == "first_node_prev_reference" or index == 0:
                value = "$input"
            elif input_name in seen_outputs:
                value = f"$context.outputs.{input_name}"
            elif source:
                value = source
            else:
                value = "$prev.output"
            repair_actions.append(
                {
                    "id": safe_id(f"map-input-{node_id}-{input_name}") or f"map-input-{index}-{len(repair_actions)}",
                    "kind": "set_input_mapping",
                    "issue_code": code or "unmapped_required_input",
                    "severity": "blocking",
                    "node_id": node_id,
                    "label": f"映射 {input_name}",
                    "patch": {
                        "path": ["nodes", index, "input_mapping", input_name],
                        "value": value,
                    },
                    "patches": [
                        {
                            "path": ["nodes", index, "input_mapping", input_name],
                            "value": value,
                        }
                    ],
                }
            )
        output_key = str(contract.get("output_key") or node.get("output_key") or handler.get("output_key") or "").strip()
        output_conflicts = output_conflicts_by_node.get(node_id, [])
        for conflict in output_conflicts:
            if not isinstance(conflict, dict):
                continue
            code = str(conflict.get("code") or "").strip()
            if code == "duplicate_output_key":
                value = unique_output_key(str(conflict.get("output_key") or output_key or "step"), index)
                patches = [
                    {"path": ["nodes", index, "output_key"], "value": value},
                    {"path": ["nodes", index, "handler", "output_key"], "value": value},
                ]
                repair_actions.append(
                    {
                        "id": safe_id(f"set-output-key-{node_id}-{value}") or f"set-output-key-{index}",
                        "kind": "set_output_key",
                        "issue_code": "duplicate_output_key",
                        "severity": "blocking",
                        "node_id": node_id,
                        "label": f"改为唯一 output_key {value}",
                        "patch": patches[0],
                        "patches": patches,
                    }
                )
            elif code == "output_key_mismatch" and output_key:
                patches = [
                    {"path": ["nodes", index, "handler", "output_key"], "value": output_key},
                ]
                repair_actions.append(
                    {
                        "id": safe_id(f"sync-handler-output-key-{node_id}") or f"sync-handler-output-key-{index}",
                        "kind": "sync_output_key",
                        "issue_code": "output_key_mismatch",
                        "severity": "blocking",
                        "node_id": node_id,
                        "label": f"同步 handler output_key 为 {output_key}",
                        "patch": patches[0],
                        "patches": patches,
                    }
                )
        preview_nodes.append(
            {
                "id": node_id,
                "index": index + 1,
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or f"节点 {index + 1}").strip(),
                "handler": {
                    "mode": str(handler.get("mode") or "human").strip() or "human",
                    "agent_id": str(handler.get("agent_id") or "").strip(),
                    "name": str(handler.get("name") or "").strip(),
                },
                "output_key": output_key,
                "inputs": copy.deepcopy(contract.get("inputs") if isinstance(contract.get("inputs"), list) else []),
                "required_inputs": copy.deepcopy(contract.get("required_inputs") if isinstance(contract.get("required_inputs"), list) else []),
                "mapped_inputs": copy.deepcopy(contract.get("mapped_inputs") if isinstance(contract.get("mapped_inputs"), list) else []),
                "input_mapping": copy.deepcopy(contract.get("input_mapping") if isinstance(contract.get("input_mapping"), dict) else {}),
                "input_refs": copy.deepcopy(contract.get("input_refs") if isinstance(contract.get("input_refs"), list) else []),
                "input_status": str(contract.get("input_status") or "").strip(),
                "missing_inputs": copy.deepcopy(missing_inputs),
                "unmapped_required_inputs": copy.deepcopy(contract.get("unmapped_required_inputs") if isinstance(contract.get("unmapped_required_inputs"), list) else []),
                "input_gap_count": safe_int(contract.get("input_gap_count"), 0),
                "output_conflicts": output_conflicts,
                "repair_actions": repair_actions,
                "tools": copy.deepcopy(contract.get("tools") if isinstance(contract.get("tools"), list) else []),
                "model": copy.deepcopy(contract.get("model") if isinstance(contract.get("model"), dict) else {}),
            }
        )
        if output_key and output_key not in seen_outputs:
            seen_outputs[output_key] = {"node_id": node_id, "index": index}
    source = template.get("source") if isinstance(template.get("source"), dict) else {}
    model = template.get("model") if isinstance(template.get("model"), dict) else {}
    raw = raw_payload if isinstance(raw_payload, dict) else {}
    topology_links = raw.get("links") if isinstance(raw.get("links"), list) else template.get("links")
    topology_preview = workflow_template_topology_preview(
        template.get("nodes") if isinstance(template.get("nodes"), list) else [],
        topology_links if isinstance(topology_links, list) else [],
        contract_nodes=contract_nodes,
        issues=issues,
    )
    return {
        "source_type": str(source.get("type") or "").strip(),
        "template_id": str(template.get("id") or "").strip(),
        "template_name": str(template.get("name") or "").strip(),
        "status": validation.get("status"),
        "node_count": len(preview_nodes),
        "agent_ids": copy.deepcopy(template.get("agent_ids") if isinstance(template.get("agent_ids"), list) else []),
        "tool_ids": copy.deepcopy(template.get("tool_ids") if isinstance(template.get("tool_ids"), list) else []),
        "provider_profile_id": str(model.get("provider_profile_id") or "").strip(),
        "chat_agent_id": str(model.get("chat_agent_id") or "").strip(),
        "nodes": preview_nodes,
        "topology_preview": topology_preview,
    }
