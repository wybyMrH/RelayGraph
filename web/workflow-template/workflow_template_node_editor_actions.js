(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.matches === "function") return target;
    return target?.parentElement && typeof target.parentElement.matches === "function" ? target.parentElement : null;
  }

  function updateNode(callbacks, updater) {
    fn(callbacks, "updateNode", () => {})(updater);
  }

  function inputMappingEntriesFromEditor(callbacks, editor) {
    const entries = fn(callbacks, "inputMappingEntriesFromEditor", () => [])(editor);
    return Array.isArray(entries) ? entries : [];
  }

  function inputMappingEntries(callbacks, mapping = {}) {
    const entries = fn(callbacks, "inputMappingEntries", () => [])(mapping);
    return Array.isArray(entries) ? entries : [];
  }

  function inputMappingFromEntries(callbacks, entries = []) {
    return fn(callbacks, "inputMappingFromEntries", () => ({}))(entries);
  }

  function syncStructuredMapping(callbacks, editor) {
    const entries = inputMappingEntriesFromEditor(callbacks, editor);
    const mapping = inputMappingFromEntries(callbacks, entries);
    fn(callbacks, "syncMappingAdvancedText", () => {})(editor, mapping);
    fn(callbacks, "setSelectedInputMapping", () => {})(mapping, { render: false });
    fn(callbacks, "refreshMappingEditorHealth", () => {})(editor);
    return entries;
  }

  function handleField(event, callbacks = {}) {
    const target = eventTarget(event);
    if (!target) return;
    if (target.matches("[data-manage-node-field]")) {
      const key = target.dataset.manageNodeField;
      updateNode(callbacks, (node) => ({ ...node, [key]: target.value }));
      return;
    }
    if (target.matches("[data-manage-handler-field]")) {
      const key = target.dataset.manageHandlerField;
      if (key === "agent_id") {
        const agent = fn(callbacks, "globalAgentById", () => null)(target.value || "");
        updateNode(callbacks, (node) => ({
          ...node,
          handler: { ...(node.handler || {}), agent_id: target.value || "", name: agent?.name || node.handler?.name || "" },
        }));
        return;
      }
      updateNode(callbacks, (node) => ({
        ...node,
        handler: { ...(node.handler || {}), [key]: target.value || "" },
      }));
      return;
    }
    if (target.matches("[data-manage-input-mapping]")) {
      const mapping = fn(callbacks, "inputMappingFromText", () => ({}))(target.value || "");
      updateNode(callbacks, (node) => {
        const next = { ...node };
        if (Object.keys(mapping).length) next.input_mapping = mapping;
        else delete next.input_mapping;
        return next;
      });
      return;
    }
    if (target.matches("[data-manage-input-mapping-name], [data-manage-input-mapping-source]")) {
      syncStructuredMapping(callbacks, target.closest(".workflow-template-mapping-editor"));
      return;
    }
    if (target.matches("[data-manage-input-mapping-source-select]")) {
      const row = target.closest(".workflow-template-mapping-row");
      const sourceInput = row?.querySelector("[data-manage-input-mapping-source]");
      if (sourceInput) sourceInput.value = target.value || "";
      syncStructuredMapping(callbacks, target.closest(".workflow-template-mapping-editor"));
      return;
    }
    if (target.matches("[data-config-key]")) {
      const key = target.dataset.configKey;
      updateNode(callbacks, (node) => ({
        ...node,
        config: { ...(node.config || {}), [key]: target.value || "" },
      }));
    }
  }

  function handleClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    if (!button) return;
    const node = fn(callbacks, "selectedNode", () => null)();
    const editor = button.closest(".workflow-template-mapping-editor");
    const entries = editor
      ? inputMappingEntriesFromEditor(callbacks, editor)
      : inputMappingEntries(callbacks, node?.input_mapping || {});
    if (button.dataset.action === "fill-template-input-mapping") {
      fn(callbacks, "fillSelectedMissingMapping", () => false)({ render: true });
      return;
    }
    if (button.dataset.action === "add-template-input-mapping") {
      if (fn(callbacks, "fillSelectedMissingMapping", () => false)({ render: true })) {
        return;
      }
      entries.push({
        name: `input_${entries.length + 1}`,
        source: fn(callbacks, "nodeIndex", () => 0)(node) === 0 ? "$input" : "$prev.output",
      });
      fn(callbacks, "setSelectedInputMapping", () => {})(
        inputMappingFromEntries(callbacks, entries),
        { render: true },
      );
      return;
    }
    if (button.dataset.action === "remove-template-input-mapping") {
      const removeIndex = Number(button.dataset.index || -1);
      const nextEntries = entries.filter((_, index) => index !== removeIndex);
      fn(callbacks, "setSelectedInputMapping", () => {})(
        inputMappingFromEntries(callbacks, nextEntries),
        { render: true },
      );
    }
  }

  function bind(root, callbacks = {}) {
    if (!root || typeof root.addEventListener !== "function") return null;
    root.addEventListener("input", (event) => handleField(event, callbacks));
    root.addEventListener("change", (event) => handleField(event, callbacks));
    root.addEventListener("click", (event) => handleClick(event, callbacks));
    return root;
  }

  window.WorkflowTemplateNodeEditorActions = {
    bind,
    handleClick,
    handleField,
  };
})();
