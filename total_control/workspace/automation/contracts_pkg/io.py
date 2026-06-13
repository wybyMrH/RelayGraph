"""Auto-split from contracts.py — io."""

from __future__ import annotations

from .._deps import *  # noqa: F403
from ...schema.agents_tools import normalize_workspace_agents, normalize_workspace_tools
from ...schema.recipe import normalize_workspace_model
from ..core import workspace_status_priority
from ..evidence import workspace_group_evidence_by_kind
from ..run_plan import workspace_node_required_tool_id, workspace_run_node_phase, workspace_run_phase_label
from ..topology import workspace_model_route_for_agent
def workspace_io_contract_for_kind(kind: str, index: int) -> dict[str, Any]:
    normalized = str(kind or "").strip()
    contract = WORKSPACE_NODE_IO_CONTRACTS.get(normalized)
    if contract:
        return copy.deepcopy(contract)
    output_key = re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_") or f"step_{index + 1}"
    return {
        "inputs": ["上一节点输出", "节点配置"] if index else ["启动输入", "节点配置"],
        "output_key": output_key,
        "evidence": "节点配置、运行结果和交接备注",
    }

def workspace_node_config_signal(node: dict[str, Any]) -> str:
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    for key in (
        "repo_url",
        "workspace_dir",
        "data_roots",
        "dataset_hints",
        "setup_command",
        "run_command",
        "server_id",
        "gpu_index",
        "artifact_paths",
        "metric_paths",
        "report_command",
    ):
        value = str(config.get(key) or "").strip()
        if value:
            return compact_workspace_command(value, limit=140)
    return ""

def workspace_io_input_mapping(node: dict[str, Any], contract: dict[str, Any], index: int) -> dict[str, str]:
    raw_mapping = node.get("input_mapping")
    if isinstance(raw_mapping, dict) and raw_mapping:
        return {
            str(key or "").strip(): str(value or "").strip()
            for key, value in raw_mapping.items()
            if str(key or "").strip()
        }
    inputs = contract.get("inputs") if isinstance(contract.get("inputs"), list) else []
    mapping: dict[str, str] = {}
    for raw in inputs[:6]:
        label = str(raw or "").strip()
        if not label:
            continue
        if index == 0:
            mapping[label] = "$input"
        elif label in {"上一节点输出", "source_context"}:
            mapping[label] = "$prev.output"
        elif label.endswith("_context") or label.endswith("_profile") or label.endswith("_ready") or label.endswith("_allocation"):
            mapping[label] = f"$context.outputs.{label}"
        else:
            mapping[label] = f"$input.{safe_id(label) or label}"
    return mapping

def workspace_has_explicit_input_mapping(node: dict[str, Any]) -> bool:
    raw_mapping = node.get("input_mapping")
    return isinstance(raw_mapping, dict) and any(str(key or "").strip() for key in raw_mapping.keys())

def workspace_contract_output_key_for_node(node: dict[str, Any], index: int) -> str:
    kind = str(node.get("kind") or "").strip()
    contract = workspace_io_contract_for_kind(kind, index)
    return str(node.get("output_key") or contract.get("output_key") or f"step_{index + 1}").strip()

def workspace_contract_input_ref_state(
    source: str,
    index: int,
    output_catalog: dict[str, dict[str, Any]],
    previous_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ref = str(source or "").strip()
    if not ref:
        return {"status": "draft", "source_type": "empty", "detail": "等待输入来源"}
    if ref == "$input" or ref.startswith("$input."):
        return {"status": "ready", "source_type": "input", "detail": "来自启动输入 input_data"}
    if ref == "$prev.output" or ref.startswith("$prev.output."):
        if index > 0 and previous_outputs:
            upstream = next(reversed(previous_outputs.values()))
            return {
                "status": "ready",
                "source_type": "previous",
                "detail": f"来自上一节点 {upstream.get('output_key') or 'output'}",
                "upstream_node_id": str(upstream.get("node_id") or "").strip(),
                "upstream_output_key": str(upstream.get("output_key") or "").strip(),
            }
        return {"status": "blocked", "source_type": "previous", "detail": "首节点不能引用 $prev.output"}
    if ref == "$context":
        return {"status": "ready" if previous_outputs else "warning", "source_type": "context", "detail": "引用整个工作流上下文"}
    if ref.startswith("$context.outputs."):
        output_key = ref[len("$context.outputs."):].split(".", 1)[0]
        previous = previous_outputs.get(output_key)
        if previous:
            return {
                "status": "ready",
                "source_type": "context_output",
                "detail": f"{output_key} 来自上游节点",
                "upstream_node_id": str(previous.get("node_id") or "").strip(),
                "upstream_output_key": output_key,
            }
        owner = output_catalog.get(output_key)
        if owner:
            owner_index = safe_int(owner.get("index"), -1)
            if owner_index == index:
                detail = f"{output_key} 引用了本节点自己的输出"
            elif owner_index > index:
                detail = f"{output_key} 来自下游节点，执行顺序倒挂"
            else:
                detail = f"{output_key} 上游未进入当前上下文"
            return {
                "status": "blocked",
                "source_type": "context_output",
                "detail": detail,
                "upstream_node_id": str(owner.get("node_id") or "").strip(),
                "upstream_output_key": output_key,
            }
        return {
            "status": "blocked",
            "source_type": "context_output",
            "detail": f"{output_key} 没有对应 output_key",
            "upstream_output_key": output_key,
        }
    if ref.startswith("$context."):
        return {"status": "warning", "source_type": "context", "detail": "上下文字段会在运行时解析"}
    return {"status": "ready", "source_type": "literal", "detail": "固定值或节点配置"}

def workspace_contract_input_refs(
    input_mapping: dict[str, str],
    index: int,
    output_catalog: dict[str, dict[str, Any]],
    previous_outputs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for key, value in input_mapping.items():
        name = str(key or "").strip()
        if not name:
            continue
        source = str(value or "").strip()
        state = workspace_contract_input_ref_state(source, index, output_catalog, previous_outputs)
        refs.append(
            {
                "name": name,
                "source": source,
                "status": str(state.get("status") or "draft").strip(),
                "source_type": str(state.get("source_type") or "").strip(),
                "detail": str(state.get("detail") or "").strip(),
                "upstream_node_id": str(state.get("upstream_node_id") or "").strip(),
                "upstream_output_key": str(state.get("upstream_output_key") or "").strip(),
            }
        )
    return refs

def workspace_apply_auto_input_mapping_fallbacks(
    input_mapping: dict[str, str],
    input_refs: list[dict[str, Any]],
) -> None:
    for ref in input_refs:
        if not isinstance(ref, dict):
            continue
        if str(ref.get("status") or "").strip() != "blocked":
            continue
        if str(ref.get("source_type") or "").strip() != "context_output":
            continue
        if str(ref.get("upstream_node_id") or "").strip():
            continue
        detail = str(ref.get("detail") or "").strip()
        if "没有对应 output_key" not in detail:
            continue
        name = str(ref.get("name") or "").strip()
        if not name:
            continue
        input_mapping[name] = "$input"
        ref["source"] = "$input"
        ref["status"] = "ready"
        ref["source_type"] = "input_fallback"
        ref["detail"] = "默认映射未找到上游 output_key，已回退到启动输入或节点配置"
        ref["upstream_output_key"] = ""
