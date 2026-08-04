(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function selectedNodeKind(callbacks) {
    return String(fn(callbacks, "selectedNodeKind", () => "custom.step")() || "custom.step");
  }

  function mappingFromEntries(callbacks, entries) {
    return fn(callbacks, "mappingFromEntries", () => ({}))(entries);
  }

  function edgeEntries(callbacks, editor) {
    return fn(callbacks, "edgeEntriesFromEditor", () => [])(editor);
  }

  function defaultEdgeEntries(callbacks, mode) {
    const entries = fn(callbacks, "defaultEdgeEntries", () => [])(mode);
    return Array.isArray(entries) ? entries : [];
  }

  function setSelectedMapping(callbacks, mapping, options) {
    fn(callbacks, "setSelectedInputMapping", () => {})(mapping, options);
  }

  function updateEdgeMapping(callbacks, editor, options = {}) {
    const { refreshHealth, ...mappingOptions } = options;
    setSelectedMapping(callbacks, mappingFromEntries(callbacks, edgeEntries(callbacks, editor)), mappingOptions);
    if (refreshHealth) {
      fn(callbacks, "refreshMappingEditorHealth", () => {})(editor, { edge: true });
    }
  }

  function handleClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    const action = button.dataset.action || "";
    const nodeId = String(button.dataset.nodeId || "").trim();
    if (nodeId) fn(callbacks, "setSelectedNodeId", () => {})(nodeId);
    if (action === "select-template-node" || action === "select-template-edge") {
      const revealEditor = action === "select-template-node" && Boolean(button.closest(".workflow-template-phase-map"));
      fn(callbacks, "renderWorkbench", () => {})();
      if (nodeId) fn(callbacks, "revealSelection", () => {})(nodeId, { editor: revealEditor });
      return;
    }
    if (action === "move-template-node") {
      fn(callbacks, "moveNode", () => {})(button.dataset.direction || "down");
      return;
    }
    if (action === "insert-template-node-after") {
      fn(callbacks, "insertNode", () => {})(selectedNodeKind(callbacks));
      return;
    }
    if (action === "fill-template-all-missing-mapping") {
      fn(callbacks, "fillAllMissingMappings", () => {})();
      return;
    }
    if (action === "template-search-prev") {
      fn(callbacks, "selectSearchMatch", () => {})(-1);
      return;
    }
    if (action === "template-search-next") {
      fn(callbacks, "selectSearchMatch", () => {})(1);
      return;
    }
    if (action === "template-search-clear") {
      fn(callbacks, "setNodeSearch", () => {})("");
      return;
    }
    if (action === "delete-template-node") {
      fn(callbacks, "removeNode", () => {})();
      return;
    }
    if (action === "map-template-edge-previous") {
      setSelectedMapping(callbacks, mappingFromEntries(callbacks, defaultEdgeEntries(callbacks, "previous")), { render: "canvas" });
      return;
    }
    if (action === "map-template-edge-context") {
      setSelectedMapping(callbacks, mappingFromEntries(callbacks, defaultEdgeEntries(callbacks, "context")), { render: "canvas" });
      return;
    }
    if (action === "fill-template-edge-mapping") {
      fn(callbacks, "fillSelectedMissingMapping", () => {})({ render: "canvas" });
      return;
    }
    if (action === "add-template-edge-mapping") {
      const editor = button.closest(".workflow-template-edge-inspector");
      const entries = edgeEntries(callbacks, editor);
      const defaults = defaultEdgeEntries(callbacks, "previous");
      entries.push(
        defaults.find((item) => !entries.some((entry) => entry.name === item.name))
        || { name: `input_${entries.length + 1}`, source: defaults[0]?.source || "$prev.output" },
      );
      setSelectedMapping(callbacks, mappingFromEntries(callbacks, entries), { render: "canvas" });
      return;
    }
    if (action === "remove-template-edge-mapping") {
      const editor = button.closest(".workflow-template-edge-inspector");
      const removeIndex = Number(button.dataset.index || -1);
      const entries = edgeEntries(callbacks, editor).filter((_, index) => index !== removeIndex);
      setSelectedMapping(callbacks, mappingFromEntries(callbacks, entries), { render: "canvas" });
      return;
    }
    if (action === "clear-template-edge-mapping") {
      setSelectedMapping(callbacks, {}, { render: "canvas" });
    }
  }

  function handleInput(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target || typeof target.matches !== "function") return;
    if (target.matches("[data-template-node-search]")) {
      fn(callbacks, "setNodeSearch", () => {})(target.value || "");
      return;
    }
    if (!target.matches("[data-edge-input-mapping-name], [data-edge-input-mapping-source]")) return;
    const editor = target.closest(".workflow-template-edge-inspector");
    updateEdgeMapping(callbacks, editor, { render: false, renderParts: true, refreshHealth: true });
  }

  function handleKeydown(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target || typeof target.matches !== "function") return;
    if (!target.matches("[data-template-node-search]") || event.key !== "Enter") return;
    event.preventDefault();
    fn(callbacks, "selectSearchMatch", () => {})(event.shiftKey ? -1 : 1);
  }

  function handleChange(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target || typeof target.matches !== "function") return;
    if (!target.matches("[data-edge-input-mapping-source-select]")) return;
    const row = target.closest(".workflow-template-mapping-row");
    const sourceInput = row?.querySelector("[data-edge-input-mapping-source]");
    if (sourceInput) sourceInput.value = target.value || "";
    const editor = target.closest(".workflow-template-edge-inspector");
    updateEdgeMapping(callbacks, editor, { render: false, renderParts: true, refreshHealth: true });
  }

  function bind(root, callbacks = {}) {
    if (!root || typeof root.addEventListener !== "function") return null;
    root.addEventListener("click", (event) => handleClick(event, callbacks));
    root.addEventListener("input", (event) => handleInput(event, callbacks));
    root.addEventListener("keydown", (event) => handleKeydown(event, callbacks));
    root.addEventListener("change", (event) => handleChange(event, callbacks));
    return root;
  }

  window.WorkflowTemplateCanvasActions = {
    bind,
    handleChange,
    handleClick,
    handleInput,
    handleKeydown,
  };
})();
