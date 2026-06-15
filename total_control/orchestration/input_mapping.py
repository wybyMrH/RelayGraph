from __future__ import annotations

import copy
import json
from typing import Any

from .workspace_mutations import apply_artifact_write, find_workspace_node


def context_ref_value(data: Any, path: str) -> Any:
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


def _is_mapping_ref(value: str) -> bool:
    ref = str(value or "").strip()
    return ref.startswith("$input") or ref.startswith("$context") or ref.startswith("$prev")


def resolve_input_mapping_ref(
    source: str,
    *,
    input_data: dict[str, Any],
    context_outputs: dict[str, Any] | None = None,
    previous_output: dict[str, Any] | None = None,
    node_config: dict[str, Any] | None = None,
) -> Any:
    ref = str(source or "").strip()
    if not ref:
        return None
    outputs = context_outputs if isinstance(context_outputs, dict) else {}
    config = node_config if isinstance(node_config, dict) else {}
    previous = previous_output if isinstance(previous_output, dict) else {}

    if ref == "$input":
        return copy.deepcopy(input_data)
    if ref.startswith("$input."):
        return context_ref_value(input_data, ref[len("$input."):])
    if ref == "$prev.output":
        return copy.deepcopy(previous) if previous else None
    if ref.startswith("$prev.output."):
        return context_ref_value(previous, ref[len("$prev.output."):])
    if ref == "$context":
        return copy.deepcopy(outputs)
    if ref.startswith("$context.outputs."):
        remainder = ref[len("$context.outputs."):]
        output_key = remainder.split(".", 1)[0]
        value = outputs.get(output_key)
        if "." in remainder:
            return context_ref_value(value, remainder.split(".", 1)[1])
        return copy.deepcopy(value)
    if ref.startswith("$context."):
        return context_ref_value(outputs, ref[len("$context."):])
    if ref == "$node.config":
        return copy.deepcopy(config)
    if ref.startswith("$node.config."):
        return context_ref_value(config, ref[len("$node.config."):])
    if _is_mapping_ref(ref):
        return None
    return ref


def resolve_mapped_inputs(
    input_mapping: dict[str, str],
    *,
    input_data: dict[str, Any],
    context_outputs: dict[str, Any] | None = None,
    previous_output: dict[str, Any] | None = None,
    node_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, source in input_mapping.items():
        name = str(key or "").strip()
        if not name:
            continue
        resolved[name] = resolve_input_mapping_ref(
            str(source or "").strip(),
            input_data=input_data,
            context_outputs=context_outputs,
            previous_output=previous_output,
            node_config=node_config,
        )
    return resolved


def _compact_value(value: Any, *, limit: int = 1200) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text[:limit] + ("…" if len(text) > limit else "")
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, list):
        return [_compact_value(item, limit=400) for item in value[:12]]
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 16:
                compact["…"] = f"+{len(value) - 16} more keys"
                break
            compact[str(key)] = _compact_value(item, limit=400)
        return compact
    return str(value)[:limit]


