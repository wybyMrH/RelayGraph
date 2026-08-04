(function () {
  "use strict";

  const DEFAULT_SPACING = { x: 220, y: 76, node_width: 170, node_height: 46 };

  function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function cssToken(value, fallback = "default") {
    const token = String(value || fallback).trim().replace(/[^a-zA-Z0-9_-]/g, "-");
    return token || fallback;
  }

  function escapeFor(deps, value) {
    return (typeof deps.escapeHtml === "function" ? deps.escapeHtml : fallbackEscapeHtml)(value);
  }

  function previewFromState(options = {}) {
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const ioStates = Array.isArray(options.ioStates) ? options.ioStates : [];
    const validation = options.validation && typeof options.validation === "object" ? options.validation : {};
    const backend = validation.preview?.topology_preview;
    if (
      backend &&
      typeof backend === "object" &&
      backend.schema === "relaygraph.workflow_template.topology_preview.v1" &&
      Number(backend.node_count || 0) === nodes.length
    ) {
      return backend;
    }

    const linksFromNodes = typeof options.linksFromNodes === "function" ? options.linksFromNodes : () => [];
    const nodeIoState = typeof options.nodeIoState === "function" ? options.nodeIoState : () => ({ status: "ready" });
    const nodeLabel = typeof options.nodeLabel === "function" ? options.nodeLabel : (kind) => kind;
    const spacing = { ...DEFAULT_SPACING };
    const links = linksFromNodes(nodes);
    const topologyNodes = nodes.map((node, index) => {
      const io = ioStates[index] || nodeIoState(node, index, nodes) || {};
      return {
        id: String(node.id || "").trim(),
        index: index + 1,
        layer: index,
        lane: 0,
        x: index * spacing.x,
        y: 0,
        position: { x: index * spacing.x, y: 0 },
        kind: String(node.kind || "").trim(),
        title: String(node.title || nodeLabel(node.kind || "") || `节点 ${index + 1}`).trim(),
        status: io.status || "ready",
        incoming_count: index > 0 ? 1 : 0,
        outgoing_count: index < nodes.length - 1 ? 1 : 0,
        incoming: index > 0 ? [String(nodes[index - 1]?.id || "")] : [],
        outgoing: index < nodes.length - 1 ? [String(nodes[index + 1]?.id || "")] : [],
      };
    });
    const nodePosition = new Map(topologyNodes.map((node) => [node.id, node]));
    const controlEdges = (Array.isArray(links) ? links : []).map((link, index) => {
      const fromNode = nodePosition.get(String(link.from || "")) || {};
      const toNode = nodePosition.get(String(link.to || "")) || {};
      return {
        id: String(link.id || `edge-${index + 1}`),
        index,
        kind: "control_link",
        from: String(link.from || ""),
        to: String(link.to || ""),
        status: "ready",
        points: [
          { x: Number(fromNode.x || 0) + spacing.node_width, y: Number(fromNode.y || 0) + spacing.node_height / 2 },
          { x: Number(toNode.x || 0), y: Number(toNode.y || 0) + spacing.node_height / 2 },
        ],
      };
    });

    return {
      schema: "relaygraph.workflow_template.topology_preview.v1",
      layout_mode: nodes.length ? "sequence" : "empty",
      node_count: topologyNodes.length,
      edge_count: controlEdges.length,
      control_edge_count: controlEdges.length,
      data_edge_count: 0,
      layer_count: topologyNodes.length,
      branch_count: 0,
      join_count: 0,
      disconnected_count: 0,
      cycle_detected: false,
      cycle_node_ids: [],
      dangling_link_count: 0,
      dangling_links: [],
      spacing,
      bounds: {
        width: Math.max(spacing.node_width, (topologyNodes.length - 1) * spacing.x + spacing.node_width),
        height: spacing.node_height,
      },
      layers: topologyNodes.map((node) => ({ index: node.layer, node_ids: [node.id], count: 1 })),
      nodes: topologyNodes,
      edges: controlEdges,
      control_edges: controlEdges,
      data_edges: [],
    };
  }

  function layoutLabel(mode = "") {
    const value = String(mode || "").trim();
    if (value === "sequence") return "顺序链";
    if (value === "branch") return "分支/汇合";
    if (value === "graph") return "图结构";
    if (value === "cyclic") return "存在环";
    if (value === "isolated") return "未连接";
    if (value === "empty") return "空模板";
    return "拓扑";
  }

  function markup(options = {}) {
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const ioStates = Array.isArray(options.ioStates) ? options.ioStates : [];
    const topology = previewFromState(options);
    const topologyNodes = Array.isArray(topology.nodes) ? topology.nodes : [];
    if (!topologyNodes.length) return "";

    const nodeById = new Map(nodes.map((node, index) => [String(node?.id || ""), { node, index }]));
    const search = options.search && typeof options.search === "object" ? options.search : {};
    const matchIndexes = search.matchIndexes instanceof Set ? search.matchIndexes : new Set();
    const query = String(search.query || "").trim();
    const spacing = topology.spacing && typeof topology.spacing === "object" ? topology.spacing : DEFAULT_SPACING;
    const bounds = topology.bounds && typeof topology.bounds === "object" ? topology.bounds : {};
    const padding = 12;
    const width = Math.max(320, Number(bounds.width || 0) + padding * 2);
    const height = Math.max(70, Number(bounds.height || 0) + padding * 2);
    const selectedId = String(options.selectedNodeId || "").trim();
    const starterNodePhase = typeof options.starterNodePhase === "function" ? options.starterNodePhase : () => "其他";
    const nodeLabel = typeof options.nodeLabel === "function" ? options.nodeLabel : (kind) => kind;
    const statusLabel = typeof options.statusLabel === "function" ? options.statusLabel : (status) => status;
    const phaseTones = options.phaseTones && typeof options.phaseTones === "object" ? options.phaseTones : {};
    const deps = { escapeHtml: options.escapeHtml };
    const edges = Array.isArray(topology.edges) ? topology.edges.slice(0, 160) : [];
    const lines = edges.map((edge) => {
      const points = Array.isArray(edge.points) ? edge.points : [];
      const p1 = points[0] || {};
      const p2 = points[1] || {};
      const status = String(edge.status || "ready").trim() || "ready";
      const kind = String(edge.kind || "control_link").trim() || "control_link";
      return `<line class="workflow-template-layout-edge kind-${escapeFor(deps, cssToken(kind))} status-${escapeFor(deps, cssToken(status))}" x1="${Number(p1.x || 0) + padding}" y1="${Number(p1.y || 0) + padding}" x2="${Number(p2.x || 0) + padding}" y2="${Number(p2.y || 0) + padding}" />`;
    }).join("");
    const nodeMarkup = topologyNodes.map((item) => {
      const id = String(item.id || "").trim();
      const source = nodeById.get(id) || {};
      const node = source.node || {};
      const index = Number.isFinite(source.index) ? source.index : Math.max(0, Number(item.index || 1) - 1);
      const phase = starterNodePhase(item.kind || node.kind || "");
      const tone = phaseTones[phase] || "other";
      const matched = !query || matchIndexes.has(index);
      const searchClass = query ? (matched ? " search-match" : " search-dim") : "";
      const active = id && id === selectedId ? " active" : "";
      const status = String(item.status || ioStates[index]?.status || "ready").trim() || "ready";
      const x = Number(item.x ?? item.position?.x ?? index * Number(spacing.x || 220)) + padding;
      const y = Number(item.y ?? item.position?.y ?? 0) + padding;
      const label = String(item.title || node.title || nodeLabel(item.kind || node.kind || "") || id || `节点 ${index + 1}`).trim();
      const detail = [
        phase,
        item.outgoing_count > 1 ? `${Number(item.outgoing_count || 0)} 出` : "",
        item.incoming_count > 1 ? `${Number(item.incoming_count || 0)} 入` : "",
        ioStates[index]?.hint || "",
      ].filter(Boolean).join(" · ");
      return `
        <button
          class="workflow-template-layout-node tone-${escapeFor(deps, cssToken(tone))} status-${escapeFor(deps, cssToken(status))}${active}${searchClass}"
          type="button"
          data-action="select-template-node"
          data-node-id="${escapeFor(deps, id)}"
          style="left:${x}px;top:${y}px;width:${Number(spacing.node_width || 170)}px;height:${Number(spacing.node_height || 46)}px"
          title="${escapeFor(deps, `${label} · ${detail}`)}"
        >
          <span>${escapeFor(deps, String(index + 1))}</span>
          <strong>${escapeFor(deps, label)}</strong>
          <em>${escapeFor(deps, detail || statusLabel(status))}</em>
        </button>
      `;
    }).join("");
    const badges = [
      layoutLabel(topology.layout_mode),
      `${Number(topology.node_count || topologyNodes.length)} 节点`,
      `${Number(topology.control_edge_count || 0)} 控制边`,
      Number(topology.data_edge_count || 0) ? `${Number(topology.data_edge_count || 0)} 数据边` : "",
      Number(topology.branch_count || 0) ? `${Number(topology.branch_count || 0)} 分支` : "",
      Number(topology.join_count || 0) ? `${Number(topology.join_count || 0)} 汇合` : "",
      Number(topology.dangling_link_count || 0) ? `${Number(topology.dangling_link_count || 0)} 悬空边` : "",
    ].filter(Boolean);
    const topologyStatus = topology.cycle_detected || Number(topology.dangling_link_count || 0) ? "warning" : "ready";
    return `
      <div class="workflow-template-layout-preview status-${escapeFor(deps, cssToken(topologyStatus))}">
        <div class="workflow-template-layout-head">
          <strong>${escapeFor(deps, "拓扑预览")}</strong>
          <span>${badges.map((item) => `<em>${escapeFor(deps, item)}</em>`).join("")}</span>
        </div>
        <div class="workflow-template-layout-rail" aria-label="模板拓扑布局预览">
          <div class="workflow-template-layout-stage" style="width:${width}px;height:${height}px">
            <svg class="workflow-template-layout-edges" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">
              ${lines}
            </svg>
            ${nodeMarkup}
          </div>
        </div>
      </div>
    `;
  }

  window.WorkflowTemplateTopology = {
    layoutLabel,
    markup,
    previewFromState,
  };
})();
