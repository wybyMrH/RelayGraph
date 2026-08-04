(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function selectedTemplateId(callbacks = {}) {
    return String(fn(callbacks, "selectedTemplateId", () => "")() || "");
  }

  function previewTemplateId(callbacks = {}) {
    return selectedTemplateId(callbacks).trim();
  }

  function setMessage(callbacks, message = "", isError = false) {
    fn(callbacks, "setMessage", () => {})(message, isError);
  }

  async function previewTemplate(options = {}, callbacks = {}) {
    const payload = fn(callbacks, "payloadForSave", () => ({}))();
    const templateId = previewTemplateId(callbacks);
    fn(callbacks, "setValidationBusy", () => {})(true);
    if (options.render !== false) fn(callbacks, "renderStudioOverview", () => {})();
    try {
      const response = await fn(callbacks, "fetchJson", async () => ({}))(
        templateId
          ? `/api/workflow-templates/${encodeURIComponent(templateId)}/preview`
          : "/api/workflow-templates/preview",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      fn(callbacks, "setValidation", () => {})(response);
      return response;
    } finally {
      fn(callbacks, "setValidationBusy", () => {})(false);
      if (options.render !== false) fn(callbacks, "renderWorkbench", () => {})();
    }
  }

  async function saveTemplate(callbacks = {}) {
    const payload = fn(callbacks, "payloadForSave", () => ({}))();
    setMessage(callbacks, "正在校验模板...");
    try {
      const preview = await fn(callbacks, "previewTemplate", async () => null)({ render: false });
      const validation = preview?.validation || {};
      if (validation.status === "blocked") {
        fn(callbacks, "renderWorkbench", () => {})();
        setMessage(callbacks, `模板校验未通过：${fn(callbacks, "validationSummary", () => "等待后端校验")(validation)}`, true);
        return null;
      }
      const templateId = selectedTemplateId(callbacks);
      setMessage(callbacks, templateId ? "正在保存模板..." : "正在创建模板...");
      const response = await fn(callbacks, "fetchJson", async () => ({}))(
        templateId
          ? `/api/workflow-templates/${encodeURIComponent(templateId)}`
          : "/api/workflow-templates",
        {
          method: templateId ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      const saved = response.workflow_template;
      await fn(callbacks, "loadStatus", async () => {})(true, { renderWorkspace: true });
      if (saved?.id) fn(callbacks, "selectTemplate", () => {})(saved.id);
      let migrationNotice = "";
      const workspaceId = String(fn(callbacks, "selectedWorkspaceId", () => "")() || "");
      if (workspaceId) {
        const diffPayload = await fn(callbacks, "refreshTemplateDiff", async () => null)(workspaceId, {
          quiet: true,
          render: fn(callbacks, "workspaceManageTab", () => "")() === "inspect",
        });
        const diff = diffPayload?.diff && typeof diffPayload.diff === "object" ? diffPayload.diff : null;
        const plan = diff?.migration_plan && typeof diff.migration_plan === "object" ? diff.migration_plan : {};
        if (diff?.status === "changed") {
          migrationNotice = plan.can_manual_apply
            ? "当前实例快照已变化，可在链路诊断应用安全迁移。"
            : plan.can_create_draft
              ? "当前实例快照已变化，建议在链路诊断新建迁移草稿。"
              : "当前实例快照已变化，请在链路诊断复核迁移计划。";
        }
      }
      const saveMessage = validation.status === "warning" ? "模板已保存，但仍有警告项。" : "模板已保存。";
      setMessage(callbacks, `${saveMessage}${migrationNotice ? ` ${migrationNotice}` : ""}`);
      return response;
    } catch (error) {
      setMessage(callbacks, error.message, true);
      return null;
    }
  }

  async function deleteTemplate(callbacks = {}) {
    const templateId = selectedTemplateId(callbacks);
    if (!templateId) {
      fn(callbacks, "newTemplate", () => {})("repo");
      return null;
    }
    const template = fn(callbacks, "selectedTemplate", () => null)();
    const confirmed = !template || fn(callbacks, "confirmAction", () => true)(
      `确定删除模板 "${template.name || template.id}" 吗？`,
    );
    if (!confirmed) return null;
    try {
      await fn(callbacks, "fetchJson", async () => ({}))(
        `/api/workflow-templates/${encodeURIComponent(templateId)}`,
        { method: "DELETE" },
      );
      await fn(callbacks, "loadStatus", async () => {})(true, { renderWorkspace: true });
      const templates = fn(callbacks, "workflowTemplates", () => [])();
      if (templates[0]) fn(callbacks, "selectTemplate", () => {})(templates[0].id);
      else fn(callbacks, "newTemplate", () => {})("repo");
      const workspaceId = String(fn(callbacks, "selectedWorkspaceId", () => "")() || "");
      if (workspaceId) {
        void fn(callbacks, "refreshTemplateDiff", async () => null)(workspaceId, {
          quiet: true,
          render: fn(callbacks, "workspaceManageTab", () => "")() === "inspect",
        });
      }
      setMessage(callbacks, "模板已删除。");
      return true;
    } catch (error) {
      setMessage(callbacks, error.message, true);
      return null;
    }
  }

  window.WorkflowTemplateLifecycleActions = {
    deleteTemplate,
    previewTemplate,
    saveTemplate,
  };
})();