def build_agent_node_input_text(
    *,
    node_kind: str,
    node_title: str,
    output_key: str,
    mapped_inputs: dict[str, Any],
    goal_text: str = "",
    node_config: dict[str, Any] | None = None,
) -> str:
    config = node_config if isinstance(node_config, dict) else {}
    config_summary = _compact_value(
        {key: config[key] for key in sorted(config.keys()) if config.get(key) not in (None, "", [], {})}
    )
    payload = {
        "goal": str(goal_text or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_title": str(node_title or node_kind or "node").strip(),
        "output_key": str(output_key or "").strip(),
        "mapped_inputs": _compact_value(mapped_inputs),
        "node_config": config_summary,
    }
    instructions = [
        f'Execute workflow node "{payload["node_title"]}" ({payload["node_kind"]}).',
    ]
    if output_key:
        instructions.append(
            f"Produce output for `{output_key}` using artifact.write and/or workflow.edit when appropriate."
        )
    instructions.append("Use mapped_inputs and node_config; do not assume unstated paths or files.")
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return "\n".join(instructions) + "\n\n" + body


def expected_output_format(node: dict[str, Any], contract: dict[str, Any] | None = None) -> str:
    handler = node.get("handler") if isinstance(node, dict) else {}
    contract_format = contract.get("output_format") if isinstance(contract, dict) else ""
    fmt = str(
        handler.get("output_format")
        or node.get("output_format")
        or contract_format
        or ""
    ).strip().lower()
    return fmt


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        stripped = stripped[first_newline + 1 :] if first_newline != -1 else stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def validate_agent_output(
    *,
    output_key: str,
    output_format: str,
    final_answer: str,
) -> dict[str, Any]:
    """Validate an Agent node's final answer against its output contract.

    Returns ``{status, expected_format, parsed, errors}`` where status is one of
    ``ok`` / ``warning`` / ``failed``. JSON contracts that fail to parse or
    missing answers surface as non-ok so callers can record them instead of
    silently accepting malformed output.
    """
    expected = str(output_format or "").strip().lower()
    answer = str(final_answer or "").strip()
    errors: list[str] = []
    if not str(output_key or "").strip():
        return {
            "status": "failed",
            "expected_format": expected,
            "parsed": None,
            "errors": ["节点缺少 output_key 契约，后续节点无法消费输出"],
        }
    if not answer:
        return {
            "status": "failed",
            "expected_format": expected,
            "parsed": None,
            "errors": ["Agent 未产出最终答案"],
        }
    want_json = expected in {"json", "object"}
    looks_json = answer.lstrip().startswith(("{", "["))
    parsed: Any = None
    if want_json:
        try:
            parsed = json.loads(_strip_json_fence(answer))
        except json.JSONDecodeError as exc:
            errors.append(f"output_format 要求 JSON，但最终答案解析失败：{exc.msg}")
    elif looks_json:
        try:
            parsed = json.loads(_strip_json_fence(answer))
        except json.JSONDecodeError:
            parsed = None
    return {
        "status": "warning" if errors else "ok",
        "expected_format": expected,
        "parsed": parsed,
        "errors": errors,
    }


def collect_agent_step_output(
    workspace: dict[str, Any],
    node: dict[str, Any],
    *,
    output_key: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    normalized_key = str(output_key or "").strip()
    artifacts: list[dict[str, Any]] = []
    target = find_workspace_node(
        workspace,
        node_id=str(node.get("id") or "").strip(),
        node_kind=str(node.get("kind") or "").strip(),
    )
    if target:
        runtime = target.get("runtime") if isinstance(target.get("runtime"), dict) else {}
        raw_artifacts = runtime.get("artifacts") if isinstance(runtime.get("artifacts"), list) else None
        if not raw_artifacts and isinstance(target.get("artifacts"), list):
            raw_artifacts = target.get("artifacts")
        if isinstance(raw_artifacts, list):
            artifacts = [item for item in raw_artifacts if isinstance(item, dict)]

    output_value: dict[str, Any] | None = None
    automation = workspace.get("automation") if isinstance(workspace.get("automation"), dict) else {}
    context = automation.get("execution_context") if isinstance(automation.get("execution_context"), dict) else {}
    outputs = context.get("outputs") if isinstance(context.get("outputs"), dict) else {}
    if normalized_key and normalized_key in outputs:
        raw = outputs.get(normalized_key)
        output_value = raw if isinstance(raw, dict) else {"value": raw}
    elif artifacts:
        latest = artifacts[-1]
        output_value = {
            "label": str(latest.get("label") or normalized_key or "artifact").strip(),
            "path": str(latest.get("path") or "").strip(),
            "summary": str(latest.get("summary") or "").strip(),
            "node_id": str((target or node).get("id") or "").strip(),
            "node_kind": str((target or node).get("kind") or "").strip(),
        }
    return artifacts, output_value


def apply_final_answer_output(
    workspace: dict[str, Any],
    node: dict[str, Any],
    *,
    output_key: str,
    final_answer: str,
    output_format: str = "",
    validation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    normalized_key = str(output_key or "").strip()
    answer = str(final_answer or "").strip()
    if not normalized_key or not answer:
        return None

    automation = workspace.get("automation") if isinstance(workspace.get("automation"), dict) else {}
    context = automation.get("execution_context") if isinstance(automation.get("execution_context"), dict) else {}
    outputs = context.get("outputs") if isinstance(context.get("outputs"), dict) else {}
    if normalized_key in outputs:
        return None

    if validation is None:
        validation = validate_agent_output(
            output_key=normalized_key,
            output_format=output_format,
            final_answer=answer,
        )
    parsed = validation.get("parsed")
    status = str(validation.get("status") or "ok").strip()
    content = json.dumps(parsed, ensure_ascii=False, indent=2) if parsed is not None else answer
    label = normalized_key.replace("_", " ").strip() or "output"
    path = f"artifacts/{normalized_key}.json" if parsed is not None else f"artifacts/{normalized_key}.txt"
    result = apply_artifact_write(
        workspace,
        node_id=str(node.get("id") or "").strip(),
        node_kind=str(node.get("kind") or "").strip(),
        label=label,
        path=path,
        content=content,
        output_key=normalized_key,
        artifact_type="json" if parsed is not None else "note",
    )
    if status != "ok" and isinstance(result, dict):
        result["validation"] = {
            "status": status,
            "expected_format": str(validation.get("expected_format") or "").strip(),
            "errors": list(validation.get("errors") or []),
        }
    return result
