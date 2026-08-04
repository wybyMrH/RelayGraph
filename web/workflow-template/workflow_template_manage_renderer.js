(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function draftFor(deps = {}) {
    const workflowTemplateDraft = fn(deps, "workflowTemplateDraft", () => null)();
    const normalizeWorkflowTemplateDraft = fn(deps, "normalizeWorkflowTemplateDraft", (value) => value || {});
    if (workflowTemplateDraft && typeof workflowTemplateDraft === "object" && Object.keys(workflowTemplateDraft).length) {
      return normalizeWorkflowTemplateDraft(workflowTemplateDraft);
    }
    const selectedWorkflowTemplate = fn(deps, "selectedWorkflowTemplate", () => null)();
    if (selectedWorkflowTemplate) return normalizeWorkflowTemplateDraft(selectedWorkflowTemplate);
    return fn(deps, "defaultWorkflowTemplateDraft", () => ({}))("repo");
  }

  function setElementText(deps, id, text) {
    const target = element(deps, id);
    if (target) target.textContent = text;
  }

  function setElementValue(deps, id, value) {
    const target = element(deps, id);
    if (target) target.value = value;
  }

  function setElementOptions(deps, id, markup, value) {
    const target = element(deps, id);
    if (!target) return;
    target.innerHTML = markup;
    target.value = value;
  }

  function renderManageTemplateModule(deps = {}) {
    const draft = draftFor(deps);
    fn(deps, "setWorkflowTemplateDraft", () => {})(draft);
    const nodes = Array.isArray(draft.nodes) ? draft.nodes : [];
    const selectedTemplateNodeId = fn(deps, "selectedTemplateNodeId", () => "")();
    if (!selectedTemplateNodeId || !nodes.some((node) => node.id === selectedTemplateNodeId)) {
      fn(deps, "setSelectedTemplateNodeId", () => {})(nodes[0]?.id || "");
    }
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const providerProfiles = fn(deps, "providerProfiles", () => [])();
    const agentDefinitions = fn(deps, "agentDefinitions", () => [])();
    const providerProfileKind = fn(deps, "providerProfileKind", () => "");
    const providerProfileLabel = fn(deps, "providerProfileLabel", (profile) => profile?.name || profile?.id || "");
    setElementText(deps, "workflowTemplateTitle", draft.name || "工作流模板");
    setElementText(deps, "workflowTemplateMeta", `${draft.source?.type || "repo"} · ${nodes.length} 个节点 · ${draft.tags.length} 个标签`);
    setElementValue(deps, "templateNameInput", draft.name || "");
    setElementValue(deps, "templateSourceTypeSelect", draft.source?.type || "repo");
    setElementValue(deps, "templateStatusSelect", draft.status || "ready");
    setElementValue(deps, "templateTagsInput", (draft.tags || []).join(","));
    setElementValue(deps, "templateDescriptionInput", draft.description || "");
    setElementValue(deps, "templateBriefInput", draft.brief || "");
    setElementValue(deps, "templateRepoUrlInput", draft.source?.repo_url || "");
    setElementValue(deps, "templateRepoRefInput", draft.source?.repo_ref || "");
    setElementValue(deps, "templatePaperUrlInput", draft.source?.paper_url || "");
    setElementValue(deps, "templateWorkspaceDirInput", draft.workspace_dir || "");
    setElementValue(deps, "templateIdeaInput", draft.source?.idea_text || "");
    setElementValue(deps, "templateEnvNameInput", draft.env?.name || "");
    setElementValue(deps, "templateEnvManagerSelect", draft.env?.manager || "");
    setElementValue(deps, "templatePythonVersionInput", draft.env?.python || "");
    setElementOptions(
      deps,
      "templateProviderProfileSelect",
      `<option value="">未选择</option>${providerProfiles.filter((profile) => providerProfileKind(profile) === "llm").map((profile) => `<option value="${escapeHtml(profile.id)}">${escapeHtml(providerProfileLabel(profile))}</option>`).join("")}`,
      draft.model?.provider_profile_id || "",
    );
    setElementValue(deps, "templateRoutingModeSelect", draft.model?.routing_mode || "workspace_default");
    setElementOptions(
      deps,
      "templateChatAgentSelect",
      `<option value="">未选择</option>${agentDefinitions.map((agent) => `<option value="${escapeHtml(agent.id)}">${escapeHtml(agent.name || agent.id)}</option>`).join("")}`,
      draft.model?.chat_agent_id || "",
    );
    fn(deps, "renderWorkflowTemplateStudioOverview", () => {})();
    fn(deps, "renderManageTemplateList", () => {})();
    fn(deps, "renderWorkflowTemplateCanvas", () => {})();
    fn(deps, "renderWorkflowTemplateNodeList", () => {})();
    fn(deps, "renderWorkflowTemplateNodeEditor", () => {})();
  }

  window.WorkflowTemplateManageRenderer = {
    draftFor,
    renderManageTemplateModule,
  };
})();
