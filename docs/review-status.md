# Review Status

Updated: 2026-08-13

This page records the current project review status for maintainers. It is a committed summary, not a scratch investigation log.

## Current Conclusion

- RelayGraph is in the architecture optimization stage, preparing for later feature work.
- The backend route/state/workspace/execution/tool split is stable enough for current regression work.
- The frontend has been moved into feature folders, while `web/core/app.js` remains the composition root for global state, dependency injection, and top-level render orchestration.
- `tests/` remains the committed deterministic regression gate. Browser, remote-host, and live-provider smoke scripts stay under ignored `dev_work/smokes/`.
- `dev_work/`, `temp/`, runtime data, logs, secrets, and caches must not be submitted.

## Fixed In This Review

- Static file path translation now keeps all fallback static requests inside `web/` after URL decoding and path normalization.
- A regression test covers encoded and plain `..` static path traversal attempts.
- Provider profile single-resource GET/PUT/POST fallback/DELETE routes now match `/api/provider-profiles/{id}` through a shared single-segment path helper instead of a fragile string slice.
- Workspace focus navigation removed a duplicate selector branch left by the helper extraction.
- Selecting an execution node from configuration-center diagnostics now returns to the cockpit/use surface before revealing the execution board.
- User-facing frontend service/error text now uses the current product name, RelayGraph, while compatibility log markers such as `[total-control]` remain unchanged.
- Runtime-storage UI actions are split into `web/monitoring/runtime_storage_actions.js`, leaving `web/core/app.js` as a dependency-injecting composition root and keeping `server_admin_actions.js` focused on server admin interactions.

## Open Follow-Ups

- `web/core/app.js` is still the largest maintenance risk and should continue shrinking by low-risk controller slices.
- The next frontend slices should target remaining server admin UI logic and then workspace run/config-center overview wiring after another contract review.
- Workspace executor adapters still include plan-only or blocked paths for tools that are registered but not implemented as real runtime adapters.
- Remote, browser, and provider smoke coverage depends on local environment and should record skips or failures in `dev_work/reports/`.

## Review Checklist

- Check route contracts before changing frontend fetch payloads or response handling.
- Check `web/index.html` script order whenever adding or moving a `window.X` helper.
- Keep helpers dependency-injected; do not let helper modules own rebuilt DOM or global business state.
- Add committed tests for path safety, persistence, public payload redaction, API envelopes, and execution state transitions.
- Put temporary reproduction scripts, screenshots, provider credentials, generated logs, and skipped smoke notes under `dev_work/`.
