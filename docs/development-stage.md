# Development Stage

## Current Stage

The current stage is architecture optimization for future feature development. It is not a product feature expansion stage.

Completed in this stage:

- Formal docs moved into committed `docs/`.
- Local plans, manual smoke scripts, and smoke artifacts moved under ignored `dev_work/`.
- `temp/` cleared from active development use.
- `provider_smoke` reusable merge logic moved from local smoke code into formal source.
- Frontend modules organized by feature folder under `web/`.
- `web/core/app.js` remains the composition root, while catalog data, runtime helpers, and focus/scroll navigation are split into reusable helpers.
- Obsolete `tests/test_provider_smoke.py` removed after its useful assertion was merged into `tests/test_provider_key_encryption.py`.
- Current review status is tracked in `docs/review-status.md`.
- Runtime-storage UI actions moved from `web/core/app.js`/server-admin binding into `web/monitoring/runtime_storage_actions.js`; `app.js` now injects dependencies through thin wrappers.

## Current Guardrails

- Do not add new product functionality during architecture cleanup unless needed to preserve existing behavior.
- Do not move browser/remote/provider smoke into `tests/`.
- Do not stage `dev_work/`, runtime data, provider profile data, secrets, logs, or cache.
- Do not split backend route contracts and frontend consumers in the same change without contract tests.
- Static file serving must keep decoded paths inside `web/`; path-safety regressions belong in `tests/`.

## Next Architecture Slices

- Split remaining server admin UI controller logic out of `web/core/app.js`.
- Split workspace run surfaces and config-center run overview wiring after another contract pass.
- Split transfer/file-picker orchestration surfaces further only if duplicated dependency plumbing remains after review.
- Review old phase-named regression files and rename them only when the rename improves code review clarity without losing history.

## Temporary Records

Known limitations, incomplete behavior, skipped smoke checks, and suspicious code should be recorded in ignored `dev_work/reports/`.
