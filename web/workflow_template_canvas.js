(function () {
  "use strict";

  function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeFor(deps, value) {
    return (typeof deps.escapeHtml === "function" ? deps.escapeHtml : fallbackEscapeHtml)(value);
  }

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function searchToolsMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const search = options.search && typeof options.search === "object" ? options.search : {};
    const query = String(search.query || "");
    const hasQuery = Boolean(query);
    return `
      <div class="workflow-template-canvas-tools">
        <label class="workflow-template-canvas-search" title="按节点标题、类型、Agent、output_key 或 input_mapping 查找">
          <span>查找</span>
          <input data-template-node-search value="${escapeFor(deps, query)}" placeholder="节点 / kind / output / Agent" />
        </label>
        <span class="workflow-template-canvas-search-count" data-template-node-search-count>${escapeFor(deps, search.label || "未筛选")}</span>
        <button class="secondary mini" type="button" data-action="template-search-prev" title="跳到上一个匹配节点" ${hasQuery && search.matches?.length ? "" : "disabled"}>上一个</button>
        <button class="secondary mini" type="button" data-action="template-search-next" title="跳到下一个匹配节点" ${hasQuery && search.matches?.length ? "" : "disabled"}>下一个</button>
        <button class="secondary mini" type="button" data-action="template-search-clear" title="清空节点查找" ${hasQuery ? "" : "disabled"}>清空</button>
      </div>
    `;
  }

  function nodeFlowMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      statusClass: options.statusClass,
      phaseFor: options.phaseFor,
      nodeMeta: options.nodeMeta,
      agentById: options.agentById,
      nodeLabel: options.nodeLabel,
      statusLabel: options.statusLabel,
      nodeIoState: options.nodeIoState,
      matchesSearch: options.matchesSearch,
    };
    const node = options.node && typeof options.node === "object" ? options.node : {};
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const index = Number.isFinite(options.index) ? options.index : 0;
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const active = String(node.id || "") === selectedNodeId ? " active" : "";
    const statusClass = fn(deps, "statusClass", (status) => status)(node.status || "ready");
    const phase = fn(deps, "phaseFor", () => "其他")(node.kind || "");
    const phaseTones = options.phaseTones && typeof options.phaseTones === "object" ? options.phaseTones : {};
    const phaseTone = phaseTones[phase] || "other";
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const statusLabel = fn(deps, "statusLabel", (status) => status);
    const meta = fn(deps, "nodeMeta", () => ({}))(node.kind || "custom.step") || {};
    const handler = node.handler && typeof node.handler === "object" ? node.handler : {};
    const agent = fn(deps, "agentById", () => null)(handler.agent_id || "");
    const io = options.ioState || fn(deps, "nodeIoState", () => ({ status: "ready", hint: "" }))(node, index, nodes) || {};
    const next = nodes[index + 1] || null;
    const nextTitle = next ? next.title || nodeLabel(next.kind) : "结束";
    const agentLabel = handler.mode === "agent"
      ? agent?.name || handler.name || "Agent 待绑定"
      : handler.mode === "system"
        ? handler.name || "系统"
        : handler.name || "人工";
    const canMoveUp = index > 0;
    const canMoveDown = index < nodes.length - 1;
    const searchQuery = String(options.searchQuery || "").trim();
    const searchMatched = !searchQuery || fn(deps, "matchesSearch", () => true)(node, index, io, searchQuery);
    const searchClass = searchQuery ? (searchMatched ? " search-match" : " search-dim") : "";
    return `
      <article
        class="workflow-template-flow-node workspace-flow-node status-${escapeFor(deps, statusClass)} tone-${escapeFor(deps, phaseTone)}${active}${searchClass}"
        data-node-id="${escapeFor(deps, node.id || "")}"
        data-index="${escapeFor(deps, String(index))}"
        title="${escapeFor(deps, `${node.title || nodeLabel(node.kind)} · ${agentLabel} · ${io.hint || ""}`)}"
      >
        <button
          class="workspace-flow-node-select"
          type="button"
          data-action="select-template-node"
          data-node-id="${escapeFor(deps, node.id || "")}"
        >
          <div class="workspace-flow-node-head">
            <span class="workspace-flow-node-icon">${escapeFor(deps, String(index + 1))}</span>
            <div class="workspace-flow-node-copy">
              <span class="workspace-flow-node-phase">${escapeFor(deps, phase)}</span>
              <strong>${escapeFor(deps, node.title || nodeLabel(node.kind))}</strong>
            </div>
            <span class="workspace-flow-node-state">${escapeFor(deps, statusLabel(node.status || "ready"))}</span>
          </div>
          <p class="workspace-flow-node-desc">${escapeFor(deps, meta.description || nodeLabel(node.kind))}</p>
          <div class="workspace-flow-node-meta-row">
            <span>${escapeFor(deps, agentLabel)}</span>
            <em>${escapeFor(deps, io.outputKey || "等待 output_key")}</em>
          </div>
          <div class="workflow-template-node-io status-${escapeFor(deps, io.status)}">
            <span>${escapeFor(deps, io.hint || "")}</span>
            <em>${escapeFor(deps, `交接至 ${nextTitle}`)}</em>
          </div>
        </button>
        <div class="workflow-template-node-actions">
          <button class="secondary mini" type="button" data-action="move-template-node" data-node-id="${escapeFor(deps, node.id || "")}" data-direction="up" title="上移这个节点" ${canMoveUp ? "" : "disabled"}>上移</button>
          <button class="secondary mini" type="button" data-action="move-template-node" data-node-id="${escapeFor(deps, node.id || "")}" data-direction="down" title="下移这个节点" ${canMoveDown ? "" : "disabled"}>下移</button>
          <button class="secondary mini" type="button" data-action="insert-template-node-after" data-node-id="${escapeFor(deps, node.id || "")}" title="在这个节点后插入当前选择的节点类型">插入</button>
          <button class="secondary mini danger" type="button" data-action="delete-template-node" data-node-id="${escapeFor(deps, node.id || "")}" title="删除这个模板节点" ${nodes.length <= 1 ? "disabled" : ""}>删除</button>
        </div>
      </article>
    `;
  }

  function connectorMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      nodeIoState: options.nodeIoState,
      nodeLabel: options.nodeLabel,
    };
    const leftNode = options.leftNode && typeof options.leftNode === "object" ? options.leftNode : {};
    const rightNode = options.rightNode && typeof options.rightNode === "object" ? options.rightNode : {};
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const rightIndex = Number.isFinite(options.rightIndex) ? options.rightIndex : 0;
    const nodeIoState = fn(deps, "nodeIoState", () => ({ status: "ready", hint: "" }));
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const leftIo = nodeIoState(leftNode, Math.max(0, rightIndex - 1), nodes) || {};
    const rightIo = options.rightIoState || nodeIoState(rightNode, rightIndex, nodes) || {};
    const status = leftIo.outputKey && rightIo.status === "ready"
      ? "done"
      : leftIo.outputKey && rightIo.status !== "blocked"
        ? "running"
        : "pending";
    const title = `${leftNode.title || nodeLabel(leftNode.kind || "")} -> ${rightNode.title || nodeLabel(rightNode.kind || "")}`;
    return `
      <button
        class="workflow-template-flow-connector workspace-flow-connector status-${escapeFor(deps, status)}"
        type="button"
        data-action="select-template-edge"
        data-node-id="${escapeFor(deps, rightNode.id || "")}"
        title="${escapeFor(deps, `${title} · ${rightIo.health?.summary || rightIo.hint || ""}`)}"
        aria-label="${escapeFor(deps, `编辑第 ${rightIndex + 1} 个节点的交接映射`)}"
      >
        <span>映射</span>
      </button>
    `;
  }

  function phaseMapMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      phaseFor: options.phaseFor,
      nodeIoState: options.nodeIoState,
      nodeLabel: options.nodeLabel,
    };
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const ioStates = Array.isArray(options.ioStates) ? options.ioStates : [];
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const phaseTones = options.phaseTones && typeof options.phaseTones === "object" ? options.phaseTones : {};
    const phases = Object.keys(phaseTones);
    const buckets = new Map(phases.map((phase) => [phase, []]));
    const query = String(options.search?.query || "").trim();
    const matchIndexes = options.search?.matchIndexes instanceof Set ? options.search.matchIndexes : new Set();
    const phaseFor = fn(deps, "phaseFor", () => "其他");
    const nodeIoState = fn(deps, "nodeIoState", () => ({ status: "ready", hint: "" }));
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    nodes.forEach((node, index) => {
      const phase = phaseFor(node.kind || "");
      const bucket = buckets.get(phase) || buckets.get("其他") || [];
      bucket.push({
        node,
        index,
        io: ioStates[index] || nodeIoState(node, index, nodes),
      });
      if (!buckets.has(phase)) buckets.set(phase, bucket);
    });
    return `
      <div class="workflow-template-phase-map" aria-label="模板阶段导航">
        ${phases.map((phase) => {
          const items = buckets.get(phase) || [];
          if (!items.length) return "";
          const tone = phaseTones[phase] || "other";
          const readyCount = items.filter((item) => item.io.status === "ready").length;
          const phaseStatus = items.some((item) => item.io.status === "blocked")
            ? "blocked"
            : items.some((item) => item.io.status === "warning")
              ? "warning"
              : "ready";
          const first = items[0]?.node || {};
          return `
            <section class="workflow-template-phase-band tone-${escapeFor(deps, tone)} status-${escapeFor(deps, phaseStatus)}">
              <button class="workflow-template-phase-head" type="button" data-action="select-template-node" data-node-id="${escapeFor(deps, first.id || "")}" title="${escapeFor(deps, `跳到 ${phase}`)}">
                <strong>${escapeFor(deps, phase)}</strong>
                <span>${escapeFor(deps, `${items.length} 节点 · ${readyCount}/${items.length} I/O`)}</span>
              </button>
              <div class="workflow-template-phase-nodes">
                ${items.map((item) => {
                  const node = item.node || {};
                  const title = node.title || nodeLabel(node.kind || "");
                  const active = String(node.id || "") === selectedNodeId ? " active" : "";
                  const searchClass = query ? (matchIndexes.has(item.index) ? " search-match" : " search-dim") : "";
                  return `
                    <button
                      class="workflow-template-phase-node status-${escapeFor(deps, item.io.status)}${active}${searchClass}"
                      type="button"
                      data-action="select-template-node"
                      data-node-id="${escapeFor(deps, node.id || "")}"
                      title="${escapeFor(deps, `${item.index + 1}. ${title} · ${item.io.hint}`)}"
                    >
                      <span>${escapeFor(deps, String(item.index + 1))}</span>
                      <em>${escapeFor(deps, item.io.outputKey || "output")}</em>
                    </button>
                  `;
                }).join("")}
              </div>
            </section>
          `;
        }).join("")}
      </div>
    `;
  }

  window.WorkflowTemplateCanvas = {
    connectorMarkup,
    nodeFlowMarkup,
    phaseMapMarkup,
    searchToolsMarkup,
  };
})();
