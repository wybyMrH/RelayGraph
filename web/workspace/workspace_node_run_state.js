(function () {
  "use strict";

  const WORKSPACE_JOB_EXECUTABLE_KINDS = new Set([
    "repo.clone",
    "path.resolve",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
  ]);

  const WORKSPACE_AGENT_EXECUTABLE_KINDS = new Set([
    "repo.inspect",
    "env.infer",
    "dataset.find",
    "eval.report",
    "research.search",
    "path.resolve",
    "artifact.collect",
  ]);

  const WORKSPACE_SHELL_DISCOVERY_KINDS = new Set([
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "eval.report",
    "path.resolve",
    "artifact.collect",
  ]);

  function workspaceNodeSupportsAgentRun(node = null) {
    const kind = String(node?.kind || "").trim();
    if (!WORKSPACE_AGENT_EXECUTABLE_KINDS.has(kind)) return false;
    const handler = node?.handler && typeof node.handler === "object" ? node.handler : {};
    return String(handler.mode || "") === "agent" && String(handler.agent_id || "").trim();
  }

  function workspaceNodeSupportsJobRun(node = null) {
    const kind = String(node?.kind || "").trim();
    return WORKSPACE_JOB_EXECUTABLE_KINDS.has(kind) || WORKSPACE_SHELL_DISCOVERY_KINDS.has(kind);
  }

  function workspaceRuntimeTrace(node = {}) {
    return Array.isArray(node?.trace)
      ? node.trace
      : Array.isArray(node?.runtime?.trace)
        ? node.runtime.trace
        : [];
  }

  function workspaceRuntimeArtifacts(node = {}) {
    return Array.isArray(node?.artifacts)
      ? node.artifacts
      : Array.isArray(node?.runtime?.artifacts)
        ? node.runtime.artifacts
        : [];
  }

  function workspaceRuntimeResources(node = {}) {
    if (node?.resources && typeof node.resources === "object") return node.resources;
    if (node?.runtime?.resources && typeof node.runtime.resources === "object") return node.runtime.resources;
    return {};
  }

  window.WorkspaceNodeRunState = {
    agentExecutableKinds: Array.from(WORKSPACE_AGENT_EXECUTABLE_KINDS),
    jobExecutableKinds: Array.from(WORKSPACE_JOB_EXECUTABLE_KINDS),
    shellDiscoveryKinds: Array.from(WORKSPACE_SHELL_DISCOVERY_KINDS),
    workspaceNodeSupportsAgentRun,
    workspaceNodeSupportsJobRun,
    workspaceRuntimeArtifacts,
    workspaceRuntimeResources,
    workspaceRuntimeTrace,
  };
})();
