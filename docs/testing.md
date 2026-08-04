# Testing

## Committed Suite

- `tests/` is the committed regression suite.
- `python -m pytest -q` is the main project test command.
- The suite covers contract and safety behavior, including HTTP routes, SSE/replay, workflow data contracts, provider profiles, runtime storage, scheduler behavior, and path safety.

Representative coverage:

- `tests/test_events.py`
- `tests/test_http_get_routes.py`
- `tests/test_handler.py`
- `tests/test_provider_profile_routes.py`
- `tests/test_workflow_data_contract.py`
- `tests/test_transfer_path_safety.py`
- `tests/test_file_browser_path_safety.py`
- `tests/test_runtime_storage_maintenance.py`
- `tests/test_scheduler_terminal_status.py`
- `tests/test_phase5_execution_package.py`
- `tests/test_phase6_*.py`
- `tests/test_provider_*.py`

## Local-Only Smoke

- Browser-heavy, remote-host, and provider-network smoke checks belong in local scratch space and are not part of the committed regression suite.
- Use them for manual verification of UI flows, remote command paths, and live provider connectivity.
- Keep them out of `tests/` so the regression gate stays fast and deterministic.
- Store local smoke scripts under `dev_work/smokes/`; store their generated output under `dev_work/artifacts/smokes/`.
- Store draft plans under `dev_work/plans/`; store review notes under `dev_work/reports/`.
- `dev_work/` is ignored and should not be staged.

## Suggested Checks

```bash
python -m compileall -q total_control
python -m pytest -q
for f in web/**/*.js; do node --check "$f" || exit 1; done
git status --short --ignored
git ls-files temp docs dev_work
git check-ignore -v dev_work/plans/example.md docs/README.md
```

`docs/README.md` should not match an ignore rule. `dev_work/plans/example.md` should match the `dev_work/` ignore rule.

## Boundary Notes

- Add new durable regressions to `tests/`.
- Static file serving changes need path traversal and resource path checks.
- API single-resource routes should have direct route harness coverage for the paths used by the frontend.
- Frontend reorganization should include `index.html` static reference checks and `window.X` load-order smoke when helpers move.
- Keep one-off smoke scripts outside the committed suite.
- Do not use runtime data or cached logs as test fixtures.
