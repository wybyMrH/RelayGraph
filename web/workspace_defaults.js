(function () {
  "use strict";

  const NODE_TEMPLATES = {
    repo: [
      { kind: "source.repo", title: "仓库输入" },
      { kind: "repo.clone", title: "克隆仓库" },
      { kind: "path.resolve", title: "解析路径" },
      { kind: "repo.inspect", title: "检查仓库" },
      { kind: "dataset.find", title: "发现数据集" },
      { kind: "env.infer", title: "推断环境" },
      { kind: "env.prepare", title: "准备环境" },
      { kind: "gpu.allocate", title: "分配 GPU" },
      { kind: "run.command", title: "运行任务" },
      { kind: "artifact.collect", title: "收集产物" },
      { kind: "eval.report", title: "结果整理" },
    ],
    paper: [
      { kind: "source.paper", title: "论文输入" },
      { kind: "research.search", title: "检索资料" },
      { kind: "repo.clone", title: "克隆仓库" },
      { kind: "path.resolve", title: "解析路径" },
      { kind: "repo.inspect", title: "检查仓库" },
      { kind: "dataset.find", title: "发现数据集" },
      { kind: "env.infer", title: "推断环境" },
      { kind: "env.prepare", title: "准备环境" },
      { kind: "gpu.allocate", title: "分配 GPU" },
      { kind: "run.command", title: "运行任务" },
      { kind: "artifact.collect", title: "收集产物" },
      { kind: "eval.report", title: "结果整理" },
    ],
    idea: [
      { kind: "source.idea", title: "想法输入" },
      { kind: "research.search", title: "检索资料" },
      { kind: "repo.clone", title: "克隆仓库" },
      { kind: "path.resolve", title: "解析路径" },
      { kind: "repo.inspect", title: "检查仓库" },
      { kind: "dataset.find", title: "发现数据集" },
      { kind: "env.infer", title: "推断环境" },
      { kind: "env.prepare", title: "准备环境" },
      { kind: "gpu.allocate", title: "分配 GPU" },
      { kind: "run.command", title: "运行任务" },
      { kind: "artifact.collect", title: "收集产物" },
      { kind: "eval.report", title: "结果整理" },
    ],
  };

  function fallbackDeepClone(value, fallback) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return fallback;
    }
  }

  function deepCloneFor(deps = {}) {
    return typeof deps.deepClone === "function" ? deps.deepClone : fallbackDeepClone;
  }

  function agentCatalogFor(deps = {}) {
    return Array.isArray(deps.agentCatalog) ? deps.agentCatalog : [];
  }

  function sourceAgentRoleIdsFor(deps = {}) {
    return deps.sourceAgentRoleIds && typeof deps.sourceAgentRoleIds === "object"
      ? deps.sourceAgentRoleIds
      : {};
  }

  function toolCatalogFor(deps = {}) {
    return Array.isArray(deps.toolCatalog) ? deps.toolCatalog : [];
  }

  function recommendedAgentTemplateByRole(role, deps = {}) {
    return agentCatalogFor(deps).find((agent) => agent.role === role || agent.id === role) || null;
  }

  function recommendedAgentRoleIds(sourceType, deps = {}) {
    const sourceAgentRoleIds = sourceAgentRoleIdsFor(deps);
    const fallback = sourceAgentRoleIds.repo;
    return sourceAgentRoleIds[String(sourceType || "repo")] || fallback;
  }

  function recommendedAgentTemplatesForSource(sourceType, deps = {}) {
    const deepClone = deepCloneFor(deps);
    const getRoleIds = typeof deps.recommendedAgentRoleIds === "function"
      ? deps.recommendedAgentRoleIds
      : (value) => recommendedAgentRoleIds(value, deps);
    const getTemplate = typeof deps.recommendedAgentTemplateByRole === "function"
      ? deps.recommendedAgentTemplateByRole
      : (role) => recommendedAgentTemplateByRole(role, deps);
    return (getRoleIds(sourceType) || [])
      .map((role) => deepClone(getTemplate(role), null))
      .filter(Boolean);
  }

  function workspaceAgentLibraryTemplates(sourceType, deps = {}) {
    const deepClone = deepCloneFor(deps);
    const getTemplates = typeof deps.recommendedAgentTemplatesForSource === "function"
      ? deps.recommendedAgentTemplatesForSource
      : (value) => recommendedAgentTemplatesForSource(value, deps);
    const primary = getTemplates(sourceType);
    const seen = new Set(primary.map((agent) => agent.role));
    agentCatalogFor(deps).forEach((agent) => {
      if (seen.has(agent.role)) return;
      primary.push(deepClone(agent, null));
    });
    return primary;
  }

  function defaultWorkspaceTools(deps = {}) {
    return deepCloneFor(deps)(toolCatalogFor(deps), []);
  }

  function defaultWorkspaceAgents(sourceType, deps = {}) {
    const getTemplates = typeof deps.recommendedAgentTemplatesForSource === "function"
      ? deps.recommendedAgentTemplatesForSource
      : (value) => recommendedAgentTemplatesForSource(value, deps);
    return getTemplates(sourceType);
  }

  function defaultWorkspaceModel() {
    return {
      provider_profile_id: "",
      routing_mode: "workspace_default",
      chat_agent_id: "",
      notes: "",
    };
  }

  function defaultWorkspaceNodes(sourceType = "repo", deps = {}) {
    const makeClientId = typeof deps.makeClientId === "function"
      ? deps.makeClientId
      : (prefix = "node") => `${prefix}-${Date.now()}`;
    const nodeDefaultConfig = typeof deps.workspaceNodeDefaultConfig === "function"
      ? deps.workspaceNodeDefaultConfig
      : () => ({});
    return (NODE_TEMPLATES[sourceType] || NODE_TEMPLATES.repo).map((template, index) => ({
      id: makeClientId("node"),
      kind: template.kind,
      title: template.title,
      order: index,
      config: nodeDefaultConfig(template.kind),
      handler: { mode: "agent" },
      runtime: {},
    }));
  }

  function defaultWorkspaceForm(sourceType = "repo", deps = {}) {
    const baseDefaults = {
      name: "",
      brief: "",
      tags: [],
      status: "draft",
      env_name: "",
      env_manager: "",
      python_version: "",
      setup_command: "",
      run_command: "",
      report_command: "",
      schedule: "",
    };

    const sourceDefaults = {
      repo: {
        source_type: "repo",
        repo_url: "",
        repo_ref: "",
        workspace_dir: "",
      },
      paper: {
        source_type: "paper",
        paper_url: "",
        workspace_dir: "",
      },
      idea: {
        source_type: "idea",
        idea_text: "",
        workspace_dir: "",
      },
    };

    const nodes = typeof deps.defaultWorkspaceNodes === "function"
      ? deps.defaultWorkspaceNodes
      : (value) => defaultWorkspaceNodes(value, deps);
    const agents = typeof deps.defaultWorkspaceAgents === "function"
      ? deps.defaultWorkspaceAgents
      : (value) => defaultWorkspaceAgents(value, deps);
    const tools = typeof deps.defaultWorkspaceTools === "function"
      ? deps.defaultWorkspaceTools
      : () => defaultWorkspaceTools(deps);
    const model = typeof deps.defaultWorkspaceModel === "function"
      ? deps.defaultWorkspaceModel
      : defaultWorkspaceModel;

    return {
      ...baseDefaults,
      ...(sourceDefaults[sourceType] || sourceDefaults.repo),
      nodes: nodes(sourceType),
      agents: agents(sourceType),
      tools: tools(),
      model: model(),
    };
  }

  window.WorkspaceDefaults = {
    defaultWorkspaceAgents,
    defaultWorkspaceForm,
    defaultWorkspaceModel,
    defaultWorkspaceNodes,
    defaultWorkspaceTools,
    recommendedAgentRoleIds,
    recommendedAgentTemplateByRole,
    recommendedAgentTemplatesForSource,
    workspaceAgentLibraryTemplates,
  };
})();
