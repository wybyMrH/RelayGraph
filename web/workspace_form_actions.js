(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function fieldName(event) {
    return event?.target?.name || "";
  }

  function value(event) {
    return event?.target?.value || "";
  }

  function call(callbacks, name, ...args) {
    fn(callbacks, name, () => {})(...args);
  }

  function callAsync(callbacks, name, ...args) {
    void fn(callbacks, name, async () => {})(...args);
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceForm")?.addEventListener("submit", (event) => {
      callAsync(callbacks, "submitWorkspace", event);
    });
    element(callbacks, "workspaceForm")?.addEventListener("input", (event) => {
      call(callbacks, "handleWorkspaceFormInput", fieldName(event), event);
    });
    element(callbacks, "workspaceSourceType")?.addEventListener("change", (event) => {
      call(callbacks, "handleWorkspaceSourceTypeChange", value(event), event);
    });
    element(callbacks, "workspaceResetBtn")?.addEventListener("click", (event) => {
      call(callbacks, "clearWorkspaceForm", event);
    });
    element(callbacks, "workspaceRunFlowBtn")?.addEventListener("click", (event) => {
      callAsync(callbacks, "runWorkspaceWorkflow", event);
    });
    element(callbacks, "workspaceFillJobBtn")?.addEventListener("click", (event) => {
      call(callbacks, "fillJobFormFromWorkspace", event);
    });
  }

  window.WorkspaceFormActions = {
    bind,
    fieldName,
    value,
  };
})();
