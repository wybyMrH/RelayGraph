(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function overviewApiFor(deps = {}) {
    return typeof deps.overviewApi === "function" ? deps.overviewApi() : deps.overviewApi;
  }

  function workflowTemplateDraftFor(deps = {}) {
    const draft = fn(deps, "workflowTemplateDraft", () => null)();
    const normalizeDraft = fn(deps, "normalizeWorkflowTemplateDraft", (value) => value || {});
    if (draft && typeof draft === "object" && Object.keys(draft).length) {
      return normalizeDraft(draft);
    }
    const selectedTemplate = fn(deps, "selectedWorkflowTemplate", () => null)();
    if (selectedTemplate) return normalizeDraft(selectedTemplate);
    return fn(deps, "defaultWorkflowTemplateDraft", () => ({}))("repo");
  }

  function studioOverviewCards(deps = {}, draft = {}) {
    const nodes = Array.isArray(draft.nodes) ? draft.nodes : [];
    const automatedNodes = nodes.filter((node) => String(node.handler?.mode || "human") !== "human");
    const assignedNodes = automatedNodes.filter((node) => String(node.handler?.agent_id || "").trim()).length;
    const rawProfiles = fn(deps, "providerProfiles", () => [])();
    const profiles = Array.isArray(rawProfiles) ? rawProfiles : [];
    const configuredProfiles = fn(deps, "configuredProviderProfiles", () => [])(profiles);
    const selectedProfile = fn(deps, "selectedProviderProfile", () => null)();
    const profile = fn(deps, "providerProfileById", () => null)(draft.model?.provider_profile_id || "") || selectedProfile;
    const chatAgent = fn(deps, "globalAgentById", () => null)(draft.model?.chat_agent_id || "");
    const sourceBits = [
      draft.source?.repo_url ? "repo" : "",
      draft.source?.paper_url ? "paper" : "",
      draft.source?.idea_text ? "idea" : "",
      draft.workspace_dir ? "workdir" : "",
    ].filter(Boolean);
    const envBits = [
      draft.env?.manager || "",
      draft.env?.name || "",
      draft.env?.python ? `Python ${draft.env.python}` : "",
    ].filter(Boolean);
    const workspaceSourceTypeLabel = fn(deps, "workspaceSourceTypeLabel", (value) => value);
    const workspaceNodeLabel = fn(deps, "workspaceNodeLabel", (kind) => kind);
    const providerProfileLabel = fn(deps, "providerProfileLabel", (item) => item?.name || item?.id || "");
    return [
      {
        label: "入口类型",
        title: workspaceSourceTypeLabel(draft.source?.type || "idea"),
        detail: sourceBits.length ? sourceBits.join(" · ") : "等待实例输入覆盖默认来源",
        state: sourceBits.length || draft.source?.type === "idea" ? "ready" : "draft",
      },
      {
        label: "节点链",
        title: `${nodes.length} 个节点`,
        detail: `${assignedNodes}/${automatedNodes.length || 0} 自动节点已绑定 Agent · ${nodes[0]?.title || workspaceNodeLabel(nodes[0]?.kind) || "未设置起点"}`,
        state: nodes.length && assignedNodes === automatedNodes.length ? "ready" : nodes.length ? "blocked" : "draft",
      },
      {
        label: "默认环境",
        title: draft.workspace_dir || draft.env?.name || "实例创建时推断",
        detail: envBits.join(" · ") || "后续由 env.infer / path.resolve 补齐",
        state: draft.workspace_dir || draft.env?.name ? "ready" : "draft",
      },
      {
        label: "AI 路由",
        title: profile
          ? providerProfileLabel(profile)
          : configuredProfiles.length
            ? `${configuredProfiles.length} 个 Profile`
            : draft.model?.routing_mode || "未配置",
        detail: chatAgent
          ? `聊天 Agent ${chatAgent.name || chatAgent.id}`
          : configuredProfiles.length
            ? "Profile 已就绪，可在 AI 路由页设模板默认"
            : "先新增 Provider Profile 并填写模型",
        state: configuredProfiles.length ? "ready" : profiles.length ? "blocked" : "draft",
      },
    ];
  }

  function renderStudioOverview(deps = {}) {
    const root = element(deps, "workflowTemplateStudioOverview");
    if (!root) return;
    const draft = workflowTemplateDraftFor(deps);
    const cards = studioOverviewCards(deps, draft);
    root.innerHTML = (overviewApiFor(deps)?.studioCardsMarkup?.({
      cards,
      escapeHtml: deps.escapeHtml,
    }) || "") + fn(deps, "validationMarkup", () => "")() + fn(deps, "versionHistoryMarkup", () => "")(draft);
  }

  window.WorkflowTemplateStudioOverviewRenderer = {
    renderStudioOverview,
    studioOverviewCards,
    workflowTemplateDraftFor,
  };
})();
