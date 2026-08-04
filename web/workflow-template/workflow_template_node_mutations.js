(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function draftNodes(draft = {}) {
    return Array.isArray(draft?.nodes) ? draft.nodes : [];
  }

  function nodeFormData(draft = {}, deps = {}) {
    const source = draft?.source && typeof draft.source === "object" ? draft.source : {};
    const env = draft?.env && typeof draft.env === "object" ? draft.env : {};
    const sourceType = fn(deps, "workspaceChainSourceType", (value) =>
      String(value || "repo") === "mixed" ? "idea" : String(value || "repo"),
    )(source.type || "repo");
    return {
      source_type: sourceType,
      repo_url: source.repo_url || "",
      repo_ref: source.repo_ref || "",
      paper_url: source.paper_url || "",
      idea_text: source.idea_text || draft?.brief || "",
      workspace_dir: draft?.workspace_dir || "",
      env_name: env.name || "",
      env_manager: env.manager || "",
      python_version: env.python || "",
    };
  }

  function selectedNode(nodes = [], selectedNodeId = "") {
    const list = Array.isArray(nodes) ? nodes : [];
    const selectedId = String(selectedNodeId || "").trim();
    return list.find((item) => item?.id === selectedId) || list[0] || null;
  }

  function normalizeNode(node = {}, index = 0, draft = {}, deps = {}) {
    return fn(deps, "normalizeWorkspaceDraftNode", (item) => item)(
      node,
      index,
      nodeFormData(draft, deps),
    );
  }

  function updateSelectedNode(options = {}, deps = {}) {
    const draft = options.draft && typeof options.draft === "object" ? options.draft : {};
    const nodes = draftNodes(draft).slice();
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const index = nodes.findIndex((item) => item?.id === selectedNodeId);
    if (index < 0) return { ok: false, nodes, selectedNodeId };
    const current = nodes[index];
    const deepClone = fn(deps, "deepClone", (value) => ({ ...(value || {}) }));
    const updater = options.updater;
    const next = typeof updater === "function"
      ? updater(deepClone(current, current))
      : { ...current, ...(updater && typeof updater === "object" ? updater : {}) };
    nodes.splice(index, 1, normalizeNode(next, index, draft, deps));
    return { ok: true, nodes, selectedNodeId };
  }

  function setSelectedInputMapping(options = {}, deps = {}) {
    const draft = options.draft && typeof options.draft === "object" ? options.draft : {};
    const nodes = draftNodes(draft).slice();
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const index = nodes.findIndex((item) => item?.id === selectedNodeId);
    if (index < 0) return { ok: false, nodes, selectedNodeId };
    const deepClone = fn(deps, "deepClone", (value) => ({ ...(value || {}) }));
    const current = deepClone(nodes[index], nodes[index]);
    const entries = fn(deps, "workspaceInputMappingEntries", () => [])(options.mapping || {});
    const cleaned = fn(deps, "workspaceInputMappingFromEntries", () => ({}))(entries);
    if (Object.keys(cleaned).length) current.input_mapping = cleaned;
    else delete current.input_mapping;
    nodes.splice(index, 1, normalizeNode(current, index, draft, deps));
    return { ok: true, nodes, selectedNodeId };
  }

  function insertNode(options = {}, deps = {}) {
    const draft = options.draft && typeof options.draft === "object" ? options.draft : {};
    const nodes = draftNodes(draft).slice();
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const currentIndex = nodes.findIndex((node) => node?.id === selectedNodeId);
    const insertIndex = currentIndex >= 0 ? currentIndex + 1 : nodes.length;
    const node = fn(deps, "createWorkspaceNode", (kind, overrides, index) => ({
      id: `node-${index + 1}`,
      kind,
      ...(overrides || {}),
    }))(
      String(options.kind || "custom.step"),
      {},
      insertIndex,
      nodeFormData(draft, deps),
    );
    nodes.splice(insertIndex, 0, node);
    return { ok: true, nodes, selectedNodeId: node.id, node };
  }

  function moveNode(options = {}) {
    const nodes = (Array.isArray(options.nodes) ? options.nodes : []).slice();
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const index = nodes.findIndex((item) => item?.id === selectedNodeId);
    if (index < 0) return { ok: false, nodes, selectedNodeId };
    const targetIndex = options.direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= nodes.length) {
      return { ok: false, nodes, selectedNodeId };
    }
    const [node] = nodes.splice(index, 1);
    nodes.splice(targetIndex, 0, node);
    return { ok: true, nodes, selectedNodeId: node?.id || selectedNodeId, node };
  }

  function removeNode(options = {}) {
    const nodes = (Array.isArray(options.nodes) ? options.nodes : []).slice();
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    if (nodes.length <= 1) {
      return { ok: false, reason: "minimum_nodes", nodes, selectedNodeId };
    }
    const index = nodes.findIndex((item) => item?.id === selectedNodeId);
    if (index < 0) return { ok: false, nodes, selectedNodeId };
    nodes.splice(index, 1);
    const nextSelectedNodeId = nodes[Math.max(0, index - 1)]?.id || nodes[0]?.id || "";
    return { ok: true, nodes, selectedNodeId: nextSelectedNodeId };
  }

  function rebuildNodes(options = {}, deps = {}) {
    const draft = options.draft && typeof options.draft === "object" ? options.draft : {};
    const nodes = fn(deps, "buildWorkspaceStarterNodes", () => [])(nodeFormData(draft, deps));
    return { ok: true, nodes, selectedNodeId: nodes[0]?.id || "" };
  }

  window.WorkflowTemplateNodeMutations = {
    draftNodes,
    insertNode,
    moveNode,
    nodeFormData,
    rebuildNodes,
    removeNode,
    selectedNode,
    setSelectedInputMapping,
    updateSelectedNode,
  };
})();
