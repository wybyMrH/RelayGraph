"""Provider catalogue: pick-a-vendor + paste-key profile creation.

Lets a profile be created from a known vendor preset (DeepSeek, OpenAI,
Ollama, ...) without typing base_url/protocol, while manual creation still
covers unregistered vendors.
"""

from __future__ import annotations

import threading
from typing import Any

from total_control.constants_pkg.provider_catalog import (
    PROVIDER_CATALOG,
    provider_catalog_by_id,
)
from total_control.state.registry import RegistryMixin


class _FakeState(RegistryMixin):
    """Minimal host exposing only what profile creation touches."""

    def __init__(self) -> None:
        self.provider_profiles: list[dict[str, Any]] = []
        self.lock = threading.RLock()

    def save_provider_profiles(self) -> None:  # no-op for tests
        pass


def test_catalog_lists_known_vendors():
    ids = {item["id"] for item in PROVIDER_CATALOG}
    assert {"deepseek", "openai", "anthropic", "ollama"} <= ids
    assert provider_catalog_by_id("deepseek")["base_url"] == "https://api.deepseek.com"
    assert provider_catalog_by_id("nope") is None


def test_create_from_catalog_materializes_full_profile():
    state = _FakeState()
    result = state.create_provider_profile_from_catalog("deepseek", api_key="sk-test-1234567890")
    # Returned shape is masked (api_key removed, masked shown)
    assert "api_key" not in result
    assert result["kind"] == "llm"
    assert result["provider"] == "openai"
    assert result["base_url"] == "https://api.deepseek.com"
    assert result["models"] == ["deepseek-v4-pro", "deepseek-v4-flash"]
    assert result["name"] == "DeepSeek"
    # The persisted copy keeps the real key.
    persisted = state.provider_profiles[0]
    assert persisted["api_key"] == "sk-test-1234567890"


def test_create_provider_profile_upserts_existing_id_and_preserves_key():
    state = _FakeState()
    state.create_provider_profile(
        {
            "id": "p1",
            "name": "DeepSeek Main",
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "sk-real-1234567890",
            "models": ["deepseek-v4-pro"],
        }
    )
    updated = state.create_provider_profile(
        {
            "id": "p1",
            "name": "DeepSeek Main 2",
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "models": ["deepseek-v4-flash"],
        }
    )
    assert len(state.provider_profiles) == 1
    persisted = state.provider_profiles[0]
    assert persisted["name"] == "DeepSeek Main 2"
    assert persisted["models"] == ["deepseek-v4-flash"]
    assert persisted["api_key"] == "sk-real-1234567890"
    assert updated["api_key_masked"]


def test_create_from_catalog_requires_key_for_keyed_vendors():
    state = _FakeState()
    try:
        state.create_provider_profile_from_catalog("openai", api_key="")
    except ValueError as exc:
        assert "api_key" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing api_key")


def test_create_from_catalog_rejects_unknown_vendor():
    state = _FakeState()
    try:
        state.create_provider_profile_from_catalog("acme-llm", api_key="sk-x")
    except ValueError as exc:
        assert "acme-llm" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown vendor")


def test_local_vendor_created_without_key():
    state = _FakeState()
    result = state.create_provider_profile_from_catalog("ollama")
    assert result["base_url"] == "http://localhost:11434/v1"
    persisted = state.provider_profiles[0]
    # Non-empty sentinel so LLMClient's empty-key guard does not block it.
    assert persisted["api_key"]


def test_is_default_unsets_others():
    state = _FakeState()
    state.create_provider_profile_from_catalog("deepseek", api_key="sk-aaaa11112222", is_default=True)
    state.create_provider_profile_from_catalog("openai", api_key="sk-bbbb33334444", is_default=True)
    defaults = [p for p in state.provider_profiles if p["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["provider"] == "openai"


def test_search_provider_profile_does_not_require_models_and_default_is_per_kind():
    state = _FakeState()
    state.create_provider_profile_from_catalog("openai", api_key="sk-llm-1234567890", is_default=True)
    result = state.create_provider_profile(
        {
            "id": "search-ddg",
            "kind": "search",
            "name": "Duck Search",
            "provider": "duckduckgo",
            "api_key": "",
            "models": [],
            "is_default": True,
            "key_required": False,
        }
    )

    assert result["kind"] == "search"
    assert result["status"] == "ready"
    assert result["key_required"] is False
    llm_defaults = [p for p in state.provider_profiles if p.get("kind", "llm") == "llm" and p.get("is_default")]
    search_defaults = [p for p in state.provider_profiles if p.get("kind") == "search" and p.get("is_default")]
    assert len(llm_defaults) == 1
    assert len(search_defaults) == 1


def test_models_override_and_custom_name():
    state = _FakeState()
    result = state.create_provider_profile_from_catalog(
        "qwen",
        api_key="sk-qwen-1234567890",
        name="我的通义",
        models=["qwen-max"],
    )
    assert result["name"] == "我的通义"
    assert result["models"] == ["qwen-max"]
