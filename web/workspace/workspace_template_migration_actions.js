(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function selectedWorkspace(callbacks) {
    return fn(callbacks, "selectedWorkspace", () => null)() || null;
  }

  function cachedDiff(callbacks, workspaceId = "") {
    const cached = fn(callbacks, "cachedDiff", () => null)() || {};
    const matches = String(cached.workspaceId || "") === String(workspaceId || "");
    return {
      matches,
      payload: matches ? cached.payload : null,
    };
  }

  async function refreshDiffPayload(callbacks, workspace, options = {}) {
    const workspaceId = String(workspace?.id || "").trim();
    if (!workspaceId) return null;
    return await fn(callbacks, "refreshWorkspaceTemplateDiff", async () => null)(workspaceId, {
      quiet: options.quiet !== false,
      render: options.render !== false,
    });
  }

  function setMessage(callbacks, message, isError = false) {
    fn(callbacks, "setWorkspaceManageMessage", () => {})(message, isError);
  }

  async function copyPlan(callbacks = {}) {
    const workspace = selectedWorkspace(callbacks);
    if (!workspace?.id) {
      setMessage(callbacks, "先选择一个实例，再复制模板迁移计划。", true);
      return;
    }
    let payload = cachedDiff(callbacks, workspace.id).payload;
    if (!payload?.diff?.migration_plan) {
      payload = await refreshDiffPayload(callbacks, workspace, { quiet: true, render: true });
    }
    const plan = payload?.diff?.migration_plan;
    if (!plan) {
      setMessage(callbacks, "还没有可复制的模板迁移计划。", true);
      return;
    }
    await fn(callbacks, "copyTextToClipboard", async () => {})(
      JSON.stringify(
        {
          schema: "relaygraph.workflow_template.migration_plan.copy.v1",
          workspace_id: workspace.id,
          workspace_name: workspace.name || "",
          template_id: payload.template_id || workspace.template_id || "",
          template_name: payload.template_name || workspace.template_name || "",
          diff_summary: payload.diff?.summary || {},
          migration_plan: plan,
        },
        null,
        2,
      ),
    );
    setMessage(callbacks, "模板迁移计划 JSON 已复制。");
  }

  async function applyMigration(callbacks = {}) {
    const workspace = selectedWorkspace(callbacks);
    if (!workspace?.id) {
      setMessage(callbacks, "先选择一个实例，再应用模板迁移。", true);
      return null;
    }
    const cached = cachedDiff(callbacks, workspace.id);
    const payload = cached.matches
      ? cached.payload
      : await refreshDiffPayload(callbacks, workspace, { quiet: true, render: true });
    const plan = payload?.diff?.migration_plan;
    if (!plan?.can_manual_apply) {
      setMessage(callbacks, "当前模板差异包含结构性变化，请新建实例或人工重建。", true);
      return null;
    }
    const confirmed = fn(callbacks, "confirmAction", (message) => window.confirm(message))(
      "应用当前模板的安全迁移？会更新此实例的模板派生字段，并保留运行记录与迁移历史。运行前仍需重新通过链路诊断和执行包 gate。",
    );
    if (!confirmed) return null;

    const response = await fn(callbacks, "fetchJson", async () => ({}))(
      `/api/workspaces/${encodeURIComponent(workspace.id)}/template-migration/apply`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
      },
    );
    const merged = fn(callbacks, "mergeWorkspaceExecutionResultPayload", () => null)(workspace.id, response)
      || response.workspace
      || workspace;
    fn(callbacks, "setWorkspaceTemplateDiff", () => {})({
      workspaceId: workspace.id,
      busy: false,
      error: "",
      payload: {
        workspace_id: workspace.id,
        template_id: response.template_id || response.workspace?.template_id || merged.template_id || "",
        template_name: response.template_name || response.workspace?.template_name || merged.template_name || "",
        diff: response.diff || null,
      },
    });
    fn(callbacks, "selectWorkspace", () => {})(workspace.id, {
      persist: true,
      selectedNodeId: fn(callbacks, "selectedWorkspaceNodeId", () => "")(),
      selectedExecutionNodeId: fn(callbacks, "selectedWorkspaceExecutionNodeId", () => "")(),
      refreshCockpit: true,
    });
    setMessage(callbacks, "模板安全迁移已应用。请重新检查链路诊断和执行包 readiness gate。");
    return response;
  }

  async function createDraft(callbacks = {}) {
    const workspace = selectedWorkspace(callbacks);
    if (!workspace?.id) {
      setMessage(callbacks, "先选择一个实例，再创建迁移草稿。", true);
      return null;
    }
    const cached = cachedDiff(callbacks, workspace.id);
    const payload = cached.matches
      ? cached.payload
      : await refreshDiffPayload(callbacks, workspace, { quiet: true, render: true });
    const plan = payload?.diff?.migration_plan;
    if (!plan?.can_create_draft) {
      setMessage(callbacks, "当前模板差异不需要迁移草稿。", true);
      return null;
    }
    const confirmed = fn(callbacks, "confirmAction", (message) => window.confirm(message))(
      "从当前实例输入和当前模板创建一个新的迁移草稿？旧实例、运行记录和任务不会被修改。",
    );
    if (!confirmed) return null;

    const response = await fn(callbacks, "fetchJson", async () => ({}))(
      `/api/workspaces/${encodeURIComponent(workspace.id)}/template-migration/create-draft`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
      },
    );
    const draft = response.workspace && typeof response.workspace === "object" ? response.workspace : null;
    if (draft?.id) {
      fn(callbacks, "upsertWorkspaceInState", () => {})(draft);
      fn(callbacks, "setWorkspaceTemplateDiff", () => {})({
        workspaceId: draft.id,
        busy: false,
        error: "",
        payload: {
          workspace_id: draft.id,
          template_id: draft.template_id || "",
          template_name: draft.template_name || "",
          diff: response.diff || null,
        },
      });
      fn(callbacks, "selectWorkspace", () => {})(draft.id, { persist: true, refreshCockpit: true });
    } else {
      await fn(callbacks, "loadStatus", async () => {})(true, { renderWorkspace: true });
    }
    setMessage(callbacks, "迁移草稿已创建。请在新实例里重新检查链路诊断和执行包 readiness gate。");
    return response;
  }

  window.WorkspaceTemplateMigrationActions = {
    applyMigration,
    copyPlan,
    createDraft,
  };
})();
