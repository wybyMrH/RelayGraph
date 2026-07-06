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

  function updateAgentField(callbacks, target) {
    const key = target.dataset.manageAgentField;
    if (!key) return;
    const value = key === "tools"
      ? fn(callbacks, "parseTags", () => [])(target.value || "")
      : target.value || "";
    fn(callbacks, "updateDraft", () => {})({ [key]: value });
  }

  function updateAgentNumber(callbacks, target) {
    const key = target.dataset.manageAgentNumber;
    if (!key) return;
    fn(callbacks, "updateDraft", () => {})({
      [key]: fn(callbacks, "positiveNumberOrBlank", () => "")(target.value),
    });
  }

  function handleInput(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.matches("[data-manage-agent-field]")) {
      updateAgentField(callbacks, target);
      return;
    }
    if (target.matches("[data-manage-agent-number]")) {
      updateAgentNumber(callbacks, target);
      return;
    }
    if (target.id === "manageAgentDebugInput") {
      fn(callbacks, "setDebugInput", () => {})(target.value || "");
    }
  }

  function handleChange(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.id === "manageAgentDebugExecuteLlm") {
      fn(callbacks, "setDebugExecuteLlm", () => {})(Boolean(target.checked));
      return;
    }
    if (target.matches("[data-manage-agent-checkbox]")) {
      const key = target.dataset.manageAgentCheckbox;
      if (key) fn(callbacks, "updateDraft", () => {})({ [key]: Boolean(target.checked) });
      return;
    }
    if (target.id === "manageAgentDebugTemplateSelect") {
      fn(callbacks, "setDebugTemplateId", () => {})(target.value || "");
      return;
    }
    if (target.matches("[data-manage-agent-field]")) {
      updateAgentField(callbacks, target);
      return;
    }
    if (target.matches("[data-manage-agent-number]")) {
      updateAgentNumber(callbacks, target);
    }
  }

  function handleClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "save-global-agent") {
      void fn(callbacks, "saveAgent", async () => {})();
    } else if (button.dataset.action === "delete-global-agent") {
      void fn(callbacks, "deleteAgent", async () => {})();
    } else if (button.dataset.action === "run-global-agent-debug") {
      void fn(callbacks, "runDebug", async () => {})();
    } else if (button.dataset.action === "copy-agent-debug-transcript") {
      void fn(callbacks, "copyDebugTranscript", async () => {})(button.dataset.debugScope || "manage")
        .then(() => fn(callbacks, "setMessage", () => {})("Agent 调试结果已复制。"))
        .catch((error) => fn(callbacks, "setMessage", () => {})(error.message || "复制 Agent 调试结果失败。", true));
    }
  }

  function bindList(callbacks = {}) {
    element(callbacks, "manageAgentList")?.addEventListener("click", (event) => {
      const target = eventTarget(event);
      const button = target?.closest("[data-action='select-global-agent']");
      if (button?.dataset.agentId) fn(callbacks, "selectAgent", () => {})(button.dataset.agentId);
    });
  }

  function bindEditor(callbacks = {}) {
    const editor = element(callbacks, "manageAgentEditor");
    if (!editor) return null;
    editor.addEventListener("input", (event) => handleInput(event, callbacks));
    editor.addEventListener("change", (event) => handleChange(event, callbacks));
    editor.addEventListener("click", (event) => handleClick(event, callbacks));
    return editor;
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceNewAgentBtn")?.addEventListener("click", () => {
      fn(callbacks, "newAgent", () => {})();
    });
    bindList(callbacks);
    bindEditor(callbacks);
  }

  window.ConfigCenterAgentActions = {
    bind,
    bindEditor,
    bindList,
    handleChange,
    handleClick,
    handleInput,
  };
})();
