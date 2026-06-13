"""Small shared helpers for automation submodules."""

from __future__ import annotations

from typing import Any

from ._deps import compact_workspace_command  # noqa: F401


def compact_contract_items(values: list[Any], *, limit: int = 6) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = compact_workspace_command(str(raw or "").strip(), limit=180)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
        if len(items) >= limit:
            break
    return items
