(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.matches === "function") return target;
    return target?.parentElement && typeof target.parentElement.matches === "function" ? target.parentElement : null;
  }

  function handlePanelClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "refresh-execution-overview") {
      void fn(callbacks, "refreshOverview", async () => {})();
    } else if (button.dataset.action === "reset-execution-overview-filters") {
      fn(callbacks, "resetFilters", () => {})();
    } else if (button.dataset.action === "open-overview-workspace") {
      fn(callbacks, "openWorkspace", () => {})(button.dataset.workspaceId || "");
    }
  }

  function handleSearchInput(event, callbacks = {}) {
    const target = eventTarget(event);
    fn(callbacks, "setQuery", () => {})(target?.value || "");
  }

  function handleStatusChange(event, callbacks = {}) {
    const target = eventTarget(event);
    fn(callbacks, "setStatus", () => {})(target?.value || "");
  }

  function handleKindChange(event, callbacks = {}) {
    const target = eventTarget(event);
    fn(callbacks, "setKind", () => {})(target?.value || "all");
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceManageRunsPanel")?.addEventListener("click", (event) => handlePanelClick(event, callbacks));
    element(callbacks, "workspaceExecutionOverviewSearch")?.addEventListener("input", (event) => handleSearchInput(event, callbacks));
    element(callbacks, "workspaceExecutionOverviewStatusFilter")?.addEventListener("change", (event) => handleStatusChange(event, callbacks));
    element(callbacks, "workspaceExecutionOverviewKindFilter")?.addEventListener("change", (event) => handleKindChange(event, callbacks));
  }

  window.ConfigCenterExecutionOverviewActions = {
    bind,
    handleKindChange,
    handlePanelClick,
    handleSearchInput,
    handleStatusChange,
  };
})();
