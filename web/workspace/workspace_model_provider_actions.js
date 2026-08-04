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

  function handleProviderClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const action = target?.closest("[data-action]");
    if (!action) return;
    if (action.dataset.action === "remove-provider-profile" && action.dataset.profileId) {
      void fn(callbacks, "removeProvider", async () => {})(action.dataset.profileId);
    } else if (action.dataset.action === "test-provider-profile") {
      void fn(callbacks, "testProvider", async () => {})();
    } else if (action.dataset.action === "toggle-provider-key-visibility") {
      fn(callbacks, "toggleKeyVisibility", () => {})();
    }
  }

  function handleProviderField(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target?.matches("[data-provider-field]")) return;
    const key = target.dataset.providerField;
    if (key === "vendor") {
      fn(callbacks, "setProviderVendor", () => {})(target.value);
      return;
    }
    fn(callbacks, "updateProviderField", () => {})(key, target.value);
  }

  function bindModelControls(callbacks = {}) {
    element(callbacks, "workspaceModelProfileSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "setModelProfileId", () => {})(eventTarget(event)?.value || "");
    });
    element(callbacks, "workspaceModelRoutingSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "setModelRoutingMode", () => {})(eventTarget(event)?.value || "workspace_default");
    });
    element(callbacks, "workspaceModelChatAgentSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "setModelChatAgentId", () => {})(eventTarget(event)?.value || "");
    });
    element(callbacks, "workspaceModelNotes")?.addEventListener("input", (event) => {
      fn(callbacks, "setModelNotes", () => {})(eventTarget(event)?.value || "");
    });
  }

  function bindProviderList(callbacks = {}) {
    element(callbacks, "providerProfileList")?.addEventListener("click", (event) => {
      const target = eventTarget(event);
      const button = target?.closest("[data-action='select-provider-profile']");
      if (button?.dataset.profileId) fn(callbacks, "selectProvider", () => {})(button.dataset.profileId);
    });
  }

  function bindProviderEditor(callbacks = {}) {
    const editor = element(callbacks, "providerProfileEditor");
    if (!editor) return null;
    editor.addEventListener("click", (event) => handleProviderClick(event, callbacks));
    editor.addEventListener("input", (event) => handleProviderField(event, callbacks));
    editor.addEventListener("change", (event) => handleProviderField(event, callbacks));
    return editor;
  }

  function bind(callbacks = {}) {
    bindModelControls(callbacks);
    element(callbacks, "workspaceAddProviderBtn")?.addEventListener("click", () => {
      fn(callbacks, "addProvider", () => {})();
    });
    bindProviderList(callbacks);
    bindProviderEditor(callbacks);
  }

  window.WorkspaceModelProviderActions = {
    bind,
    bindModelControls,
    bindProviderEditor,
    bindProviderList,
    handleProviderClick,
    handleProviderField,
  };
})();
