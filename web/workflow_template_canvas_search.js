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

  window.WorkflowTemplateCanvasSearch = {
    nodeMatchesSearch,
    nodeSearchText,
    searchState,
  };
})();
