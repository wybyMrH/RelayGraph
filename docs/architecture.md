# Architecture

RelayGraph is a local web app for GPU monitoring, remote command launch, file transfer, and workflow orchestration.

## Runtime Model

- Backend entrypoint: `python -m total_control.server`
- Server stack: Python standard library HTTP server
- Frontend stack: static HTML/CSS/plain JavaScript
- No database, no Node build step, and no required app-specific Python package install
- Transport: JSON REST, file download/upload handlers, and SSE for workspace event streams
- Persistence model: tracked starter JSON plus ignored local runtime JSON, logs, caches, and encrypted provider secrets

## Backend Layers

- `total_control/server.py` is the compatibility facade and process entrypoint.
- `total_control/handler.py` hosts the HTTP server, static file serving, and request dispatch.
- `total_control/http_api/` contains method-specific route handlers.
- `total_control/state/` owns shared app state, monitoring, jobs, workspaces, templates, and persistence helpers.
- `total_control/orchestration/` contains mixed Agent + Job workflow execution.
- `total_control/workspace/` contains cockpit, execution, automation, normalization, schema, and error handling.
- `total_control/infra/` contains shell, host checks, and browser terminal helpers.
- `total_control/tools/` contains tool registry and workspace executor adapters.

Route handlers are intentionally thin. They parse request inputs, call state or orchestration services, and preserve public response envelopes used by the plain JavaScript client.

Static fallback serving is limited to decoded paths inside `web/`. Any change to `Handler.translate_path` must keep path traversal attempts from resolving to repository files, runtime data, local secrets, or logs.

## Frontend Layers

- `web/index.html` is the app shell and navigation surface.
- `web/core/app.js` remains the composition root.
- `web/core/` holds app-wide runtime helpers, navigation/status actions, labels, formatters, and parsers.
- `web/workspace/` holds cockpit, workspace execution, Agent/tool/run surfaces, event streams, and workspace catalog data.
- `web/workflow-template/` holds template catalog, canvas, validation, mapping, repair, version history, and template review helpers.
- `web/config-center/` holds configuration-center renderers/actions for Agents, tools, AI/provider profiles, diagnostics, and global run overview.
- `web/monitoring/` holds server, GPU/process, job, tmux, log, terminal, runtime-storage, and task-plan UI helpers.
- `web/transfer/` holds file picker, file preview, transfer path, tree, progress, and transfer action helpers.
- `web/styles/` holds CSS.
- The frontend uses `window.X` globals instead of a bundler or module build pipeline.
- New helper modules should expose pure functions or dependency-injected services on `window.X`.
- Helpers should not own global business state or cache DOM nodes that are rebuilt during render.

Current architecture optimization keeps `web/core/app.js` responsible for shared `state`, dependency injection, and top-level rendering composition. Data catalogs, runtime utilities, and focus/scroll behavior are split into reusable helpers because they are low-risk shared behavior.

## Product Surfaces

- Monitoring console: servers, GPUs, jobs, tmux, terminals, and transfer activity.
- Workspace cockpit: project input, starter chains, conversations, agents, tools, and run records.
- Configuration center: templates, agent/tool registries, AI profiles, diagnostics, and global execution views.

The cockpit is the execution surface: goal input, workspace creation, starter-chain selection, feedback, and run inspection. The configuration center is the setup surface: templates, Agents, tools, AI providers, global runtime views, and chain diagnostics.

## UI Boundaries

| Surface | Responsibility | Main Frontend Areas | Allowed Operations |
| --- | --- | --- | --- |
| Workspace cockpit | Run the current instance and inspect execution feedback. | `web/index.html` cockpit panels, `web/workspace/`, `web/core/app.js` composition wiring | Goal input, instance creation, starter-chain selection, run/node focus, feedback, replay, export, and evidence review |
| Global configuration center | Manage reusable setup shared by instances. | `web/config-center/`, `web/workflow-template/`, configuration-center panels in `web/index.html` | Workflow template CRUD/validation, global Agent/tool definitions, AI/provider profiles, diagnostics, and global run overview |
| Instance snapshot advanced editing | Edit the selected workspace instance copy when execution preparation needs exact fields. | Workspace drawer/tabs inside `web/index.html`, `web/workspace/` helpers | Project metadata, node configs, instance Agent/tool/model overrides, and instance-bound run records |

Navigation between these surfaces must make hidden state explicit. Actions that say they will locate an execution node should switch back to the cockpit/use surface before revealing the execution board.

## Data Boundaries

- `config/` holds tracked defaults and local overlays.
- `data/*.json` holds starter registries.
- Runtime data such as jobs, workspaces, provider profiles, logs, and secrets stay local and are not part of the starter surface.
- `docs/` is committed project documentation.
- `dev_work/` is ignored local development workspace for draft plans, manual smoke scripts, generated smoke artifacts, and reports.
