# Development Guide

## Local Setup

Run the app from the repository root:

```bash
python -m total_control.server --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

## Project Map

- `total_control/handler.py` serves static files and dispatches HTTP methods.
- `total_control/http_api/` owns route handlers.
- `total_control/state/` owns persisted state and public payload assembly.
- `total_control/orchestration/` owns workflow execution.
- `total_control/workspace/` owns workspace schemas, cockpit, automation, and execution helpers.
- `total_control/tools/` owns tool registry and workspace executor adapters.
- `web/index.html` is the frontend shell.
- `web/core/` is the frontend composition/runtime layer.
- `web/workspace/`, `web/workflow-template/`, `web/config-center/`, `web/monitoring/`, and `web/transfer/` are feature folders.
- `docs/` is committed project documentation.
- `dev_work/` is ignored local work: draft plans, manual smoke scripts, generated smoke artifacts, and reports.

## Frontend Rules

- Keep plain JavaScript and `window.X` helpers; do not introduce npm, bundlers, ES modules, or frameworks in the current phase.
- Keep `web/core/app.js` as the composition root for global `state`, dependency injection, and top-level render orchestration.
- Put reusable data, formatting, normalization, action handlers, and render helpers into the feature folder that owns them.
- Helpers should accept dependencies or data arguments; they should not own business state or cache DOM nodes rebuilt by render.
- Preserve the cockpit/config-center boundary: cockpit is for execution, configuration center is for setup and diagnostics.

## Backend Rules

- Keep HTTP response envelopes and SSE event types stable unless a contract test changes with them.
- Route handlers should parse inputs, call state/orchestration services, and return public payloads.
- Do not expose raw provider keys, raw runtime log paths, or private local machine paths in public payloads.
- Add durable regressions under `tests/` for contract, safety, persistence, and execution behavior.

## Test Workflow

Run the standard checks before commit:

```bash
python -m compileall -q total_control
python -m pytest -q
for f in web/**/*.js; do node --check "$f" || exit 1; done
```

Use `dev_work/smokes/` for browser-heavy, remote-machine, or live-provider checks. Put generated output under `dev_work/artifacts/smokes/`.

## Change Hygiene

- Keep related changes together and avoid unrelated rewrites.
- Prefer extracting repeated behavior over adding new one-off helpers.
- When behavior is incomplete, blocked, or risky, record it in `dev_work/reports/` instead of hiding it in code comments.
- Check `git status --short --ignored` before commit so local runtime data, secrets, cache, and `dev_work/` are not staged.
