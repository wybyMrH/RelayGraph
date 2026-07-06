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

  function handleAgentClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "remove-workspace-agent" && button.dataset.agentId) {
      fn(callbacks, "removeAgent", () => {})(button.dataset.agentId);
      return;
    }
    if (button.dataset.action === "prefill-workspace-agent-debug") {
      fn(callbacks, "prefillAgentDebug", () => {})();
      return;
    }
    if (button.dataset.action === "run-workspace-agent-debug" && button.dataset.agentId) {
      void fn(callbacks, "runAgentDebug", async () => {})(button.dataset.agentId);
      return;
    }
    if (button.dataset.action === "copy-agent-debug-transcript") {
      void fn(callbacks, "copyAgentDebug", async () => {})(button.dataset.debugScope || "workspace");
    }
  }

  function handleAgentField(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.matches("[data-agent-field]")) {
      fn(callbacks, "updateAgentField", () => {})(target.dataset.agentField, target.value);
      return;
    }
    if (target.matches("[data-agent-debug-input]")) {
      fn(callbacks, "setAgentDebugInput", () => {})(target.value);
      return;
    }
    if (target.matches("[data-agent-debug-execute-llm]")) {
      fn(callbacks, "setAgentDebugExecuteLlm", () => {})(Boolean(target.checked));
      return;
    }
    if (target.matches("[data-agent-checkbox]")) {
      fn(callbacks, "updateAgentCheckbox", () => {})(target.dataset.agentCheckbox, Boolean(target.checked));
    }
  }

  function handleToolClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "add-workspace-tool") {
      fn(callbacks, "addTool", () => {})();
      return;
    }
    if (button.dataset.action === "remove-workspace-tool" && button.dataset.toolId) {
      fn(callbacks, "removeTool", () => {})(button.dataset.toolId);
    }
  }

  function handleToolField(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.matches("[data-tool-field]")) {
      fn(callbacks, "updateToolField", () => {})(target.dataset.toolField, target.value);
      return;
    }
    if (target.matches("[data-tool-checkbox]")) {
      fn(callbacks, "updateToolCheckbox", () => {})(target.dataset.toolCheckbox, Boolean(target.checked));
    }
  }

  function bindAgentList(callbacks = {}) {
    element(callbacks, "workspaceAgentList")?.addEventListener("click", (event) => {
      const target = eventTarget(event);
      const button = target?.closest("[data-action='select-workspace-agent']");
      if (button?.dataset.agentId) fn(callbacks, "selectAgent", () => {})(button.dataset.agentId);
    });
  }

  function bindAgentPresets(callbacks = {}) {
    element(callbacks, "workspaceAgentPresetList")?.addEventListener("click", (event) => {
      const target = eventTarget(event);
      const button = target?.closest("[data-action='apply-agent-template']");
      if (button?.dataset.role) fn(callbacks, "applyAgentTemplate", () => {})(button.dataset.role);
    });
  }

  function bindAgentEditor(callbacks = {}) {
    const editor = element(callbacks, "workspaceAgentEditor");
    if (!editor) return null;
    editor.addEventListener("click", (event) => handleAgentClick(event, callbacks));
    editor.addEventListener("input", (event) => handleAgentField(event, callbacks));
    editor.addEventListener("change", (event) => handleAgentField(event, callbacks));
    return editor;
  }

  function bindToolList(callbacks = {}) {
    element(callbacks, "workspaceToolList")?.addEventListener("click", (event) => {
      const target = eventTarget(event);
      const button = target?.closest("[data-action='select-workspace-tool']");
      if (button?.dataset.toolId) fn(callbacks, "selectTool", () => {})(button.dataset.toolId);
    });
  }

  function bindToolEditor(callbacks = {}) {
    const editor = element(callbacks, "workspaceToolEditor");
    if (!editor) return null;
    editor.addEventListener("click", (event) => handleToolClick(event, callbacks));
    editor.addEventListener("input", (event) => handleToolField(event, callbacks));
    editor.addEventListener("change", (event) => handleToolField(event, callbacks));
    return editor;
  }

  function bind(callbacks = {}) {
    bindAgentList(callbacks);
    bindAgentPresets(callbacks);
    bindAgentEditor(callbacks);
    bindToolList(callbacks);
    bindToolEditor(callbacks);
  }

  window.WorkspaceAgentToolActions = {
    bind,
    bindAgentEditor,
    bindAgentList,
    bindAgentPresets,
    bindToolEditor,
    bindToolList,
    handleAgentClick,
    handleAgentField,
    handleToolClick,
    handleToolField,
  };
})();
