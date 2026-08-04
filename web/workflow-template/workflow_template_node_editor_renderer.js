(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function editorApiFor(deps = {}) {
    return typeof deps.editorApi === "function" ? deps.editorApi() : deps.editorApi;
  }

  function renderNodeEditor(deps = {}) {
    const box = element(deps, "workflowTemplateNodeEditor");
    if (!box) return;
    const node = fn(deps, "selectedNode", () => null)();
    if (!node) {
      box.innerHTML = '<div class="empty">选择一个节点后，在这里编辑配置。</div>';
      return;
    }
    const nodeIndex = fn(deps, "nodeIndex", () => 0)(node);
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    box.innerHTML = editorApiFor(deps)?.editorMarkup?.({
      agentDefinitions: fn(deps, "agentDefinitions", () => [])(),
      escapeHtml: deps.escapeHtml,
      inputMappingEditorMarkup: deps.inputMappingEditorMarkup,
      node,
      nodeIndex,
      nodeLabel: deps.nodeLabel,
      nodeMeta: deps.nodeMeta,
      outputPlaceholder: nodeIoContract(node.kind, 0).output || "step_output",
      renderNodeField: deps.renderNodeField,
      statusLabel: deps.statusLabel,
    }) || '<div class="empty">模板节点编辑器暂不可用。</div>';
  }

  window.WorkflowTemplateNodeEditorRenderer = {
    renderNodeEditor,
  };
})();
