"""Pure context path lookup shared by execution and workspace projections."""

from __future__ import annotations

from typing import Any


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
