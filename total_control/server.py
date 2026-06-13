"""RelayGraph HTTP server — public facade re-exporting split modules."""

from __future__ import annotations

# Preserve `python -m total_control.server` and test imports.
from .config import (
    AppConfig,
    ServerConfig,
    config_alias,
    dump_toml,
    load_config,
    load_secrets,
    load_user_overlay,
    parse_ssh_config,
    save_user_overlay,
    secret_password,
)
from .constants import *  # noqa: F403
from .handler import Handler, STATE, main, run
from .infra.checks import build_process_stop_script, run_server_checks, stop_server_process
from .infra.shell import *  # noqa: F403
from .infra.web_terminal import WebTerminal, set_terminal_winsize
from .state import TotalControlState
from .utils import *  # noqa: F403
from .workspace.cockpit import *  # noqa: F403
from .workspace.errors import WorkspaceWorkflowReadinessError
from .workspace.normalize import *  # noqa: F403
from .workspace.execution import *  # noqa: F403
from .workspace.automation import *  # noqa: F403

__all__ = [name for name in globals() if not name.startswith("_")]
