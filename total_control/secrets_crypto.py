"""At-rest encryption for local secrets (provider API keys).

Provider keys live in ``data/provider_profiles.json`` (gitignored). To avoid
plaintext at rest — especially on synced Windows drives mounted under WSL —
keys are encrypted with a Fernet key stored in a separate gitignored file
(``data/.master_key``, 0600). In memory the keys stay plaintext so LLMClient
can use them; only the on-disk file holds ciphertext.

Legacy plaintext values (no ``enc:v1:`` prefix) are returned as-is and get
re-encrypted on the next save, so no manual migration is needed.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

from .constants_pkg.paths import DATA_DIR

MASTER_KEY_PATH = DATA_DIR / ".master_key"
_PREFIX = "enc:v1:"
_fernet: Fernet | None = None


def _load_or_create_master_key() -> bytes:
    MASTER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MASTER_KEY_PATH.exists():
        data = MASTER_KEY_PATH.read_bytes().strip()
        if data:
            return data
    key = Fernet.generate_key()
    fd = os.open(str(MASTER_KEY_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, key)
    finally:
        os.close(fd)
    return key


def _fernet_instance() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_master_key())
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    text = str(plaintext or "")
    if not text or text.startswith(_PREFIX):
        return text
    token = _fernet_instance().encrypt(text.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_secret(stored: str) -> str:
    text = str(stored or "")
    if not text.startswith(_PREFIX):
        return text
    try:
        return _fernet_instance().decrypt(text[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def is_encrypted(value: str) -> bool:
    return str(value or "").startswith(_PREFIX)
