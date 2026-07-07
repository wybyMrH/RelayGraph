(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function nodesFor(deps) {
    const nodes = typeof deps.nodes === "function" ? deps.nodes() : deps.nodes;
    return Array.isArray(nodes) ? nodes : [];
  }

  function selectedNodeIdFor(deps) {
    return typeof deps.selectedNodeId === "function" ? deps.selectedNodeId() : deps.selectedNodeId;
  }

  function fillSelectedMissingInputMapping(deps = {}, options = {}) {
    const nodes = nodesFor(deps);
    const selectedNodeId = selectedNodeIdFor(deps);
    const index = nodes.findIndex((item) => item.id === selectedNodeId);
    if (index < 0) return 0;
    const mergedMissingInputMapping = fn(deps, "mergedMissingInputMapping", () => ({ mapping: {}, added: 0, targetInputs: [] }));
    const setMessage = fn(deps, "setMessage", () => {});
    const result = mergedMissingInputMapping(nodes[index], index, nodes) || { mapping: {}, added: 0, targetInputs: [] };
    if (!result.targetInputs.length) {
      setMessage("当前节点没有声明输入，不需要补齐 input_mapping。");
      return 0;
    }
    if (!result.added) {
      setMessage("当前节点 input_mapping 已完整。");
      return 0;
    }
    fn(deps, "setSelectedInputMapping", () => {})(result.mapping, options);
    setMessage(`已为当前节点补齐 ${result.added} 条 input_mapping。`);
    return result.added;
  }

  function fillAllMissingInputMappings(deps = {}) {
    const nodes = nodesFor(deps).slice();
    const mergedMissingInputMapping = fn(deps, "mergedMissingInputMapping", () => ({ mapping: {}, added: 0, targetInputs: [] }));
    const setMessage = fn(deps, "setMessage", () => {});
    let addedTotal = 0;
    const nextNodes = nodes.map((node, index) => {
      const result = mergedMissingInputMapping(node, index, nodes) || { mapping: {}, added: 0 };
      if (!result.added) return node;
      addedTotal += result.added;
      return { ...node, input_mapping: result.mapping };
    });
    if (!addedTotal) {
      setMessage("全链 input_mapping 已完整，没有新的缺口需要补齐。");
      return;
    }
    fn(deps, "updateDraft", () => {})((draft) => ({ ...draft, nodes: nextNodes }));
    setMessage(`已为全链补齐 ${addedTotal} 条 input_mapping，未覆盖已有手工映射。`);
  }

  function refreshEditorHealth(deps = {}, editor, options = {}) {
    const mappingApi = typeof deps.mappingApi === "function" ? deps.mappingApi() : deps.mappingApi;
    const selectedNode = fn(deps, "selectedNode", () => null)();
    const mappingNodes = fn(deps, "mappingNodes", () => [])();
    const nodeIndex = fn(deps, "nodeIndex", () => 0)(selectedNode);
    const mappingDeps = fn(deps, "mappingDeps", () => ({}))();
    mappingApi?.refreshEditorHealth?.(editor, {
      ...options,
      node: selectedNode,
      nodes: mappingNodes,
      index: nodeIndex,
      ...mappingDeps,
    });
  }

  window.WorkflowTemplateMappingActions = {
    fillAllMissingInputMappings,
    fillSelectedMissingInputMapping,
    refreshEditorHealth,
  };
})();
