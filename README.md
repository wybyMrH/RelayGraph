# RelayGraph

RelayGraph is a local web dashboard for GPU labs and research workflows. It monitors local or SSH-accessible GPU machines, launches commands in `tmux`, moves files with `rsync`, and provides a node-based workbench for turning repos, papers, and ideas into executable multi-agent workflows.

The backend uses the Python standard library, and the frontend is plain HTML/CSS/JavaScript. Runtime setup stays light: no database, no Node build step, and no required Python package install for the app itself.

## Features

- Monitor local and remote GPUs with `nvidia-smi`: memory, utilization, temperature, power, and CUDA processes.
- Discover SSH hosts from `~/.ssh/config` and merge them with local config overlays.
- Launch background jobs in `tmux`, with optional GPU selection through `CUDA_VISIBLE_DEVICES`.
- Queue jobs until a GPU meets configurable free-memory and utilization thresholds.
- Transfer files with `rsync`, including progress tracking and task history.
- Inspect live `tmux` sessions and open browser-based terminal sessions for selected servers.
- Manage a workbench with projects, workflows, conversations, agents, tools, AI profiles, and run records.
- Generate starter workflow chains from a repo, paper, or idea, then edit nodes, assignments, and execution order.
- Use default agent/tool/workflow registries from `data/*.json`, editable through the app.

## Requirements

- Python 3.11 or newer.
- A modern browser.
- `nvidia-smi` for GPU monitoring.
- `ssh`, `tmux`, and `rsync` for remote execution and file transfer.
- `pytest` only if you want to run the test suite.

RelayGraph works best with SSH key authentication. Password-based SSH is supported for local-only use, but plain-text password files should never be committed or shared.

## Quick Start

Start the local server:

```bash
python -m total_control.server --host 127.0.0.1 --port 8765
```

Open the dashboard:

```text
http://127.0.0.1:8765
```

Run tests:

```bash
python -m pytest -q
```

The app defaults to `127.0.0.1`. Binding to `0.0.0.0` exposes a remote command execution surface and should only be used on a trusted network.

## Configuration

The tracked default config is:

```text
config/servers.toml
```

It starts with a local server and SSH discovery enabled:

```toml
[app]
poll_interval_seconds = 5
remote_timeout_seconds = 6
idle_min_free_mib = 1024
idle_max_gpu_util = 10

[server_aliases]
"local" = "Local"

[[servers]]
id = "local"
name = "Local"
mode = "local"
enabled = true
labels = ["local"]

[ssh_discovery]
enabled = true
config_path = "~/.ssh/config"
include = ["*"]
exclude = []
```

Keep personal machine lists in an ignored local overlay:

```bash
cp config/user_servers.example.toml config/user_servers.toml
```

`config/user_servers.toml` is intended for private SSH paths, aliases, and host lists.

If you must use SSH passwords, create the ignored secrets file:

```bash
cp config/secrets.example.toml config/secrets.toml
```

Example format:

```toml
[ssh_passwords]
"gpu-box" = "your-password"
"192.0.2.10" = "your-password"
"alice@192.0.2.10" = "your-password"
```

Prefer SSH keys whenever possible. `config/secrets.toml` is ignored by Git and should remain local.

## Workbench Data

RelayGraph ships with public starter registries:

```text
data/agent_definitions.json
data/tool_definitions.json
data/workflow_templates.json
```

Runtime data is local and ignored:

```text
data/jobs.json
data/workspaces.json
data/provider_profiles.json
data/logs/
```

AI provider profiles may contain API keys. Keep them local, rotate any key that may have been exposed, and do not include runtime data in public archives or screenshots.

## Project Layout

```text
config/            Example and default configuration
data/              Public starter registries plus ignored runtime state
tests/             Unit and smoke tests
total_control/     Python backend and workflow execution code
web/               Static frontend
```

## Development

Run the full test suite from the repository root:

```bash
python -m pytest -q
```

The project includes `pytest.ini` so local scratch directories such as `temp/` are not collected as tests.

## Roadmap

RelayGraph is evolving from a GPU control panel into a workflow and multi-agent operations workbench. Near-term work focuses on clearer module boundaries for projects, workflows, chat, agent management, tool registration, AI configuration, and run records.

## License

MIT
