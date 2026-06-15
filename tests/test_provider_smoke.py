from __future__ import annotations

import importlib.util
from pathlib import Path

from total_control.secrets_crypto import encrypt_secret


def _provider_smoke_module():
    path = Path(__file__).resolve().parents[1] / "temp" / "provider_smoke.py"
    spec = importlib.util.spec_from_file_location("provider_smoke_test_module", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_merge_saved_profile_versions_decrypts_and_preserves_key():
    module = _provider_smoke_module()
    merged = module._merge_saved_profile_versions(
        [
            {
                "id": "p1",
                "name": "DeepSeek Main",
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": encrypt_secret("sk-real-1234567890"),
                "models": ["deepseek-v4-pro"],
                "created_at": "2026-06-15T23:37:19",
                "updated_at": "2026-06-15T23:37:19",
            },
            {
                "id": "p1",
                "name": "DeepSeek Main",
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "",
                "models": ["deepseek-v4-flash"],
                "created_at": "2026-06-15T23:37:22",
                "updated_at": "2026-06-15T23:37:22",
            },
        ],
        "p1",
    )
    assert merged is not None
    assert merged["api_key"] == "sk-real-1234567890"
    assert merged["models"] == ["deepseek-v4-flash"]
    assert merged["updated_at"] == "2026-06-15T23:37:22"
