(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function nodeIoState(options = {}) {
    const deps = {
      fallbackMapping: options.fallbackMapping,
      inputMappingEntries: options.inputMappingEntries,
      mappingHealth: options.mappingHealth,
      mappingSourceOptions: options.mappingSourceOptions,
      nodeIoContract: options.nodeIoContract,
    };
    const node = options.node && typeof options.node === "object" ? options.node : {};
    const index = Number.isFinite(Number(options.index)) ? Number(options.index) : 0;
    const nodeList = Array.isArray(options.nodes) ? options.nodes : [];
    const nodeIoContract = fn(deps, "nodeIoContract", () => ({}));
    const inputMappingEntries = fn(deps, "inputMappingEntries", () => []);
    const fallbackMapping = fn(deps, "fallbackMapping", () => ({}));
    const mappingSourceOptions = fn(deps, "mappingSourceOptions", () => []);
    const mappingHealth = fn(deps, "mappingHealth", () => ({
      status: "warning",
      missingInputs: [],
    }));

    const contract = nodeIoContract(node.kind || "", index) || {};
    const outputKey = String(node.output_key || contract.output || "").trim();
    const inputMapping = node.input_mapping && typeof node.input_mapping === "object" ? node.input_mapping : {};
    const entries = inputMappingEntries(inputMapping);
    const targetInputs = Array.isArray(contract.inputs) ? contract.inputs : [];
    const fallbackRows = inputMappingEntries(fallbackMapping(targetInputs, index));
    const rows = entries.length ? entries : fallbackRows;
    const sourceOptions = mappingSourceOptions(node, index, nodeList);
    const previousNode = nodeList[index - 1] || null;
    const previousContract = previousNode ? nodeIoContract(previousNode.kind || "", index - 1) || {} : {};
    const previousOutputKey = previousNode
      ? String(previousNode.output_key || previousContract.output || "").trim()
      : "";
    const health = mappingHealth(rows, {
      targetInputs,
      sourceOptions,
      sourceOutputKey: previousOutputKey,
      requiresPreviousOutput: index > 0,
      savedCount: entries.length,
    });
    const inputCount = entries.length;
    const status = !outputKey
      ? "blocked"
      : health.status === "ready"
        ? "ready"
        : health.status === "blocked"
          ? "blocked"
          : "warning";
    const inputLabel = inputCount
      ? `${inputCount} 输入`
      : health.missingInputs?.length
        ? `缺 ${health.missingInputs.length} 输入`
        : index === 0
          ? "$input"
          : "等待 input_mapping";
    const hint = `${inputLabel} -> ${outputKey || "output"}`;
    return { outputKey, inputCount, status, hint, health };
  }

  window.WorkflowTemplateIoState = {
    nodeIoState,
  };
})();
