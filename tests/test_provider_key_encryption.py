"""Provider API keys are encrypted at rest, plaintext only in memory."""

from __future__ import annotations

import json
import threading
from typing import Any

import pytest

from total_control import secrets_crypto
from total_control.secrets_crypto import decrypt_secret, encrypt_secret, is_encrypted
from total_control.state.persistence import PersistenceMixin


class _FakeState(PersistenceMixin):
    def __init__(self) -> None:
        self.provider_profiles: list[dict[str, Any]] = []
        self.lock = threading.RLock()


def _isolate_crypto(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(secrets_crypto, "MASTER_KEY_PATH", tmp_path / ".master_key")
    monkeypatch.setattr(secrets_crypto, "_fernet", None)


def test_round_trip(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    cipher = encrypt_secret("sk-secret-1234567890")
    assert cipher != "sk-secret-1234567890"
    assert is_encrypted(cipher)
    assert decrypt_secret(cipher) == "sk-secret-1234567890"


def test_master_key_file_created(monkeypatch, tmp_path):
    master = tmp_path / ".master_key"
    _isolate_crypto(monkeypatch, tmp_path)
    encrypt_secret("x")
    assert master.exists()
    assert master.read_bytes().strip()  # non-empty Fernet key


def test_legacy_plaintext_returned_as_is(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    assert decrypt_secret("sk-legacy-plain") == "sk-legacy-plain"
    assert not is_encrypted("sk-legacy-plain")


def test_empty_stays_empty(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""


def test_encrypt_is_non_deterministic(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    a = encrypt_secret("same-key")
    b = encrypt_secret("same-key")
    assert a != b  # Fernet embeds a random IV/timestamp
    assert decrypt_secret(a) == decrypt_secret(b) == "same-key"


def test_save_writes_ciphertext_and_keeps_plaintext_in_memory(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    store = tmp_path / "provider_profiles.json"
    monkeypatch.setattr("total_control.state.persistence.PROVIDER_PROFILES_PATH", store)

    state = _FakeState()
    state.provider_profiles = [{"id": "p1", "name": "DeepSeek", "api_key": "sk-real-1234567890"}]
    state.save_provider_profiles()

    # in-memory stays plaintext so LLMClient can use it
    assert state.provider_profiles[0]["api_key"] == "sk-real-1234567890"
    # on-disk is ciphertext
    on_disk = json.loads(store.read_text(encoding="utf-8"))
    assert on_disk[0]["api_key"] != "sk-real-1234567890"
    assert is_encrypted(on_disk[0]["api_key"])
    # reload decrypts back to the original key
    assert decrypt_secret(on_disk[0]["api_key"]) == "sk-real-1234567890"


def test_search_provider_key_is_encrypted_too(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    store = tmp_path / "provider_profiles.json"
    monkeypatch.setattr("total_control.state.persistence.PROVIDER_PROFILES_PATH", store)

    state = _FakeState()
    state.provider_profiles = [
        {
            "id": "search-firecrawl",
            "kind": "search",
            "name": "Firecrawl",
            "provider": "firecrawl",
            "api_key": "fc-real-1234567890",
        }
    ]
    state.save_provider_profiles()

    on_disk = json.loads(store.read_text(encoding="utf-8"))
    assert on_disk[0]["api_key"] != "fc-real-1234567890"
    assert is_encrypted(on_disk[0]["api_key"])
    assert decrypt_secret(on_disk[0]["api_key"]) == "fc-real-1234567890"


def test_invalid_ciphertext_does_not_raise(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    encrypt_secret("seed")  # initialise fernet
    assert decrypt_secret("enc:v1:garbage-not-a-real-token") == ""


def test_idempotent_encrypt(monkeypatch, tmp_path):
    _isolate_crypto(monkeypatch, tmp_path)
    once = encrypt_secret("sk-abc-1234567890")
    twice = encrypt_secret(once)  # already encrypted → left as-is
    assert twice == once
