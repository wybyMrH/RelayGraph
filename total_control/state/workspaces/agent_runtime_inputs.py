"""Workspace Agent runtime input reference helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403

RUNTIME_INPUT_REF_PREFIXES = ("$input.", "$context.", "$prev.output", "$node.config.")


def _agent_node_runtime_input_refs(
    workspace: dict[str, Any],
    node: dict[str, Any],
    *,
    node_index: int,
    input_mapping: dict[str, str],
    mapped_inputs: dict[str, Any],
    context_outputs: dict[str, Any],
    previous_output: dict[str, Any] | None,
    enforce_previous_output: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    output_catalog: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(nodes):
        if not isinstance(item, dict):
            continue
        output_key = workspace_contract_output_key_for_node(item, index)
        if not output_key or output_key in output_catalog:
            continue
        output_catalog[output_key] = {
            "output_key": output_key,
            "node_id": str(item.get("id") or item.get("kind") or f"node-{index}").strip(),
            "index": index,
            "kind": str(item.get("kind") or "").strip(),
            "title": str(item.get("title") or item.get("kind") or f"节点 {index + 1}").strip(),
        }
    previous_outputs: dict[str, dict[str, Any]] = {}
    for key, value in context_outputs.items():
        output_key = str(key or "").strip()
        if not output_key or value is None:
            continue
        owner = output_catalog.get(output_key, {})
        previous_outputs[output_key] = {
            "output_key": output_key,
            "node_id": str(owner.get("node_id") or "").strip(),
            "index": safe_int(owner.get("index"), -1),
            "kind": str(owner.get("kind") or "").strip(),
            "title": str(owner.get("title") or output_key).strip(),
        }
    if isinstance(previous_output, dict):
        previous_key = str(previous_output.get("output_key") or "").strip()
        if previous_key:
            previous_outputs[previous_key] = {
                "output_key": previous_key,
                "node_id": str(previous_output.get("node_id") or "").strip(),
                "index": safe_int(previous_output.get("index"), node_index - 1),
                "kind": str(previous_output.get("node_kind") or previous_output.get("kind") or "").strip(),
                "title": str(previous_output.get("title") or previous_key).strip(),
            }
    input_refs = workspace_contract_input_refs(input_mapping, node_index, output_catalog, previous_outputs)
    blockers = [
        ref for ref in input_refs
        if isinstance(ref, dict) and str(ref.get("status") or "").strip() in {"blocked", "failed"}
        and (enforce_previous_output or str(ref.get("code") or "").strip() != "first_node_prev_reference")
    ]
    blocker_names = {str(ref.get("name") or "").strip() for ref in blockers if isinstance(ref, dict)}
    for name, source in input_mapping.items():
        input_name = str(name or "").strip()
        source_ref = str(source or "").strip()
        if not input_name or input_name in blocker_names:
            continue
        if not (source_ref in {"$prev.output"} or source_ref.startswith(RUNTIME_INPUT_REF_PREFIXES)):
            continue
        if source_ref.startswith("$prev.output") and not enforce_previous_output:
            continue
        if mapped_inputs.get(input_name) is not None:
            continue
        detail = "运行时输入引用解析为空"
        if source_ref.startswith("$node.config"):
            detail = "节点配置中缺少这个必需输入"
        elif source_ref.startswith("$input"):
            detail = "启动输入中缺少这个必需输入"
        elif source_ref.startswith("$context"):
            detail = "上游上下文中缺少这个必需输出"
        elif source_ref.startswith("$prev.output"):
            detail = "上一节点没有可交接输出"
        blockers.append(
            {
                "name": input_name,
                "source": source_ref,
                "status": "blocked",
                "source_type": "runtime",
                "code": "unresolved_runtime_input",
                "detail": detail,
                "upstream_node_id": "",
                "upstream_output_key": "",
            }
        )
        input_refs.append(blockers[-1])
        blocker_names.add(input_name)
    return input_refs, blockers
