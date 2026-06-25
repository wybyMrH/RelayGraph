from __future__ import annotations

import copy
import re
import uuid
from typing import Any

from ...constants import *  # noqa: F403
from ...utils import *  # noqa: F403
from ..errors import WorkspaceWorkflowReadinessError


def normalize_workspace_recipe(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    recipe_id = str(payload.get("recipe_id") or current.get("id") or "default").strip() or "default"
    name = str(payload.get("recipe_name") or current.get("name") or "默认运行").strip() or "默认运行"
    return {
        "id": safe_id(recipe_id),
        "name": name,
        "setup_command": str(payload.get("setup_command") or current.get("setup_command") or "").strip(),
        "run_command": str(payload.get("run_command") or current.get("run_command") or "").strip(),
        "report_command": str(payload.get("report_command") or current.get("report_command") or "").strip(),
        "schedule": str(payload.get("schedule") or current.get("schedule") or "").strip(),
        "notes": str(payload.get("recipe_notes") or current.get("notes") or "").strip(),
        "enabled": bool(payload.get("recipe_enabled", current.get("enabled", True))),
    }

def clean_workspace_config_default(kind: str, key: str, value: Any) -> Any:
    text = str(value or "").strip()
    placeholder_values = {
        ("research.search", "goal"): {"检索相关代码仓库、依赖和运行方式"},
        ("path.resolve", "output_roots"): {"runs\noutputs\ncheckpoints\nlogs"},
        ("repo.inspect", "questions"): {"入口、依赖、默认配置、结果目录"},
        ("env.infer", "manifest_paths"): {
            "requirements.txt, pyproject.toml, environment.yml, setup.py",
            "requirements.txt, pyproject.toml, environment.yml, conda.yml, setup.py",
        },
        ("artifact.collect", "artifact_paths"): {"runs\noutputs\ncheckpoints\nlogs"},
    }
    if text in placeholder_values.get((str(kind or "").strip(), str(key or "").strip()), set()):
        return ""
    return value

def normalize_workspace_handler(value: Any) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    mode = str(current.get("mode") or "human").strip().lower()
    if mode not in {"human", "agent", "system"}:
        mode = "human"
    max_iterations_raw = current.get("max_iterations")
    max_iterations = safe_int(max_iterations_raw, 0) if max_iterations_raw not in (None, "") else 0
    timeout_raw = current.get("timeout_seconds")
    timeout_seconds = float(timeout_raw) if timeout_raw not in (None, "") and safe_int(timeout_raw, 0) > 0 else 0.0
    output_format = str(current.get("output_format") or "").strip().lower()
    if output_format not in {"", "text", "json"}:
        output_format = ""
    payload: dict[str, Any] = {
        "mode": mode,
        "agent_id": safe_id(str(current.get("agent_id") or "")) if str(current.get("agent_id") or "").strip() else "",
        "name": str(current.get("name") or "").strip(),
        "handoff": str(current.get("handoff") or "").strip(),
        "output_key": str(current.get("output_key") or "").strip(),
    }
    if max_iterations > 0:
        payload["max_iterations"] = max_iterations
    if timeout_seconds > 0:
        payload["timeout_seconds"] = timeout_seconds
    if output_format:
        payload["output_format"] = output_format
    return payload

def normalize_workspace_runtime(value: Any) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    return {
        "run_count": max(safe_int(current.get("run_count"), 0), 0),
        "last_job_id": str(current.get("last_job_id") or "").strip(),
        "last_job_name": str(current.get("last_job_name") or "").strip(),
        "last_job_kind": str(current.get("last_job_kind") or "").strip(),
        "last_job_status": str(current.get("last_job_status") or "").strip(),
        "last_run_at": str(current.get("last_run_at") or "").strip(),
        "last_finished_at": str(current.get("last_finished_at") or "").strip(),
        "last_error": str(current.get("last_error") or "").strip(),
        "trace": copy.deepcopy(current.get("trace")) if isinstance(current.get("trace"), list) else [],
        "artifacts": copy.deepcopy(current.get("artifacts")) if isinstance(current.get("artifacts"), list) else [],
        "resources": copy.deepcopy(current.get("resources")) if isinstance(current.get("resources"), dict) else {},
    }

def normalize_workspace_model(
    value: Any,
    *,
    existing: Any = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    routing_mode = str(current.get("routing_mode") or previous.get("routing_mode") or "workspace_default").strip()
    if routing_mode not in {"workspace_default", "agent_override"}:
        routing_mode = "workspace_default"
    return {
        "provider_profile_id": str(current.get("provider_profile_id") or previous.get("provider_profile_id") or "").strip(),
        "routing_mode": routing_mode,
        "chat_agent_id": safe_id(str(current.get("chat_agent_id") or previous.get("chat_agent_id") or ""))
        if str(current.get("chat_agent_id") or previous.get("chat_agent_id") or "").strip()
        else "",
        "notes": str(current.get("notes") or previous.get("notes") or "").strip(),
    }

def normalize_workspace_inputs(
    payload: Any,
    *,
    existing: Any = None,
) -> dict[str, Any]:
    current = payload if isinstance(payload, dict) else {}
    previous = existing if isinstance(existing, dict) else {}

    repo_urls = parse_line_list(
        current.get("repo_urls")
        if "repo_urls" in current
        else current.get("repo_references")
        if "repo_references" in current
        else previous.get("repo_urls", [])
    )
    paper_urls = parse_line_list(
        current.get("paper_urls")
        if "paper_urls" in current
        else current.get("paper_references")
        if "paper_references" in current
        else previous.get("paper_urls", [])
    )
    references = parse_line_list(current.get("references", previous.get("references", [])))
    context_blocks = parse_line_list(
        current.get("context_blocks")
        if "context_blocks" in current
        else current.get("context")
        if "context" in current
        else previous.get("context_blocks", [])
    )
    goal_text = str(
        current.get("goal_text")
        or current.get("brief")
        or current.get("idea_text")
        or previous.get("goal_text")
        or previous.get("brief")
        or ""
    ).strip()
    source_mode = normalize_source_mode(
        current.get("source_mode")
        or previous.get("source_mode")
        or infer_source_mode_from_inputs(repo_urls=repo_urls, paper_urls=paper_urls, goal_text=goal_text)
    )
    return {
        "goal_text": goal_text,
        "repo_urls": repo_urls,
        "paper_urls": paper_urls,
        "references": references,
        "context_blocks": context_blocks,
        "source_mode": source_mode,
    }

def normalize_source_mode(value: str) -> str:
    source_mode = str(value or "").strip().lower()
    if source_mode in {"repo", "paper", "idea", "mixed"}:
        return source_mode
    return "idea"

def infer_source_mode_from_inputs(
    *,
    repo_urls: list[str],
    paper_urls: list[str],
    goal_text: str,
) -> str:
    has_repo = bool(repo_urls)
    has_paper = bool(paper_urls)
    has_goal = bool(str(goal_text or "").strip())
    count = sum(1 for flag in (has_repo, has_paper, has_goal) if flag)
    if count > 1 and (has_repo or has_paper):
        return "mixed"
    if has_repo:
        return "repo"
    if has_paper:
        return "paper"
    return "idea"

def source_type_for_chain(value: str) -> str:
    source_mode = normalize_source_mode(value)
    if source_mode == "mixed":
        return "idea"
    return source_mode

def workspace_input_source_summary(inputs: dict[str, Any]) -> tuple[str, str, str, str]:
    repo_urls = parse_line_list(inputs.get("repo_urls", []))
    paper_urls = parse_line_list(inputs.get("paper_urls", []))
    goal_text = str(inputs.get("goal_text") or "").strip()
    source_mode = normalize_source_mode(inputs.get("source_mode") or "")
    repo_url = repo_urls[0] if repo_urls else ""
    paper_url = paper_urls[0] if paper_urls else ""
    idea_text = goal_text
    chain_source_type = source_type_for_chain(source_mode)
    return chain_source_type, repo_url, paper_url, idea_text
