from __future__ import annotations

from typing import Any

from ...constants_pkg.provider_catalog import PROVIDER_CATALOG, provider_catalog_by_id


def normalized_provider_base_url(value: Any) -> str:
    return str(value or "").strip().rstrip("/")


def provider_catalog_for_profile(profile: dict[str, Any]) -> dict[str, Any]:
    vendor_id = str(profile.get("vendor_id") or profile.get("catalog_id") or "").strip()
    if vendor_id:
        vendor = provider_catalog_by_id(vendor_id)
        if vendor:
            return vendor
    base_url = normalized_provider_base_url(profile.get("base_url"))
    if base_url:
        for vendor in PROVIDER_CATALOG:
            if normalized_provider_base_url(vendor.get("base_url")) == base_url:
                return vendor
    return {}


def provider_profile_kind(profile: dict[str, Any]) -> str:
    value = str(profile.get("kind") or profile.get("profile_type") or profile.get("type") or "").strip().lower()
    if value in {"search", "web_search", "web-search"}:
        return "search"
    return "llm"


def provider_profile_key_required(profile: dict[str, Any]) -> bool:
    kind = provider_profile_kind(profile)
    provider = str(profile.get("provider") or profile.get("vendor") or "").strip().lower()
    if kind == "search" and provider in {"duckduckgo", "ddg"}:
        return False
    if "key_required" in profile:
        return bool(profile.get("key_required"))
    vendor = provider_catalog_for_profile(profile)
    if vendor:
        return bool(vendor.get("key_required", True))
    base_url = normalized_provider_base_url(profile.get("base_url")).lower()
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return False
    return True


def search_provider_base_url_required(profile: dict[str, Any]) -> bool:
    provider = str(profile.get("provider") or profile.get("vendor") or "").strip().lower()
    return provider in {"endpoint", "generic", "http", "custom"}


def provider_profile_models(profile: dict[str, Any]) -> list[str]:
    return [
        str(item or "").strip()
        for item in (profile.get("models") if isinstance(profile.get("models"), list) else [])
        if str(item or "").strip()
    ]


def provider_profile_health(profile: dict[str, Any]) -> dict[str, Any]:
    source = profile if isinstance(profile, dict) else {}
    kind = provider_profile_kind(source)
    key_required = provider_profile_key_required(source)
    has_api_key = bool(str(source.get("api_key") or "").strip()) or not key_required
    models = provider_profile_models(source)
    base_url = str(source.get("base_url") or "").strip()
    provider = str(source.get("provider") or source.get("vendor") or "").strip().lower()
    missing_fields: list[str] = []
    if kind == "search":
        if not provider:
            missing_fields.append("provider")
        if search_provider_base_url_required(source) and not base_url:
            missing_fields.append("base_url")
    elif not base_url:
        missing_fields.append("base_url")
    if kind == "llm" and not models:
        missing_fields.append("models")
    if key_required and not str(source.get("api_key") or "").strip():
        missing_fields.append("api_key")
    ready = not missing_fields
    return {
        "status": "ready" if ready else "blocked" if "api_key" in missing_fields or "base_url" in missing_fields else "warning",
        "ready": ready,
        "kind": kind,
        "provider": provider,
        "key_required": key_required,
        "has_api_key": has_api_key,
        "model_count": len(models),
        "missing_fields": missing_fields,
    }


def provider_profile_public_payload(profile: dict[str, Any]) -> dict[str, Any]:
    public_profile = dict(profile if isinstance(profile, dict) else {})
    health = provider_profile_health(public_profile)
    api_key = str(public_profile.get("api_key") or "")
    if api_key:
        public_profile["api_key_masked"] = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        del public_profile["api_key"]
    public_profile["has_api_key"] = bool(api_key) or not bool(health.get("key_required", True))
    public_profile["key_required"] = bool(health.get("key_required", True))
    public_profile["status"] = str(health.get("status") or "warning")
    public_profile["missing_fields"] = list(health.get("missing_fields") or [])
    return public_profile


def provider_profiles_public_payload(profiles: list[Any]) -> list[dict[str, Any]]:
    return [
        provider_profile_public_payload(profile)
        for profile in profiles
    ]
