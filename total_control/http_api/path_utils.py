from __future__ import annotations

from urllib.parse import unquote


def single_segment_path_id(path: str, prefix: str) -> str:
    """Return one decoded path segment after prefix, or an empty string."""
    if not path.startswith(prefix):
        return ""
    tail = path[len(prefix):]
    value = unquote(tail)
    if not value or "/" in value:
        return ""
    return value
