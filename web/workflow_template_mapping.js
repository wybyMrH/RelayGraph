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

  function toText(mapping = {}) {
    if (!mapping || typeof mapping !== "object") return "";
    return Object.entries(mapping)
      .map(([key, value]) => `${String(key || "").trim()}: ${String(value || "").trim()}`.trim())
      .filter(Boolean)
      .join("\n");
  }

  function fromText(text = "") {
    const raw = String(text || "").trim();
    if (!raw) return {};
    if (raw.startsWith("{")) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          return Object.entries(parsed).reduce((acc, [key, value]) => {
            const name = String(key || "").trim();
            if (name) acc[name] = String(value || "").trim();
            return acc;
          }, {});
        }
      } catch (error) {
        // Keep accepting partial JSON while the user is editing.
      }
    }
    return raw.split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .reduce((acc, line) => {
        const separatorIndex = line.search(/[:=]/);
        if (separatorIndex <= 0) return acc;
        const name = line.slice(0, separatorIndex).trim();
        const value = line.slice(separatorIndex + 1).trim();
        if (name) acc[name] = value;
        return acc;
      }, {});
  }

  function entries(mapping = {}) {
    if (!mapping || typeof mapping !== "object") return [];
    return Object.entries(mapping)
      .map(([name, source]) => ({
        name: String(name || "").trim(),
        source: String(source || "").trim(),
      }))
      .filter((item) => item.name || item.source);
  }

  function fromEntries(rows = []) {
    return (Array.isArray(rows) ? rows : []).reduce((acc, entry) => {
      const name = String(entry?.name || "").trim();
      const source = String(entry?.source || "").trim();
      if (name && source) acc[name] = source;
      return acc;
    }, {});
  }

  function sourceStatus(source = "", sourceOptions = [], options = {}) {
    const value = String(source || "").trim();
    if (!value) return { status: "blocked", message: "来源为空" };
    if (value === "$prev.output" && options.requiresPreviousOutput && !options.sourceOutputKey) {
      return { status: "blocked", message: "上一节点缺 output_key" };
    }
    const known = sourceOptions.some((option) => String(option.value || "") === value);
    if (known) return { status: "ready", message: "" };
    if (value === "$input" || value.startsWith("$input.")) return { status: "ready", message: "" };
    if (value === "$context.outputs") return { status: "ready", message: "" };
    if (value.startsWith("$context.outputs.")) {
      return { status: "warning", message: "未出现在上游输出候选" };
    }
    if (value.startsWith("$prev.")) return { status: "warning", message: "自定义上一节点来源" };
    if (value.startsWith("$context.")) return { status: "warning", message: "自定义上下文来源" };
    return { status: "warning", message: "自定义来源" };
  }

  function health(rows = [], options = {}) {
    const normalizedRows = (Array.isArray(rows) ? rows : [])
      .map((entry, index) => ({
        index,
        name: String(entry?.name || "").trim(),
        source: String(entry?.source || "").trim(),
        messages: [],
        status: "ready",
      }))
      .filter((entry) => entry.name || entry.source);
    const counts = normalizedRows.reduce((acc, entry) => {
      if (entry.name) acc[entry.name] = (acc[entry.name] || 0) + 1;
      return acc;
    }, {});
    const targetInputs = (Array.isArray(options.targetInputs) ? options.targetInputs : [])
      .map((item) => String(item || "").trim())
      .filter(Boolean);
    const sourceOptions = Array.isArray(options.sourceOptions) ? options.sourceOptions : [];
    const rowHealth = normalizedRows.map((entry) => {
      const messages = [];
      let status = "ready";
      if (!entry.name) {
        status = "blocked";
        messages.push("输入名为空");
      }
      if (!entry.source) {
        status = "blocked";
        messages.push("来源为空");
      }
      if (entry.name && counts[entry.name] > 1) {
        if (status !== "blocked") status = "warning";
        messages.push("输入名重复，保存时会被后面的同名项覆盖");
      }
      const checkedSource = sourceStatus(entry.source, sourceOptions, options);
      if (checkedSource.status === "blocked") status = "blocked";
      else if (checkedSource.status === "warning" && status !== "blocked") status = "warning";
      if (checkedSource.message) messages.push(checkedSource.message);
      return { ...entry, status, messages };
    });
    const mappedNames = new Set(rowHealth.map((entry) => entry.name).filter(Boolean));
    const missingInputs = targetInputs.filter((name) => !mappedNames.has(name));
    const incompleteCount = rowHealth.filter((entry) => entry.status === "blocked").length;
    const warningCount = rowHealth.filter((entry) => entry.status === "warning").length + missingInputs.length;
    const draftDefault = Number(options.savedCount ?? rowHealth.length) === 0 && rowHealth.length > 0;
    const status = incompleteCount
      ? "blocked"
      : warningCount || draftDefault
        ? "warning"
        : rowHealth.length
          ? "ready"
          : targetInputs.length
            ? "blocked"
            : "warning";
    const summaryParts = [];
    if (rowHealth.length) summaryParts.push(`${rowHealth.length} 条映射`);
    else summaryParts.push("暂无映射");
    if (missingInputs.length) summaryParts.push(`缺 ${missingInputs.length} 个声明输入`);
    if (incompleteCount) summaryParts.push(`${incompleteCount} 条不完整`);
    if (warningCount && !incompleteCount) summaryParts.push(`${warningCount} 个提示`);
    if (draftDefault) summaryParts.push("默认预览未保存");
    return {
      status,
      rowHealth,
      missingInputs,
      incompleteCount,
      warningCount,
      draftDefault,
      summary: summaryParts.join(" · "),
    };
  }

  function healthMarkup(mappingHealth = {}, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const status = String(mappingHealth.status || "warning");
    const missing = Array.isArray(mappingHealth.missingInputs) ? mappingHealth.missingInputs : [];
    const detail = missing.length ? `缺少：${missing.slice(0, 5).join(" / ")}` : "";
    const draft = mappingHealth.draftDefault ? "默认映射还没有写入模板" : "";
    const parts = [detail, draft].filter(Boolean);
    return `
    <div class="workflow-template-mapping-health status-${escapeFor(deps, status)}" data-mapping-health-summary>
      <strong>${escapeFor(deps, mappingHealth.summary || "等待映射")}</strong>
      ${parts.length ? `<span title="${escapeFor(deps, parts.join(" · "))}">${escapeFor(deps, parts.join(" · "))}</span>` : ""}
    </div>
  `;
  }

  function sourceOptions(options = {}) {
    const deps = {
      nodeIoContract: options.nodeIoContract,
      nodeLabel: options.nodeLabel,
    };
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const index = Math.max(0, Number(options.index || 0));
    const previousNodes = nodes.slice(0, index);
    const values = [
      { value: "$input", label: "$input · 启动输入" },
      { value: "$prev.output", label: "$prev.output · 上一节点输出" },
      { value: "$context.outputs", label: "$context.outputs · 全部上下文输出" },
    ];
    previousNodes.forEach((item, itemIndex) => {
      const outputKey = String(item.output_key || nodeIoContract(item.kind || "", itemIndex).output || "").trim();
      if (!outputKey) return;
      const title = String(item.title || nodeLabel(item.kind || "") || outputKey).trim();
      values.push({
        value: `$context.outputs.${outputKey}`,
        label: `${outputKey} · ${title}`,
      });
    });
    return values;
  }

  function rowsMarkup(rows = [], optionRows = [], options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const nameAttr = options.nameAttr || "data-manage-input-mapping-name";
    const sourceAttr = options.sourceAttr || "data-manage-input-mapping-source";
    const sourceSelectAttr = options.sourceSelectAttr || "data-manage-input-mapping-source-select";
    const removeAction = options.removeAction || "remove-template-input-mapping";
    const sourcePlaceholder = options.sourcePlaceholder || "$context.outputs.repo_profile";
    const emptyText = options.emptyText || "还没有输入映射。可以点“添加映射”补一条。";
    const rowHealth = Array.isArray(options.health?.rowHealth) ? options.health.rowHealth : [];
    return rows.length ? rows.map((entry, rowIndex) => {
      const source = String(entry.source || "").trim();
      const hasSourceOption = optionRows.some((option) => option.value === source);
      const rowOptions = [
        ...optionRows,
        ...(hasSourceOption || !source ? [] : [{ value: source, label: `${source} · 自定义` }]),
      ];
      const rowState = rowHealth.find((item) => item.index === rowIndex) || {};
      const status = String(rowState.status || "ready");
      const message = Array.isArray(rowState.messages) && rowState.messages.length
        ? rowState.messages.join(" / ")
        : status === "ready"
          ? "映射正常"
          : "映射待确认";
      return `
      <div class="workflow-template-mapping-row status-${escapeFor(deps, status)}" data-mapping-row="${rowIndex}" title="${escapeFor(deps, message)}">
        <input ${nameAttr}="${rowIndex}" value="${escapeFor(deps, entry.name || "")}" placeholder="输入名，如 dataset_profile" />
        <select ${sourceSelectAttr}="${rowIndex}" title="选择常用来源">
          ${rowOptions.map((option) => `<option value="${escapeFor(deps, option.value)}" ${option.value === source ? "selected" : ""}>${escapeFor(deps, option.label)}</option>`).join("")}
        </select>
        <input ${sourceAttr}="${rowIndex}" value="${escapeFor(deps, source)}" placeholder="${escapeFor(deps, sourcePlaceholder)}" />
        <span class="workflow-template-mapping-row-actions">
          <em class="mapping-row-state">${escapeFor(deps, status === "ready" ? "ok" : status === "blocked" ? "阻塞" : "提示")}</em>
          <button class="secondary mini danger" type="button" data-action="${escapeFor(deps, removeAction)}" data-index="${rowIndex}" title="删除这条输入映射">删除</button>
        </span>
      </div>
    `;
    }).join("") : `<div class="empty">${escapeFor(deps, emptyText)}</div>`;
  }

  function inputEditorMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      nodeIoContract: options.nodeIoContract,
      nodeLabel: options.nodeLabel,
    };
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const node = options.node && typeof options.node === "object" ? options.node : {};
    const index = Math.max(0, Number(options.index || 0));
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const contract = nodeIoContract(node.kind || "", index);
    const mapping = node.input_mapping && typeof node.input_mapping === "object" ? node.input_mapping : {};
    const mappingEntries = entries(mapping);
    const rows = mappingEntries.length ? mappingEntries : (Array.isArray(contract.inputs) ? contract.inputs : [])
      .map((name) => ({ name: String(name || "").trim(), source: index === 0 ? "$input" : "$prev.output" }))
      .filter((item) => item.name);
    const optionRows = sourceOptions({ node, index, nodes, ...deps });
    const outputKey = String(node.output_key || contract.output || "").trim();
    const previousNode = nodes[index - 1] || null;
    const previousContract = previousNode ? nodeIoContract(previousNode.kind || "", index - 1) : {};
    const previousOutputKey = previousNode
      ? String(previousNode.output_key || previousContract.output || "").trim()
      : "";
    const mappingHealth = health(rows, {
      targetInputs: Array.isArray(contract.inputs) ? contract.inputs : [],
      sourceOptions: optionRows,
      sourceOutputKey: previousOutputKey,
      requiresPreviousOutput: index > 0,
      savedCount: mappingEntries.length,
    });
    const rowMarkup = rowsMarkup(rows, optionRows, {
      escapeHtml: options.escapeHtml,
      nameAttr: "data-manage-input-mapping-name",
      sourceAttr: "data-manage-input-mapping-source",
      sourceSelectAttr: "data-manage-input-mapping-source-select",
      removeAction: "remove-template-input-mapping",
      sourcePlaceholder: "$context.outputs.repo_profile",
      health: mappingHealth,
    });
    return `
    <section class="workflow-template-mapping-editor">
      <div class="workflow-template-mapping-head">
        <div>
          <strong>结构化 input_mapping</strong>
          <span>${escapeFor(deps, outputKey ? `输出写入 $context.outputs.${outputKey}` : "先设置 output_key")}</span>
        </div>
        <span class="workflow-template-mapping-head-actions">
          <button class="secondary mini" type="button" data-action="fill-template-input-mapping" title="为当前节点声明输入补齐缺失 input_mapping，不覆盖已有映射">补缺口</button>
          <button class="secondary mini" type="button" data-action="add-template-input-mapping" title="添加一条 input_mapping">添加映射</button>
        </span>
      </div>
      ${healthMarkup(mappingHealth, { escapeHtml: options.escapeHtml })}
      <div class="workflow-template-mapping-grid">
        <span>输入名</span>
        <span>常用来源</span>
        <span>实际来源</span>
        <span>操作</span>
        ${rowMarkup}
      </div>
      <details class="workflow-template-mapping-advanced">
        <summary>高级文本</summary>
        <textarea data-manage-input-mapping="1" rows="4" placeholder="dataset_profile: $context.outputs.dataset_profile">${escapeFor(deps, toText(mapping))}</textarea>
      </details>
    </section>
  `;
  }

  function inputEntriesFromEditor(editor) {
    return Array.from(editor?.querySelectorAll(".workflow-template-mapping-row") || []).map((row) => ({
      name: row.querySelector("[data-manage-input-mapping-name]")?.value || "",
      source: row.querySelector("[data-manage-input-mapping-source]")?.value || "",
    }));
  }

  function edgeEntriesFromEditor(editor) {
    return Array.from(editor?.querySelectorAll(".workflow-template-mapping-row") || []).map((row) => ({
      name: row.querySelector("[data-edge-input-mapping-name]")?.value || "",
      source: row.querySelector("[data-edge-input-mapping-source]")?.value || "",
    }));
  }

  function syncAdvancedText(editor, mapping = null) {
    const textarea = editor?.querySelector("[data-manage-input-mapping]");
    if (!textarea) return;
    const nextMapping = mapping || fromEntries(inputEntriesFromEditor(editor));
    textarea.value = toText(nextMapping);
  }

  function edgeState(options = {}) {
    const deps = {
      nodeIoContract: options.nodeIoContract,
      normalizePathForCompare: options.normalizePathForCompare,
    };
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const normalize = fn(deps, "normalizePathForCompare", (value) => String(value || "").trim());
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const selectedIndex = Number(options.selectedIndex || 0);
    const targetIndex = Math.max(0, Math.min(selectedIndex, Math.max(nodes.length - 1, 0)));
    const targetNode = nodes[targetIndex] || null;
    const sourceNode = targetIndex > 0 ? nodes[targetIndex - 1] : null;
    const sourceContract = sourceNode ? nodeIoContract(sourceNode.kind || "", targetIndex - 1) : null;
    const targetContract = targetNode ? nodeIoContract(targetNode.kind || "", targetIndex) : null;
    const sourceOutputKey = sourceNode
      ? String(sourceNode.output_key || sourceContract?.output || "").trim()
      : "$input";
    const sourceRef = sourceNode ? sourceOutputKey ? `$context.outputs.${sourceOutputKey}` : "$prev.output" : "$input";
    const targetMapping = targetNode?.input_mapping && typeof targetNode.input_mapping === "object" ? targetNode.input_mapping : {};
    const targetInputs = Array.isArray(targetContract?.inputs) ? targetContract.inputs : [];
    const rows = entries(targetMapping);
    const displayRows = rows.length ? rows : targetInputs
      .map((name) => ({ name: String(name || "").trim(), source: targetIndex === 0 ? "$input" : sourceRef }))
      .filter((item) => item.name);
    const mappedFromSource = Object.values(targetMapping)
      .filter((value) => normalize(value) === normalize(sourceRef) || String(value || "").trim() === "$prev.output")
      .length;
    const status = !targetNode
      ? "draft"
      : targetIndex === 0
        ? rows.length ? "ready" : "warning"
        : sourceOutputKey && rows.length ? "ready" : sourceOutputKey ? "warning" : "blocked";
    return {
      nodes,
      targetIndex,
      targetNode,
      sourceNode,
      sourceOutputKey,
      sourceRef,
      targetInputs,
      rows,
      displayRows,
      mappedFromSource,
      status,
    };
  }

  function edgeSourceOptions(edge = {}, options = {}) {
    const targetIndex = Number(edge.targetIndex || 0);
    const base = sourceOptions({
      node: edge.targetNode || options.node,
      index: targetIndex,
      nodes: edge.nodes || options.nodes,
      nodeIoContract: options.nodeIoContract,
      nodeLabel: options.nodeLabel,
    });
    const additions = [];
    if (edge.sourceNode && edge.sourceRef) {
      additions.push({
        value: edge.sourceRef,
        label: `${edge.sourceOutputKey || "上一节点输出"} · 上一节点显式输出`,
      });
    }
    return [
      ...additions,
      ...base.filter((option) => !additions.some((item) => item.value === option.value)),
    ];
  }

  function edgeStatusText(edge = {}, mappingHealth = {}) {
    if (mappingHealth.status === "ready") return `${Number(edge.rows?.length || 0)} 条映射已保存`;
    if (mappingHealth.status === "blocked") return mappingHealth.summary || "映射阻塞";
    return mappingHealth.summary || "等待确认映射";
  }

  function edgeInspectorMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      nodeIoContract: options.nodeIoContract,
      nodeLabel: options.nodeLabel,
      normalizePathForCompare: options.normalizePathForCompare,
    };
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const edge = edgeState(options);
    const target = edge.targetNode;
    if (!target) return "";
    const sourceTitle = edge.sourceNode
      ? edge.sourceNode.title || nodeLabel(edge.sourceNode.kind || "")
      : "启动输入";
    const targetTitle = target.title || nodeLabel(target.kind || "");
    const sourceMeta = edge.sourceNode
      ? edge.sourceOutputKey ? `$context.outputs.${edge.sourceOutputKey}` : "等待上游 output_key"
      : "$input";
    const optionRows = edgeSourceOptions(edge, options);
    const mappingHealth = health(edge.displayRows, {
      targetInputs: edge.targetInputs,
      sourceOptions: optionRows,
      sourceOutputKey: edge.sourceOutputKey,
      requiresPreviousOutput: edge.targetIndex > 0,
      savedCount: edge.rows.length,
    });
    const statusText = edgeStatusText(edge, mappingHealth);
    const rowMarkup = rowsMarkup(edge.displayRows, optionRows, {
      escapeHtml: options.escapeHtml,
      nameAttr: "data-edge-input-mapping-name",
      sourceAttr: "data-edge-input-mapping-source",
      sourceSelectAttr: "data-edge-input-mapping-source-select",
      removeAction: "remove-template-edge-mapping",
      sourcePlaceholder: edge.sourceRef || "$prev.output",
      emptyText: "当前节点没有声明输入，可手动添加一条边映射。",
      health: mappingHealth,
    });
    const canMapPrevious = edge.targetIndex === 0 || Boolean(edge.sourceOutputKey);
    const canClear = edge.rows.length > 0;
    return `
    <section class="workflow-template-edge-inspector status-${escapeFor(deps, mappingHealth.status)}" data-edge-target-id="${escapeFor(deps, target.id || "")}">
      <div class="workflow-template-edge-head">
        <div>
          <strong>交接映射</strong>
          <span title="${escapeFor(deps, `${sourceTitle} -> ${targetTitle}`)}">${escapeFor(deps, `${sourceTitle} -> ${targetTitle}`)}</span>
        </div>
        <em>${escapeFor(deps, statusText)}</em>
      </div>
      <div class="workflow-template-edge-summary">
        <span title="${escapeFor(deps, sourceMeta)}">${escapeFor(deps, sourceMeta)}</span>
        <strong aria-hidden="true">-></strong>
        <span title="${escapeFor(deps, targetTitle)}">${escapeFor(deps, targetTitle)}</span>
      </div>
      <div class="workflow-template-edge-actions">
        <button class="secondary mini" type="button" data-action="map-template-edge-previous" title="把当前节点输入映射到上一节点显式输出" ${canMapPrevious ? "" : "disabled"}>上一节点输出</button>
        <button class="secondary mini" type="button" data-action="map-template-edge-context" title="把当前节点输入映射到整个上下文输出">全部上下文</button>
        <button class="secondary mini" type="button" data-action="fill-template-edge-mapping" title="只补齐当前下游节点缺失的输入映射，不覆盖已有映射">补缺口</button>
        <button class="secondary mini" type="button" data-action="add-template-edge-mapping" title="添加一条交接映射">添加映射</button>
        <button class="secondary mini danger" type="button" data-action="clear-template-edge-mapping" title="清空当前节点 input_mapping" ${canClear ? "" : "disabled"}>清空</button>
      </div>
      ${healthMarkup(mappingHealth, { escapeHtml: options.escapeHtml })}
      <div class="workflow-template-edge-grid workflow-template-mapping-grid">
        <span>下游输入</span>
        <span>来源快捷</span>
        <span>实际来源</span>
        <span>操作</span>
        ${rowMarkup}
      </div>
    </section>
  `;
  }

  function defaultEdgeEntries(options = {}) {
    const mode = String(options.mode || "previous");
    const edge = edgeState(options);
    const names = edge.targetInputs.length ? edge.targetInputs : ["input"];
    const source = mode === "context"
      ? "$context.outputs"
      : edge.targetIndex === 0
        ? "$input"
        : edge.sourceRef || "$prev.output";
    return names.map((name) => ({ name: String(name || "").trim(), source })).filter((item) => item.name);
  }

  function priorOutputKeys(options = {}) {
    const deps = { nodeIoContract: options.nodeIoContract };
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const keys = new Set();
    (Array.isArray(options.nodes) ? options.nodes : []).slice(0, Math.max(0, Number(options.index || 0))).forEach((node, nodeIndex) => {
      if (!node || typeof node !== "object") return;
      const contract = nodeIoContract(node.kind || "", nodeIndex);
      const outputKey = String(node.output_key || contract.output || "").trim();
      if (outputKey) keys.add(outputKey);
    });
    return keys;
  }

  function defaultInputSource(options = {}) {
    const deps = {
      nodeIoContract: options.nodeIoContract,
      nodeIoFallbackMapping: options.nodeIoFallbackMapping,
    };
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const nodeIoFallbackMapping = fn(deps, "nodeIoFallbackMapping", () => ({}));
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const index = Math.max(0, Number(options.index || 0));
    const name = String(options.inputName || "").trim();
    if (index <= 0) return "$input";
    const priorOutputs = priorOutputKeys({ nodes, index, nodeIoContract });
    if (name && priorOutputs.has(name)) return `$context.outputs.${name}`;
    const fallback = nodeIoFallbackMapping(name ? [name] : [], index);
    const fallbackSource = String(fallback[name] || "").trim();
    if (fallbackSource) return fallbackSource;
    const previousNode = nodes[index - 1] || null;
    if (!previousNode) return "$prev.output";
    const previousContract = nodeIoContract(previousNode.kind || "", index - 1);
    const outputKey = String(previousNode.output_key || previousContract.output || "").trim();
    return outputKey ? `$context.outputs.${outputKey}` : "$prev.output";
  }

  function mergedMissingInputMapping(options = {}) {
    const deps = {
      nodeIoContract: options.nodeIoContract,
      nodeIoFallbackMapping: options.nodeIoFallbackMapping,
    };
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const node = options.node && typeof options.node === "object" ? options.node : {};
    const index = Math.max(0, Number(options.index || 0));
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const contract = nodeIoContract(node.kind || "", index);
    const targetInputs = (Array.isArray(contract.inputs) ? contract.inputs : [])
      .map((item) => String(item || "").trim())
      .filter(Boolean);
    const current = node.input_mapping && typeof node.input_mapping === "object" ? node.input_mapping : {};
    const mapping = fromEntries(entries(current));
    let added = 0;
    targetInputs.forEach((name) => {
      if (mapping[name]) return;
      mapping[name] = defaultInputSource({ nodes, index, inputName: name, ...deps });
      added += 1;
    });
    return { mapping, added, targetInputs };
  }

  function refreshEditorHealth(editor, options = {}) {
    if (!editor) return;
    const deps = {
      escapeHtml: options.escapeHtml,
      nodeIoContract: options.nodeIoContract,
      nodeLabel: options.nodeLabel,
      normalizePathForCompare: options.normalizePathForCompare,
    };
    const edgeMode = Boolean(options.edge);
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const node = options.node && typeof options.node === "object" ? options.node : {};
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const index = Math.max(0, Number(options.index || 0));
    const mappingEntries = edgeMode
      ? edgeEntriesFromEditor(editor)
      : inputEntriesFromEditor(editor);
    let mappingHealth;
    let edge = null;
    if (edgeMode) {
      edge = edgeState({ nodes, selectedIndex: index, ...deps });
      const optionRows = edgeSourceOptions(edge, { nodes, ...deps });
      mappingHealth = health(mappingEntries, {
        targetInputs: edge.targetInputs,
        sourceOptions: optionRows,
        sourceOutputKey: edge.sourceOutputKey,
        requiresPreviousOutput: edge.targetIndex > 0,
        savedCount: mappingEntries.length,
      });
    } else {
      const contract = nodeIoContract(node?.kind || "", index);
      const optionRows = sourceOptions({ node, index, nodes, ...deps });
      const previousNode = nodes[index - 1] || null;
      const previousContract = previousNode ? nodeIoContract(previousNode.kind || "", index - 1) : {};
      const previousOutputKey = previousNode
        ? String(previousNode.output_key || previousContract.output || "").trim()
        : "";
      mappingHealth = health(mappingEntries, {
        targetInputs: Array.isArray(contract.inputs) ? contract.inputs : [],
        sourceOptions: optionRows,
        sourceOutputKey: previousOutputKey,
        requiresPreviousOutput: index > 0,
        savedCount: mappingEntries.length,
      });
    }
    const summary = editor.querySelector("[data-mapping-health-summary]");
    if (summary) {
      const replacement = document.createElement("div");
      replacement.innerHTML = healthMarkup(mappingHealth, { escapeHtml: options.escapeHtml }).trim();
      summary.replaceWith(replacement.firstElementChild);
    }
    if (edgeMode && edge) {
      const status = String(mappingHealth.status || "warning");
      editor.classList.remove("status-ready", "status-warning", "status-blocked");
      editor.classList.add(`status-${status}`);
      const edgeStatus = editor.querySelector(".workflow-template-edge-head em");
      if (edgeStatus) edgeStatus.textContent = edgeStatusText(edge, mappingHealth);
    }
    Array.from(editor.querySelectorAll(".workflow-template-mapping-row")).forEach((row, rowIndex) => {
      const rowHealth = mappingHealth.rowHealth.find((item) => item.index === rowIndex) || {};
      const status = String(rowHealth.status || "ready");
      row.classList.remove("status-ready", "status-warning", "status-blocked");
      row.classList.add(`status-${status}`);
      const message = Array.isArray(rowHealth.messages) && rowHealth.messages.length
        ? rowHealth.messages.join(" / ")
        : status === "ready"
          ? "映射正常"
          : "映射待确认";
      row.title = message;
      const stateLabel = row.querySelector(".mapping-row-state");
      if (stateLabel) stateLabel.textContent = status === "ready" ? "ok" : status === "blocked" ? "阻塞" : "提示";
    });
  }

  window.WorkflowTemplateMapping = {
    defaultEdgeEntries,
    defaultInputSource,
    edgeEntriesFromEditor,
    edgeInspectorMarkup,
    edgeSourceOptions,
    edgeState,
    edgeStatusText,
    entries,
    fromEntries,
    fromText,
    health,
    healthMarkup,
    inputEditorMarkup,
    inputEntriesFromEditor,
    mergedMissingInputMapping,
    priorOutputKeys,
    refreshEditorHealth,
    rowsMarkup,
    sourceOptions,
    sourceStatus,
    syncAdvancedText,
    toText,
  };
})();
