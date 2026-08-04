# Development Roadmap

This roadmap starts after the current architecture optimization phase. The current phase should prepare reusable boundaries and keep existing behavior stable; the items below are the next feature-development phase.

## 1. Real Execution Evidence

- Close the gap between local runs and mixed local/remote Agent + Job workflows.
- Strengthen replayable evidence for workspace execution, job creation, and run records.
- Keep workflow output envelopes and event streams stable while expanding coverage.

## 2. Runtime Adapter Hardening

- Harden provider and remote execution adapters.
- Make cleanup, log retention, and status reporting consistent across local and remote hosts.
- Preserve existing route and payload contracts while tightening edge-case handling.

## 3. Workflow Editor V2

- Improve template editing, node mapping, validation, version history, and repair flows.
- Reuse the existing workspace and template modules instead of introducing duplicate editor paths.
- Keep cockpit and configuration-center responsibilities separate.

## 4. Data Retention and Export

- Define longer-term storage for runtime data, run evidence, and exports.
- Separate transient cache data from records that must survive audits or reruns.
- Keep private machine data local by default.

## 5. Backend Contract Stability

- Lock down the high-risk HTTP surfaces and response envelopes before adding new route shapes.
- Expand contract tests alongside any new public API or event type.
- Treat browser, remote, and provider smoke as supplementary checks, not the main regression gate.

## Quality Bar

- Prefer reuse of existing modules, renderers, and state helpers.
- Add abstraction only when it removes repeated behavior or narrows a boundary.
- Keep the frontend split compatible with the current `window.X` loading model.
