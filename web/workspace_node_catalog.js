(function () {
  "use strict";

  const REPO_SOURCE_KINDS = [
    "source.repo",
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
    "eval.report",
  ];

  const PAPER_SOURCE_KINDS = [
    "source.paper",
    "research.search",
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
    "eval.report",
  ];

  const IDEA_SOURCE_KINDS = [
    "source.idea",
    "research.search",
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
    "eval.report",
  ];

  function workspaceNodeMeta(nodeTypes = {}, kind = "") {
    const map = nodeTypes && typeof nodeTypes === "object" ? nodeTypes : {};
    return map[kind] || map["custom.step"];
  }

  function workspaceNodeLabel(nodeTypes = {}, kind = "") {
    const meta = workspaceNodeMeta(nodeTypes, kind) || {};
    return meta.label || kind || "节点";
  }

  function workspaceNodeKindsForSource(sourceType) {
    if (sourceType === "repo") return [...REPO_SOURCE_KINDS];
    if (sourceType === "paper") return [...PAPER_SOURCE_KINDS];
    return [...IDEA_SOURCE_KINDS];
  }

  window.WorkspaceNodeCatalog = {
    workspaceNodeKindsForSource,
    workspaceNodeLabel,
    workspaceNodeMeta,
  };
})();
