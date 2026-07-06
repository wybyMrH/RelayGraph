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

  function handleNodeListClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    const nodeId = button.dataset.nodeId || "";
    if (button.dataset.action === "select-workspace-node") {
      fn(callbacks, "selectNode", () => {})(nodeId);
    } else if (button.dataset.action === "move-workspace-node") {
      fn(callbacks, "moveNode", () => {})(nodeId, button.dataset.direction || "down");
    } else if (button.dataset.action === "remove-workspace-node") {
      fn(callbacks, "removeNode", () => {})(nodeId);
    } else if (button.dataset.action === "run-workspace-node") {
      void fn(callbacks, "runNode", async () => {})(nodeId);
    } else if (button.dataset.action === "fill-job-from-node") {
      fn(callbacks, "fillJobFromNode", () => {})(nodeId);
    }
  }

  function handleNodeEditorClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "sync-form-from-node") {
      fn(callbacks, "syncFormFromSelectedNode", () => {})();
    } else if (button.dataset.action === "run-workspace-node") {
      void fn(callbacks, "runNode", async () => {})(button.dataset.nodeId || "");
    } else if (button.dataset.action === "fill-job-from-node") {
      fn(callbacks, "fillJobFromNode", () => {})(button.dataset.nodeId || "");
    }
  }

  function handleNodeEditorField(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.matches("[data-node-field]")) {
      fn(callbacks, "updateNodeField", () => {})(target.dataset.nodeField, target.value);
      return;
    }
    if (target.matches("[data-handler-field]")) {
      fn(callbacks, "updateHandlerField", () => {})(target.dataset.handlerField, target.value);
      return;
    }
    if (target.matches("[data-node-input-mapping]")) {
      fn(callbacks, "updateInputMapping", () => {})(target.value || "");
      return;
    }
    if (target.matches("[data-config-key]")) {
      fn(callbacks, "updateConfigField", () => {})(target.dataset.configKey, target.value);
    }
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceAddNodeBtn")?.addEventListener("click", () => {
      fn(callbacks, "addNode", () => {})();
    });
    element(callbacks, "workspaceRebuildGraphBtn")?.addEventListener("click", () => {
      fn(callbacks, "rebuildGraph", () => {})();
    });
    element(callbacks, "workspaceNodeList")?.addEventListener("click", (event) => handleNodeListClick(event, callbacks));
    const editor = element(callbacks, "workspaceNodeEditor");
    if (editor) {
      editor.addEventListener("click", (event) => handleNodeEditorClick(event, callbacks));
      editor.addEventListener("input", (event) => handleNodeEditorField(event, callbacks));
      editor.addEventListener("change", (event) => handleNodeEditorField(event, callbacks));
    }
  }

  window.WorkspaceNodeActions = {
    bind,
    handleNodeEditorClick,
    handleNodeEditorField,
    handleNodeListClick,
  };
})();
