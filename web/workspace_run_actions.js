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
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function call(callbacks, name, ...args) {
    return fn(callbacks, name, () => {})(...args);
  }

  function callAsync(callbacks, name, ...args) {
    void fn(callbacks, name, async () => {})(...args);
  }

  function handleWorkspaceListClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const deleteButton = target?.closest("[data-action='delete-workspace']");
    if (deleteButton?.dataset.workspaceId) {
      event?.stopPropagation?.();
      callAsync(callbacks, "deleteWorkspace", deleteButton.dataset.workspaceId);
      return;
    }
    const item = target?.closest("[data-action='select-workspace']");
    if (item?.dataset.workspaceId) call(callbacks, "selectWorkspace", item.dataset.workspaceId);
  }

  function handleRunFilter(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target?.matches("[data-workspace-run-filter]")) return;
    call(callbacks, "updateRunFilter", target.dataset.workspaceRunFilter || "", target.value || "");
  }

  function handleRunListKeydown(event, callbacks = {}) {
    if (!["Enter", " "].includes(event.key)) return;
    const item = eventTarget(event)?.closest(".workspace-run-item[data-job-id], .workspace-execution-run-item[data-run-id]");
    if (!item?.dataset.jobId && !item?.dataset.runId) return;
    call(callbacks, "consumeEvent", event);
    if (item.dataset.jobId) callAsync(callbacks, "openJobLog", item.dataset.jobId);
    else callAsync(callbacks, "openRunDetail", item.dataset.runId);
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceList")?.addEventListener("click", (event) => {
      handleWorkspaceListClick(event, callbacks);
    });
    element(callbacks, "workspaceHistoryList")?.addEventListener("click", (event) => {
      handleWorkspaceListClick(event, callbacks);
    });
    element(callbacks, "workspaceRunList")?.addEventListener("click", (event) => {
      call(callbacks, "handleRunSurfaceClick", event);
    });
    element(callbacks, "workspaceHomeRuns")?.addEventListener("click", (event) => {
      call(callbacks, "handleRunSurfaceClick", event);
    });
    element(callbacks, "workspaceRunList")?.addEventListener("input", (event) => {
      handleRunFilter(event, callbacks);
    });
    element(callbacks, "workspaceRunList")?.addEventListener("change", (event) => {
      handleRunFilter(event, callbacks);
    });
    element(callbacks, "workspaceRunList")?.addEventListener("keydown", (event) => {
      handleRunListKeydown(event, callbacks);
    });
  }

  window.WorkspaceRunActions = {
    bind,
    handleRunFilter,
    handleRunListKeydown,
    handleWorkspaceListClick,
  };
})();
