(function () {
  "use strict";

  const WORKSPACE_ACTION_SURFACE_IDS = [
    "workspaceLauncherPlan",
    "workspaceLauncherDetails",
    "workspaceCapabilityBaseline",
    "workspaceHomeDecision",
    "workspaceHomeCockpit",
    "workspaceHomePreflight",
    "workspaceHomeContext",
    "workspaceHomeActions",
    "workspaceHomeQuickLinks",
    "workspaceProjectQueue",
    "workspaceWorkflowSummary",
    "workspaceHomeFlow",
    "workspaceHomeReadiness",
    "workspaceHomeResources",
    "workspaceHomeTopology",
    "workspaceHomeRuns",
    "workspaceAgentCoverageSummary",
    "workspaceToolCatalogSummary",
    "workspaceModelRoutingSummary",
    "workspaceManageInspectChain",
    "workspaceManageInspectHandoff",
    "workspaceManageInspectGaps",
    "workspaceManageInspectReadiness",
  ];

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function query(callbacks, selector) {
    return fn(callbacks, "query", (value) => document.querySelector(value))(selector);
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function routeActionClick(event, callbacks = {}) {
    const button = eventTarget(event)?.closest("[data-action]");
    if (button) fn(callbacks, "handleAutomationAction", () => {})(button);
  }

  function bindActionSurface(root, callbacks = {}) {
    root?.addEventListener("click", (event) => {
      routeActionClick(event, callbacks);
    });
  }

  function bind(callbacks = {}) {
    bindActionSurface(element(callbacks, "workspaceExecutionBoard"), callbacks);
    bindActionSurface(query(callbacks, ".workspace-execution-inspector"), callbacks);
    bindActionSurface(element(callbacks, "workspaceExecutionDetail"), callbacks);
    WORKSPACE_ACTION_SURFACE_IDS.forEach((id) => {
      bindActionSurface(element(callbacks, id), callbacks);
    });
  }

  window.WorkspaceActionSurfaces = {
    WORKSPACE_ACTION_SURFACE_IDS,
    bind,
    bindActionSurface,
    eventTarget,
    routeActionClick,
  };
})();
