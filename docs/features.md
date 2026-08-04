# Features

RelayGraph is a local operations workbench for GPU machines, remote execution, and reproducible Agent + Job workflows.

## Monitoring Console

- Shows local and SSH-discovered servers.
- Reads GPU state through `nvidia-smi`: memory, utilization, temperature, power, and CUDA processes.
- Supports server sorting, pinning, refresh, hidden server recovery, and SSH connection checks.
- Provides controlled process-stop confirmation for non-owner or owner-unknown processes.

## Execution And Activity

- Launches local or remote commands into `tmux`.
- Supports queued jobs with GPU free-memory and utilization thresholds.
- Tracks job status, exit-code markers, logs, tmux sessions, browser terminal sessions, and output tabs.
- Preserves job/run log evidence while protecting raw runtime paths in public payloads.

## File Transfer

- Builds `rsync` transfer commands with sensitive-path guards.
- Supports local/remote file picking, file preview, favorites, selected-source memory, ignore chips, conflict checks, progress state, and transfer history.

## Workspace Cockpit

- Turns a repo, paper, or idea into a workspace with starter chains.
- Keeps the cockpit focused on goal input, workspace creation, chain selection, execution, feedback, run details, and evidence review.
- Supports project chat, context reflection dismissal, Agent traces, per-node Agent/Job execution, run replay, run export, and run comparison.

## Configuration Center

- Manages workflow templates, template canvas editing, node mappings, validation, repair, version history, and migration review.
- Manages Agent definitions, tool definitions, AI provider profiles, Search Provider profiles, provider route health, diagnostics, and global run overview.
- Keeps advanced configuration out of the cockpit so execution and setup remain separate.

## Provider And Agent Runtime

- Stores provider keys encrypted at rest and plaintext only in memory.
- Supports LLM provider catalog profiles, search provider profiles, no-key local providers, and provider route health checks.
- Runs Agent nodes with tool policy metadata, cancellation/timeout state, output validation, child job tracking, and summary-only event evidence.

## Data And Privacy Boundaries

- Tracked starter data lives in `data/agent_definitions.json`, `data/tool_definitions.json`, and `data/workflow_templates.json`.
- Local runtime state, logs, provider profiles, master key, and user server config are ignored.
- Manual browser, remote, and provider smoke scripts live in ignored `dev_work/`.
