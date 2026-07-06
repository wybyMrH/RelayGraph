from __future__ import annotations

from pathlib import Path

import pytest

from total_control.config import ServerConfig
from total_control.infra.shell_pkg.transfer import download_remote_file_to_local
from total_control.utils import browse_local_files, read_local_text_file, resolve_local_browser_target


def test_local_file_browser_filters_sensitive_entries(tmp_path: Path) -> None:
    (tmp_path / "normal.txt").write_text("ok", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=dummy", encoding="utf-8")
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "config").write_text("Host dummy", encoding="utf-8")

    payload = browse_local_files(str(tmp_path), max_entries=50)

    names = {entry["name"] for entry in payload["entries"]}
    assert "normal.txt" in names
    assert ".env" not in names
    assert ".ssh" not in names


@pytest.mark.parametrize("name", [".env", ".master_key", "id_ed25519", "credentials.json"])
def test_local_file_browser_blocks_sensitive_file_read(tmp_path: Path, name: str) -> None:
    target = tmp_path / name
    target.write_text("dummy", encoding="utf-8")

    with pytest.raises(ValueError, match="敏感"):
        read_local_text_file(str(target))


def test_local_file_browser_blocks_sensitive_resolved_symlink(tmp_path: Path) -> None:
    secret_dir = tmp_path / ".ssh"
    secret_dir.mkdir()
    secret_file = secret_dir / "config"
    secret_file.write_text("Host dummy", encoding="utf-8")
    link = tmp_path / "safe-name"
    link.symlink_to(secret_file)

    with pytest.raises(ValueError, match="敏感"):
        resolve_local_browser_target(str(link))


def test_remote_preview_download_blocks_sensitive_source_before_rsync(tmp_path: Path) -> None:
    server = ServerConfig(id="remote", name="Remote", mode="ssh", host_name="example.invalid", user="user")

    with pytest.raises(ValueError, match="敏感"):
        download_remote_file_to_local(server, "~/.ssh/id_ed25519", tmp_path)
