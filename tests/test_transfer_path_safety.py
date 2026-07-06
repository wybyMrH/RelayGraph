from __future__ import annotations

from pathlib import Path

import pytest

from total_control.config import ServerConfig
from total_control.infra.shell_pkg.transfer import (
    build_transfer_command,
    check_transfer_conflicts,
)


def _remote() -> ServerConfig:
    return ServerConfig(
        id="remote-a",
        name="Remote A",
        mode="ssh",
        host_name="example.invalid",
        user="alice",
    )


@pytest.mark.parametrize(
    "source",
    [
        "~/.ssh/id_ed25519",
        "/tmp/project/.env",
        "/tmp/project/.master_key",
        "/proc/123/environ",
        "/run/secrets/token",
    ],
)
def test_build_transfer_command_blocks_sensitive_sources(source: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="传输源.*敏感"):
        build_transfer_command(
            {
                "sources": [{"path": source, "value": source, "is_dir": False}],
                "target": str(tmp_path),
            },
            [],
        )


@pytest.mark.parametrize(
    "target",
    [
        "~/.ssh",
        "/tmp/project/.env",
        "/tmp/project/.master_key",
        "/proc/123/environ",
        "/run/secrets/token",
    ],
)
def test_build_transfer_command_blocks_sensitive_targets(target: str, tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("ok", encoding="utf-8")

    with pytest.raises(ValueError, match="传输目标.*敏感"):
        build_transfer_command(
            {
                "sources": [{"path": str(source), "value": str(source), "is_dir": False}],
                "target": target,
            },
            [],
        )


def test_check_transfer_conflicts_blocks_sensitive_before_probe(monkeypatch, tmp_path: Path) -> None:
    called = False

    def fake_exists(*_args, **_kwargs):
        nonlocal called
        called = True
        return False

    monkeypatch.setattr("total_control.infra.shell_pkg.transfer.transfer_path_exists", fake_exists)

    with pytest.raises(ValueError, match="传输目标.*敏感"):
        check_transfer_conflicts(
            {
                "sources": [{"path": str(tmp_path / "source.txt"), "is_dir": False}],
                "target": "/run/secrets",
            },
            [],
        )

    assert called is False


@pytest.mark.parametrize("endpoint", ["unknown:/tmp/file", "remote-a:relative/file", "remote-a:~/file"])
def test_build_transfer_command_rejects_uncontrolled_remote_endpoints(endpoint: str, tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("ok", encoding="utf-8")

    with pytest.raises(ValueError, match="远程传输"):
        build_transfer_command(
            {
                "sources": [{"path": str(source), "value": endpoint, "is_dir": False}],
                "target": str(tmp_path / "dest"),
            },
            [_remote()],
        )


def test_build_transfer_command_uses_protect_args_separator_and_sensitive_excludes(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("ok", encoding="utf-8")
    target = tmp_path / "dest"

    command, display = build_transfer_command(
        {
            "sources": [{"path": str(source), "value": str(source), "is_dir": False}],
            "target": str(target),
        },
        [],
    )

    assert "--protect-args" in command
    assert " -- " in command
    assert "--exclude '.ssh/***'" in display
    assert "--exclude .env" in display


def test_check_transfer_conflicts_checks_single_file_target_itself(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    target = tmp_path / "existing-target.txt"
    source.write_text("source", encoding="utf-8")
    target.write_text("existing", encoding="utf-8")

    result = check_transfer_conflicts(
        {
            "sources": [{"path": str(source), "value": str(source), "is_dir": False}],
            "target": str(target),
        },
        [],
    )

    assert result["checked"] is True
    assert [item["destination"] for item in result["conflicts"]] == [str(target)]
