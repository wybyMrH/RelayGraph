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

  function handleInput(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.matches("[data-manage-provider-field]")) {
      fn(callbacks, "updateProviderField", () => {})(
        target.dataset.manageProviderField,
        target.value || "",
      );
    }
  }

  function handleChange(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.id === "manageAiTemplateProfileSelect") {
      fn(callbacks, "setTemplateProfileId", () => {})(target.value || "");
      return;
    }
    if (target.id === "manageAiTemplateRoutingSelect") {
      fn(callbacks, "setTemplateRoutingMode", () => {})(target.value || "workspace_default");
      return;
    }
    if (target.id === "manageAiTemplateChatAgentSelect") {
      fn(callbacks, "setTemplateChatAgentId", () => {})(target.value || "");
      return;
    }
    if (target.matches("[data-manage-provider-field]")) {
      const key = target.dataset.manageProviderField;
      if (key === "kind") {
        fn(callbacks, "setProviderKind", () => {})(target.value || "");
        return;
      }
      if (key === "vendor") {
        fn(callbacks, "setProviderVendor", () => {})(target.value || "");
        return;
      }
      fn(callbacks, "updateProviderField", () => {})(key, target.value || "");
      return;
    }
    if (target.matches("[data-manage-provider-checkbox]")) {
      const key = target.dataset.manageProviderCheckbox;
      if (key) fn(callbacks, "updateProviderCheckbox", () => {})(key, Boolean(target.checked));
    }
  }

  function handleClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "save-provider-profile") {
      void fn(callbacks, "saveProfile", async () => {})();
    } else if (button.dataset.action === "test-provider-profile") {
      void fn(callbacks, "testProfile", async () => {})();
    } else if (button.dataset.action === "fetch-provider-models") {
      void fn(callbacks, "fetchModels", async () => {})();
    } else if (button.dataset.action === "pick-provider-model") {
      event.preventDefault();
      const model = button.dataset.model || "";
      if (model) fn(callbacks, "pickModel", () => {})(model);
    } else if (button.dataset.action === "toggle-provider-key-visibility") {
      fn(callbacks, "toggleKeyVisibility", () => {})();
    } else if (button.dataset.action === "delete-provider-profile-manage") {
      void fn(callbacks, "deleteProfile", async () => {})();
    } else if (button.dataset.action === "save-template-routing") {
      void fn(callbacks, "saveTemplateRouting", async () => {})();
    }
  }

  function bindList(callbacks = {}) {
    element(callbacks, "manageProviderProfileList")?.addEventListener("click", (event) => {
      const target = eventTarget(event);
      const button = target?.closest("[data-action='select-provider-profile']");
      if (button?.dataset.profileId) fn(callbacks, "selectProfile", () => {})(button.dataset.profileId);
    });
  }

  function bindEditor(callbacks = {}) {
    const editor = element(callbacks, "manageAiEditor");
    if (!editor) return null;
    editor.addEventListener("input", (event) => handleInput(event, callbacks));
    editor.addEventListener("change", (event) => handleChange(event, callbacks));
    editor.addEventListener("click", (event) => handleClick(event, callbacks));
    return editor;
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceManageAddProviderBtn")?.addEventListener("click", () => {
      fn(callbacks, "addProfile", () => {})();
    });
    bindList(callbacks);
    bindEditor(callbacks);
  }

  window.ConfigCenterProviderActions = {
    bind,
    bindEditor,
    bindList,
    handleChange,
    handleClick,
    handleInput,
  };
})();
