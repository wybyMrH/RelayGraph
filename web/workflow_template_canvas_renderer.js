(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function createElement(deps, tagName) {
    const fallback = (tag) => (typeof document !== "undefined" ? document.createElement(tag) : null);
    return fn(deps, "createElement", fallback)(tagName);
  }

  function draftFor(deps = {}) {
    const workflowTemplateDraft = fn(deps, "workflowTemplateDraft", () => null)();
    const selectedWorkflowTemplate = fn(deps, "selectedWorkflowTemplate", () => null)();
    const defaultWorkflowTemplateDraft = fn(deps, "defaultWorkflowTemplateDraft", () => ({}));
    const normalizeWorkflowTemplateDraft = fn(deps, "normalizeWorkflowTemplateDraft", (value) => value || {});
    return normalizeWorkflowTemplateDraft(workflowTemplateDraft || selectedWorkflowTemplate || defaultWorkflowTemplateDraft("repo"));
  }

  function canvasModel(deps = {}, nodes = []) {
    const selectedTemplateNodeId = fn(deps, "selectedTemplateNodeId", () => "")();
    const selectedIndex = Math.max(0, nodes.findIndex((node) => node.id === selectedTemplateNodeId));
    const selectedNode = nodes[selectedIndex] || nodes[0] || {};
    const nodeIoState = fn(deps, "nodeIoState", () => ({}));
    const canvasSearchState = fn(deps, "canvasSearchState", () => ({}));
    const ioStates = nodes.map((node, index) => nodeIoState(node, index, nodes));
    const search = canvasSearchState(nodes, ioStates);
    const mappedCount = ioStates.filter((item) => item.status === "ready").length;
    return { ioStates, mappedCount, search, selectedIndex, selectedNode };
  }

  function flowTrackMarkup(deps = {}, nodes = [], ioStates = [], search = {}) {
    const nodeFlowMarkup = fn(deps, "nodeFlowMarkup", () => "");
    const connectorMarkup = fn(deps, "connectorMarkup", () => "");
    const parts = [];
    nodes.forEach((node, index) => {
      parts.push(nodeFlowMarkup(node, index, nodes, ioStates[index], { searchQuery: search.query }));
      if (index < nodes.length - 1) parts.push(connectorMarkup(node, nodes[index + 1], index + 1, nodes, ioStates[index + 1]));
    });
    return parts.join("");
  }

  function renderCanvas(deps = {}) {
    const root = element(deps, "workflowTemplateCanvas");
    if (!root) return;
    const draft = draftFor(deps);
    const nodes = Array.isArray(draft.nodes) ? draft.nodes : [];
    if (!nodes.length) {
      root.innerHTML = '<div class="empty">模板里还没有节点。</div>';
      return;
    }
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const workspaceNodeLabel = fn(deps, "workspaceNodeLabel", (kind) => kind);
    const { ioStates, mappedCount, search, selectedIndex, selectedNode } = canvasModel(deps, nodes);
    const trackMarkup = flowTrackMarkup(deps, nodes, ioStates, search);
    const edgeMarkup = fn(deps, "edgeInspectorMarkup", () => "")(nodes, selectedIndex);
    const phaseMap = fn(deps, "phaseMapMarkup", () => "")(nodes, selectedNode.id || "", ioStates, search);
    const topologyPreview = fn(deps, "topologyPreviewMarkup", () => "")(nodes, ioStates, search);
    root.innerHTML = `
    <div class="workflow-template-canvas-head">
      <div>
        <strong>${escapeHtml(`${nodes.length} 节点 · ${mappedCount}/${nodes.length} I/O 闭合`)}</strong>
        <span title="${escapeHtml(selectedNode.title || workspaceNodeLabel(selectedNode.kind))}">${escapeHtml(`当前：${selectedNode.title || workspaceNodeLabel(selectedNode.kind)}`)}</span>
      </div>
      <div class="workflow-template-canvas-actions">
        <button class="secondary mini" type="button" data-action="move-template-node" data-node-id="${escapeHtml(selectedNode.id || "")}" data-direction="up" title="上移当前节点" ${selectedIndex > 0 ? "" : "disabled"}>上移</button>
        <button class="secondary mini" type="button" data-action="move-template-node" data-node-id="${escapeHtml(selectedNode.id || "")}" data-direction="down" title="下移当前节点" ${selectedIndex < nodes.length - 1 ? "" : "disabled"}>下移</button>
        <button class="secondary mini" type="button" data-action="insert-template-node-after" data-node-id="${escapeHtml(selectedNode.id || "")}" title="在当前节点后插入左上角选择的节点类型">插入</button>
        <button class="secondary mini" type="button" data-action="fill-template-all-missing-mapping" title="为全链声明输入补齐缺失 input_mapping，不覆盖已有手工映射">补齐映射</button>
      </div>
    </div>
    ${fn(deps, "canvasSearchToolsMarkup", () => "")(search)}
    ${topologyPreview}
    ${phaseMap}
    <div class="workflow-template-flow-viewport" aria-label="模板顺序链路画布">
      <div class="workflow-template-flow-track">
        ${trackMarkup}
      </div>
    </div>
    ${edgeMarkup}
  `;
  }

  function refreshFlowSummary(deps = {}) {
    const root = element(deps, "workflowTemplateCanvas");
    if (!root) return;
    const draft = fn(deps, "workflowTemplateDraft", () => ({}))() || {};
    const nodes = Array.isArray(draft.nodes) ? draft.nodes : [];
    if (!nodes.length) return;
    const workspaceNodeLabel = fn(deps, "workspaceNodeLabel", (kind) => kind);
    const { ioStates, mappedCount, search, selectedNode } = canvasModel(deps, nodes);
    const headStrong = root.querySelector(".workflow-template-canvas-head strong");
    if (headStrong) headStrong.textContent = `${nodes.length} 节点 · ${mappedCount}/${nodes.length} I/O 闭合`;
    const headCurrent = root.querySelector(".workflow-template-canvas-head span");
    if (headCurrent) {
      const label = selectedNode.title || workspaceNodeLabel(selectedNode.kind);
      headCurrent.textContent = `当前：${label}`;
      headCurrent.title = label;
    }
    const phaseMap = root.querySelector(".workflow-template-phase-map");
    if (phaseMap) {
      const replacement = createElement(deps, "div");
      replacement.innerHTML = fn(deps, "phaseMapMarkup", () => "")(nodes, selectedNode.id || "", ioStates, search).trim();
      phaseMap.replaceWith(replacement.firstElementChild);
    }
    const topologyPreview = root.querySelector(".workflow-template-layout-preview");
    if (topologyPreview) {
      const replacement = createElement(deps, "div");
      replacement.innerHTML = fn(deps, "topologyPreviewMarkup", () => "")(nodes, ioStates, search).trim();
      topologyPreview.replaceWith(replacement.firstElementChild);
    }
    const track = root.querySelector(".workflow-template-flow-track");
    if (track) track.innerHTML = flowTrackMarkup(deps, nodes, ioStates, search);
    fn(deps, "refreshSearchDecorations", () => {})();
  }

  window.WorkflowTemplateCanvasRenderer = {
    renderCanvas,
    refreshFlowSummary,
  };
})();
