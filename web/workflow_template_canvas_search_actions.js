(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function nodesFor(deps = {}) {
    const nodes = typeof deps.nodes === "function" ? deps.nodes() : deps.nodes;
    return Array.isArray(nodes) ? nodes : [];
  }

  function searchApiFor(deps = {}) {
    return typeof deps.searchApi === "function" ? deps.searchApi() : deps.searchApi;
  }

  function setNodeSearch(deps = {}, query = "", options = {}) {
    fn(deps, "setSearchQuery", () => {})(String(query || ""));
    if (options.render === true) fn(deps, "renderCanvas", () => {})();
    else fn(deps, "refreshFlowSummary", () => {})();
  }

  function fallbackNextMatchNodeId(search = {}, direction = 1) {
    const matches = Array.isArray(search.matches) ? search.matches : [];
    const currentIndex = search.selectedMatchIndex >= 0 ? search.selectedMatchIndex : (direction > 0 ? -1 : 0);
    const nextIndex = (currentIndex + direction + matches.length) % matches.length;
    return matches[nextIndex]?.node?.id || "";
  }

  function selectSearchMatch(deps = {}, direction = 1) {
    const nodes = nodesFor(deps);
    if (!nodes.length) return;
    const nodeIoState = fn(deps, "nodeIoState", () => ({}));
    const ioStates = nodes.map((node, index) => nodeIoState(node, index, nodes));
    const search = fn(deps, "searchState", () => ({}))(nodes, ioStates);
    if (!search.query || !search.matches.length) return;
    const api = searchApiFor(deps);
    const nextNodeId = typeof api?.nextMatchNodeId === "function"
      ? api.nextMatchNodeId({ search, direction })
      : fallbackNextMatchNodeId(search, direction);
    if (!nextNodeId) return;
    fn(deps, "setSelectedNodeId", () => {})(nextNodeId);
    fn(deps, "renderCanvas", () => {})();
    fn(deps, "renderNodeList", () => {})();
    fn(deps, "renderNodeEditor", () => {})();
    fn(deps, "revealSelection", () => {})(nextNodeId, { editor: false });
  }

  window.WorkflowTemplateCanvasSearchActions = {
    fallbackNextMatchNodeId,
    selectSearchMatch,
    setNodeSearch,
  };
})();
