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

  function value(event) {
    return event?.target?.value || "";
  }

  function call(callbacks, name, ...args) {
    fn(callbacks, name, () => {})(...args);
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceProjectConfigDrawer")?.addEventListener("toggle", (event) => {
      call(callbacks, "setProjectConfigDrawerOpen", Boolean(event.currentTarget?.open), event);
    });
    element(callbacks, "workspaceLauncherPreviewBand")?.addEventListener("toggle", (event) => {
      call(callbacks, "syncLauncherPreview", Boolean(event.currentTarget?.open), event);
    });
    element(callbacks, "workspaceTemplateSelect")?.addEventListener("change", (event) => {
      call(callbacks, "selectWorkspaceTemplate", value(event), event);
    });
    element(callbacks, "workspaceHomeResources")?.addEventListener("change", (event) => {
      const picker = eventTarget(event)?.closest("[data-role='workspace-resource-server-select']");
      if (!picker) return;
      call(callbacks, "selectWorkspaceResourceServer", picker.value || "", event);
    });
  }

  window.WorkspaceShellActions = {
    bind,
  };
})();
