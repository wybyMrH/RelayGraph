(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function templateById(templates = [], templateId = "") {
    const id = String(templateId || "").trim();
    return (Array.isArray(templates) ? templates : []).find((template) => String(template?.id || "") === id) || null;
  }

  function firstNodeId(draft = {}) {
    return Array.isArray(draft?.nodes) ? draft.nodes[0]?.id || "" : "";
  }

  function normalizeDraft(template = {}, deps = {}) {
    return fn(deps, "normalizeWorkflowTemplateDraft", (value) => value || {})(template || {});
  }

  function newDraftState(sourceType = "repo", deps = {}) {
    const draft = normalizeDraft(
      fn(deps, "defaultWorkflowTemplateDraft", () => ({}))(sourceType),
      deps,
    );
    return {
      selectedTemplateId: "",
      workflowTemplateDraft: draft,
      workflowTemplateValidation: null,
      selectedTemplateNodeId: firstNodeId(draft),
      workflowTemplateDirty: true,
      workflowTemplateNodeSearch: "",
    };
  }

  function selectTemplateState(options = {}, deps = {}) {
    const template = templateById(options.templates, options.templateId);
    if (!template) return { ok: false, template: null };
    const changed = String(options.currentSelectedTemplateId || "") !== String(template.id || "");
    const draft = normalizeDraft(template, deps);
    const selectedTemplateNodeId = String(options.options?.selectedNodeId || firstNodeId(draft) || "").trim();
    return {
      ok: true,
      template,
      changed,
      selectedTemplateId: template.id,
      workflowTemplateDraft: draft,
      workflowTemplateValidation: null,
      selectedTemplateNodeId,
      workflowTemplateDirty: false,
      resetWorkflowTemplateNodeSearch: changed,
    };
  }

  function updateDraftState(options = {}, deps = {}) {
    const current = normalizeDraft(options.currentDraft || {}, deps);
    const deepClone = fn(deps, "deepClone", (value, fallback) => value == null ? fallback : JSON.parse(JSON.stringify(value)));
    const updater = options.updater;
    const next = typeof updater === "function"
      ? updater(deepClone(current, current))
      : { ...current, ...(updater && typeof updater === "object" ? updater : {}) };
    const draft = normalizeDraft(next, deps);
    let selectedTemplateNodeId = String(options.selectedNodeId || "").trim();
    if (!Array.isArray(draft.nodes) || !draft.nodes.some((node) => node.id === selectedTemplateNodeId)) {
      selectedTemplateNodeId = firstNodeId(draft);
    }
    return {
      workflowTemplateDraft: draft,
      workflowTemplateValidation: null,
      selectedTemplateNodeId,
      workflowTemplateDirty: true,
    };
  }

  window.WorkflowTemplateState = {
    newDraftState,
    selectTemplateState,
    templateById,
    updateDraftState,
  };
})();
