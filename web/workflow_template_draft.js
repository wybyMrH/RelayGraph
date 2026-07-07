(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function defaultDraft(sourceType = "repo", deps = {}) {
    const chainSourceType = fn(deps, "workspaceChainSourceType", (value) =>
      String(value || "idea") === "mixed" ? "idea" : String(value || "idea"),
    )(sourceType);
    const defaults = fn(deps, "defaultWorkspaceForm", () => ({}))(chainSourceType) || {};
    const recipe = {
      enabled: true,
      setup_command: defaults.setup_command || "",
      run_command: defaults.run_command || "",
      report_command: defaults.report_command || "",
      schedule: defaults.schedule || "",
    };
    const nodes = defaults.nodes || [];
    return {
      id: "",
      name: sourceType === "paper"
        ? "Paper 复现默认流"
        : sourceType === "idea" || sourceType === "mixed"
          ? "Idea 探索默认流"
          : "Repo 复现默认流",
      description: "",
      status: "ready",
      brief: "",
      source: {
        type: sourceType,
        repo_url: "",
        repo_ref: "",
        paper_url: "",
        idea_text: "",
      },
      workspace_dir: "",
      env: {
        name: defaults.env_name || "",
        manager: defaults.env_manager || "",
        python: defaults.python_version || "",
      },
      recipes: [recipe],
      model: fn(deps, "defaultWorkspaceModel", () => ({}))(),
      nodes,
      links: fn(deps, "workspaceLinksFromNodes", () => [])(nodes),
      tags: [],
      notes: "",
      version_history: [],
      created_at: "",
      updated_at: "",
    };
  }

  function normalizeDraft(template = {}, deps = {}) {
    const source = template.source && typeof template.source === "object" ? template.source : {};
    const env = template.env && typeof template.env === "object" ? template.env : {};
    const recipes = Array.isArray(template.recipes) ? template.recipes : [];
    const recipe = recipes.find((item) => item && item.enabled !== false) || recipes[0] || {};
    const sourceType = String(source.type || template.source_type || "repo");
    const chainSourceType = fn(deps, "workspaceChainSourceType", (value) =>
      String(value || "idea") === "mixed" ? "idea" : String(value || "idea"),
    )(sourceType);
    const base = defaultDraft(sourceType, deps);
    const nodes = (Array.isArray(template.nodes) && template.nodes.length
      ? template.nodes
      : fn(deps, "buildWorkspaceStarterNodes", () => [])({ source_type: chainSourceType }))
      .map((node, index) => fn(deps, "normalizeWorkspaceDraftNode", (item) => item)(node, index, {
        source_type: chainSourceType,
        repo_url: source.repo_url || "",
        repo_ref: source.repo_ref || "",
        paper_url: source.paper_url || "",
        idea_text: source.idea_text || template.brief || "",
        workspace_dir: template.workspace_dir || "",
        env_name: env.name || "",
        env_manager: env.manager || "",
        python_version: env.python || "",
        setup_command: recipe.setup_command || "",
        run_command: recipe.run_command || "",
        report_command: recipe.report_command || "",
        schedule: recipe.schedule || "",
        notes: template.notes || "",
      }));
    return {
      ...base,
      id: String(template.id || ""),
      name: String(template.name || base.name),
      description: String(template.description || ""),
      status: String(template.status || base.status),
      brief: String(template.brief || ""),
      source: {
        type: sourceType,
        repo_url: String(source.repo_url || ""),
        repo_ref: String(source.repo_ref || ""),
        paper_url: String(source.paper_url || ""),
        idea_text: String(source.idea_text || ""),
      },
      workspace_dir: String(template.workspace_dir || ""),
      env: {
        name: String(env.name || base.env.name || ""),
        manager: String(env.manager || base.env.manager || ""),
        python: String(env.python || base.env.python || ""),
      },
      recipes: [{
        enabled: recipe.enabled !== false,
        setup_command: String(recipe.setup_command || ""),
        run_command: String(recipe.run_command || ""),
        report_command: String(recipe.report_command || ""),
        schedule: String(recipe.schedule || ""),
      }],
      model: fn(deps, "normalizeWorkspaceModelDraft", (model) => model || {})(template.model || base.model),
      nodes,
      links: fn(deps, "workspaceLinksFromNodes", () => [])(nodes),
      tags: fn(deps, "parseTagList", (value) => Array.isArray(value) ? value : [])(template.tags || []),
      notes: String(template.notes || ""),
      version_history: Array.isArray(template.version_history)
        ? template.version_history.map((record) => ({
            ...record,
            id: String(record?.id || ""),
            mode: String(record?.mode || "update"),
            recorded_at: String(record?.recorded_at || ""),
            template_id: String(record?.template_id || ""),
            template_name: String(record?.template_name || ""),
            from_updated_at: String(record?.from_updated_at || ""),
            to_updated_at: String(record?.to_updated_at || ""),
            summary: record?.summary && typeof record.summary === "object" ? { ...record.summary } : {},
            changed_fields: Array.isArray(record?.changed_fields) ? record.changed_fields.map((item) => String(item || "")).filter(Boolean) : [],
            added_nodes: Array.isArray(record?.added_nodes) ? record.added_nodes : [],
            removed_nodes: Array.isArray(record?.removed_nodes) ? record.removed_nodes : [],
            changed_nodes: Array.isArray(record?.changed_nodes) ? record.changed_nodes : [],
            warnings: Array.isArray(record?.warnings) ? record.warnings.map((item) => String(item || "")).filter(Boolean) : [],
          })).filter((record) => record.id || record.recorded_at).slice(0, 20)
        : [],
      created_at: String(template.created_at || ""),
      updated_at: String(template.updated_at || ""),
    };
  }

  function payloadForSave(draftInput = {}, deps = {}) {
    const draft = normalizeDraft(draftInput || {}, deps);
    const recipe = Array.isArray(draft.recipes) ? draft.recipes[0] || {} : {};
    const deepClone = fn(deps, "deepClone", (value, fallback) => value == null ? fallback : JSON.parse(JSON.stringify(value)));
    return {
      id: draft.id || undefined,
      name: draft.name,
      description: draft.description,
      status: draft.status,
      brief: draft.brief,
      source_type: draft.source?.type || "repo",
      repo_url: draft.source?.repo_url || "",
      repo_ref: draft.source?.repo_ref || "",
      paper_url: draft.source?.paper_url || "",
      idea_text: draft.source?.idea_text || "",
      workspace_dir: draft.workspace_dir || "",
      env_name: draft.env?.name || "",
      env_manager: draft.env?.manager || "",
      python_version: draft.env?.python || "",
      setup_command: recipe.setup_command || "",
      run_command: recipe.run_command || "",
      report_command: recipe.report_command || "",
      schedule: recipe.schedule || "",
      model: deepClone(draft.model || {}, {}),
      nodes: deepClone(draft.nodes || [], []),
      links: fn(deps, "workspaceLinksFromNodes", () => [])(draft.nodes || []),
      tags: deepClone(draft.tags || [], []),
      notes: draft.notes || "",
    };
  }

  window.WorkflowTemplateDraft = {
    defaultDraft,
    normalizeDraft,
    payloadForSave,
  };
})();
