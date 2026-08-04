(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function nodeSearchText(options = {}) {
    const deps = {
      agentById: options.agentById,
      nodeLabel: options.nodeLabel,
      phaseFor: options.phaseFor,
    };
    const node = options.node && typeof options.node === "object" ? options.node : {};
    const index = Number.isFinite(options.index) ? options.index : 0;
    const ioState = options.ioState && typeof options.ioState === "object" ? options.ioState : {};
    const handler = node.handler && typeof node.handler === "object" ? node.handler : {};
    const agent = fn(deps, "agentById", () => null)(handler.agent_id || "");
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const phaseFor = fn(deps, "phaseFor", () => "");
    const mapping = node.input_mapping && typeof node.input_mapping === "object" ? node.input_mapping : {};
    const mappingText = Object.entries(mapping)
      .map(([name, source]) => `${name} ${source}`)
      .join(" ");
    return [
      String(index + 1),
      node.id,
      node.title,
      node.kind,
      nodeLabel(node.kind || ""),
      phaseFor(node.kind || ""),
      node.output_key,
      ioState.outputKey,
      ioState.hint,
      handler.mode,
      handler.name,
      handler.agent_id,
      agent?.name,
      agent?.role,
      mappingText,
    ].filter(Boolean).join(" ").toLowerCase();
  }

  function nodeMatchesSearch(options = {}) {
    const text = String(options.query || "").trim().toLowerCase();
    if (!text) return true;
    return text.split(/\s+/).every((part) => nodeSearchText(options).includes(part));
  }

  function searchState(options = {}) {
    const query = String(options.query || "").trim();
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const ioStates = Array.isArray(options.ioStates) ? options.ioStates : [];
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const matches = !query
      ? []
      : nodes
        .map((node, index) => ({ node, index }))
        .filter(({ node, index }) => nodeMatchesSearch({
          ...options,
          node,
          index,
          ioState: ioStates[index],
          query,
        }));
    const selectedMatchIndex = matches.findIndex(({ node }) => String(node?.id || "") === selectedNodeId);
    return {
      query,
      matches,
      matchIndexes: new Set(matches.map((item) => item.index)),
      selectedMatchIndex,
      label: query
        ? matches.length
          ? `${selectedMatchIndex >= 0 ? selectedMatchIndex + 1 : 0}/${matches.length}`
          : "0/0"
        : "未筛选",
    };
  }

  function matchIndexSet(search = {}) {
    if (search.matchIndexes instanceof Set) return search.matchIndexes;
    if (Array.isArray(search.matchIndexes)) return new Set(search.matchIndexes);
    const matches = Array.isArray(search.matches) ? search.matches : [];
    return new Set(matches.map((item) => item.index));
  }

  function nodeIndexById(nodes = [], nodeId = "") {
    const normalized = String(nodeId || "").trim();
    return (Array.isArray(nodes) ? nodes : []).findIndex((node) => String(node?.id || "") === normalized);
  }

  function applySearchDecorations(options = {}) {
    const root = options.root;
    if (!root) return;
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const search = options.search && typeof options.search === "object" ? options.search : {};
    const query = String(search.query || "");
    const matches = Array.isArray(search.matches) ? search.matches : [];
    const indexes = matchIndexSet(search);
    const input = root.querySelector("[data-template-node-search]");
    if (input && input.value !== query) input.value = query;
    const count = root.querySelector("[data-template-node-search-count]");
    if (count) count.textContent = search.label || (query ? `${matches.length}/${matches.length}` : "未筛选");
    root.querySelectorAll("[data-action='template-search-prev'], [data-action='template-search-next']").forEach((button) => {
      button.disabled = !(query && matches.length);
    });
    root.querySelectorAll("[data-action='template-search-clear']").forEach((button) => {
      button.disabled = !query;
    });
    root.querySelectorAll(".workflow-template-flow-node").forEach((nodeEl) => {
      const index = Number(nodeEl.dataset.index || -1);
      const matched = !query || indexes.has(index);
      nodeEl.classList.toggle("search-match", Boolean(query && matched));
      nodeEl.classList.toggle("search-dim", Boolean(query && !matched));
    });
    root.querySelectorAll(".workflow-template-phase-node, .workflow-template-layout-node").forEach((nodeEl) => {
      const index = nodeIndexById(nodes, nodeEl.dataset.nodeId || "");
      const matched = !query || indexes.has(index);
      nodeEl.classList.toggle("search-match", Boolean(query && matched));
      nodeEl.classList.toggle("search-dim", Boolean(query && !matched));
    });
  }

  function nextMatchNodeId(options = {}) {
    const search = options.search && typeof options.search === "object" ? options.search : {};
    const matches = Array.isArray(search.matches) ? search.matches : [];
    if (!String(search.query || "").trim() || !matches.length) return "";
    const direction = Number(options.direction || 1);
    const currentIndex = Number(search.selectedMatchIndex) >= 0
      ? Number(search.selectedMatchIndex)
      : direction > 0
        ? -1
        : 0;
    const nextIndex = (currentIndex + direction + matches.length) % matches.length;
    return String(matches[nextIndex]?.node?.id || "").trim();
  }

  window.WorkflowTemplateCanvasSearch = {
    applySearchDecorations,
    nextMatchNodeId,
    nodeMatchesSearch,
    nodeSearchText,
    searchState,
  };
})();
