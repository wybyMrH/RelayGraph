from __future__ import annotations

from typing import Any


def build_runtime_storage_cleanup_limits(
    settings: dict[str, Any],
    *,
    remove_all: bool = False,
) -> dict[str, dict[str, int]]:
    return {
        "preview": {
            "max_age_hours": 0 if remove_all else int(settings.get("preview_max_age_hours") or 0),
            "max_size_mib": 0 if remove_all else int(settings.get("preview_max_size_mib") or 0),
        },
        "logs": {
            "max_age_hours": 0 if remove_all else int(settings.get("log_max_age_hours") or 0),
            "max_file_mib": 0 if remove_all else int(settings.get("log_max_file_mib") or 0),
            "max_size_mib": 0 if remove_all else int(settings.get("log_max_size_mib") or 0),
        },
    }


def runtime_storage_cleanup_limits_enabled(limits: dict[str, dict[str, int]]) -> bool:
    preview = limits.get("preview") if isinstance(limits.get("preview"), dict) else {}
    logs = limits.get("logs") if isinstance(limits.get("logs"), dict) else {}
    values = [
        int(preview.get("max_age_hours") or 0),
        int(preview.get("max_size_mib") or 0),
        int(logs.get("max_age_hours") or 0),
        int(logs.get("max_file_mib") or 0),
        int(logs.get("max_size_mib") or 0),
    ]
    return any(value > 0 for value in values)


def runtime_storage_log_cleanup_enabled(limits: dict[str, dict[str, int]]) -> bool:
    logs = limits.get("logs") if isinstance(limits.get("logs"), dict) else {}
    return any(
        int(logs.get(key) or 0) > 0
        for key in ("max_age_hours", "max_file_mib", "max_size_mib")
    )


def runtime_storage_auto_cleanup_interval_seconds(settings: dict[str, Any]) -> int:
    return max(300, int(settings.get("auto_cleanup_interval_minutes") or 60) * 60)
