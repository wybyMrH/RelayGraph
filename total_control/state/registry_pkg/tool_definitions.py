from __future__ import annotations

from typing import Any

from ...utils import parse_tag_list


def rewrite_agent_tool_reference(
    agent: dict[str, Any],
    *,
    previous_tool_id: str,
    next_tool_id: str = "",
) -> None:
    previous_tool_id = str(previous_tool_id or "").strip()
    next_tool_id = str(next_tool_id or "").strip()
    if not previous_tool_id or not isinstance(agent, dict):
        return
    tools = parse_tag_list(agent.get("tools", []))
    if next_tool_id:
        agent["tools"] = [next_tool_id if item == previous_tool_id else item for item in tools]
    else:
        agent["tools"] = [item for item in tools if item != previous_tool_id]
