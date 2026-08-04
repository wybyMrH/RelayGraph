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

  function updateToolField(callbacks, target) {
    const key = target.dataset.manageToolField;
    if (!key) return;
    fn(callbacks, "updateDraft", () => {})({ [key]: target.value || "" });
  }

  function handleInput(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.matches("[data-manage-tool-field]")) {
      updateToolField(callbacks, target);
      return;
    }
    if (target.id === "manageToolTestArguments") {
      fn(callbacks, "setTestArguments", () => {})(target.value || "");
    }
  }

  function handleChange(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.id === "manageToolTestWorkspaceSelect") {
      fn(callbacks, "setTestWorkspaceId", () => {})(target.value || "");
      return;
    }
    if (target.id === "manageToolSearchProfileSelect") {
      fn(callbacks, "setSearchProfileId", () => {})(target.value || "");
      return;
    }
    if (target.matches("[data-manage-tool-checkbox]")) {
      const key = target.dataset.manageToolCheckbox;
      if (key) fn(callbacks, "updateDraft", () => {})({ [key]: Boolean(target.checked) });
      return;
    }
    if (target.matches("[data-manage-tool-field]")) {
      updateToolField(callbacks, target);
    }
  }

  function handleClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "save-global-tool") {
      void fn(callbacks, "saveTool", async () => {})();
    } else if (button.dataset.action === "delete-global-tool") {
      void fn(callbacks, "deleteTool", async () => {})();
    } else if (button.dataset.action === "reset-global-tool-test") {
      fn(callbacks, "resetTest", () => {})();
    } else if (button.dataset.action === "run-global-tool-test") {
      void fn(callbacks, "runTest", async () => {})();
    } else if (button.dataset.action === "copy-tool-test-result") {
      void fn(callbacks, "copyTestResult", async () => {})()
        .then(() => fn(callbacks, "setMessage", () => {})("工具测试结果已复制。"))
        .catch((error) => fn(callbacks, "setMessage", () => {})(error.message || "复制工具测试结果失败。", true));
    }
  }

  function bindList(callbacks = {}) {
    element(callbacks, "manageToolList")?.addEventListener("click", (event) => {
      const target = eventTarget(event);
      const button = target?.closest("[data-action='select-global-tool']");
      if (button?.dataset.toolId) fn(callbacks, "selectTool", () => {})(button.dataset.toolId);
    });
  }

  function bindEditor(callbacks = {}) {
    const editor = element(callbacks, "manageToolEditor");
    if (!editor) return null;
    editor.addEventListener("input", (event) => handleInput(event, callbacks));
    editor.addEventListener("change", (event) => handleChange(event, callbacks));
    editor.addEventListener("click", (event) => handleClick(event, callbacks));
    return editor;
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceNewToolBtn")?.addEventListener("click", () => {
      fn(callbacks, "newTool", () => {})();
    });
    bindList(callbacks);
    bindEditor(callbacks);
  }

  window.ConfigCenterToolActions = {
    bind,
    bindEditor,
    bindList,
    handleChange,
    handleClick,
    handleInput,
  };
})();
