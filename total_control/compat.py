from __future__ import annotations

import sys
from typing import Any, Callable


def public_api_override(name: str, current: Callable[..., Any]) -> Callable[..., Any] | None:
    facade = sys.modules.get("total_control.server")
    if facade is None:
        return None
    candidate = getattr(facade, name, None)
    if candidate is None or candidate is current:
        return None
    return candidate


def public_api_value(name: str, default: Any) -> Any:
    facade = sys.modules.get("total_control.server")
    if facade is None or not hasattr(facade, name):
        return default
    return getattr(facade, name)
