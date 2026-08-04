(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function listFor(value) {
    return Array.isArray(value) ? value : [];
  }

  function renderManageToolModule(deps = {}) {
    const list = element(deps, "manageToolList");
    const editor = element(deps, "manageToolEditor");
    const toolDefinitions = listFor(fn(deps, "toolDefinitions", () => [])());
    if (!fn(deps, "selectedGlobalTool", () => null)() && toolDefinitions.length) {
      const toolId = toolDefinitions[0].id;
      fn(deps, "setSelectedGlobalToolId", () => {})(toolId);
      const storageKeys = fn(deps, "storageKeys", () => ({}))();
      fn(deps, "saveStoredValue", () => {})(storageKeys.selectedGlobalTool, toolId);
    }
    const rawDraft = fn(deps, "toolDefinitionDraft", () => ({}))();
    const normalizeToolDraft = fn(deps, "normalizeGlobalToolDefinitionDraft", (value) => value || {});
    if (!rawDraft.id && fn(deps, "selectedGlobalTool", () => null)()) {
      fn(deps, "setToolDefinitionDraft", () => {})(normalizeToolDraft(fn(deps, "selectedGlobalTool", () => null)()));
    }
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const selectedGlobalToolId = fn(deps, "selectedGlobalToolId", () => "")();
    const workspaceToolCategoryLabel = fn(deps, "workspaceToolCategoryLabel", (value) => value);
    const workspaceToolPolicyBadge = fn(deps, "workspaceToolPolicyBadge", () => "");
    if (list) {
      list.innerHTML = toolDefinitions.length
        ? toolDefinitions.map((tool) => {
            const active = tool.id === selectedGlobalToolId ? " active" : "";
            return `
            <button class="workspace-template-item${active}" type="button" data-action="select-global-tool" data-tool-id="${escapeHtml(tool.id)}" title="选择这个全局工具定义，编辑工具类别和能力边界">
              <div class="workspace-template-item-head">
                <strong>${escapeHtml(tool.label || tool.id)}</strong>
                <span class="state ${tool.enabled === false ? "blocked" : "ready"}">${tool.enabled === false ? "停用" : "启用"}</span>
              </div>
              <div class="workspace-template-item-meta">${escapeHtml(workspaceToolCategoryLabel(tool.category || "general"))} · ${escapeHtml(tool.capability || "read")}${tool.side_effect ? ` · ${workspaceToolPolicyBadge(tool.side_effect, tool.side_effect === "mutate_runtime")}` : ""}</div>
              <div class="workspace-template-item-desc">${escapeHtml(tool.description || "未填写描述")}</div>
            </button>
          `;
          }).join("")
        : '<div class="empty">还没有全局工具。</div>';
    }
    if (!editor) return;
    const nextRawDraft = fn(deps, "toolDefinitionDraft", () => ({}))();
    const tool = nextRawDraft && Object.keys(nextRawDraft).length
      ? normalizeToolDraft(nextRawDraft)
      : null;
    if (!tool) {
      editor.innerHTML = '<div class="empty">选择一个工具后在这里编辑。</div>';
      return;
    }
    fn(deps, "ensureToolDefinitionTestState", () => {})(tool);
    const testState = fn(deps, "toolDefinitionTest", () => ({}))();
    const workspaceOptions = [
      { id: "", name: "自动选择最近实例" },
      ...listFor(fn(deps, "workspaces", () => [])()).map((workspace) => ({ id: workspace.id, name: workspace.name || workspace.brief || workspace.id })),
    ];
    const searchProfilesForTool = listFor(fn(deps, "searchProviderProfiles", () => [])());
    const selectedToolSearchProfileId = String(tool.provider_profile_id || fn(deps, "selectedSearchProviderProfileId", () => "")() || "").trim();
    const providerProfileLabel = fn(deps, "providerProfileLabel", (profile) => profile?.name || profile?.id || "");
    const toolTestResultMarkup = fn(deps, "toolTestResultMarkup", () => "");
    editor.innerHTML = `
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(tool.label || tool.id)}</h4>
          <p class="muted">工具边界是全局注册表，Agent 只通过 allowlist 引用。${tool.side_effect ? workspaceToolPolicyBadge(tool.side_effect, tool.side_effect === "mutate_runtime") : ""}</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="save-global-tool" title="保存当前全局工具定义，供 Agent allowlist 引用">保存工具</button>
          <button class="secondary mini danger" type="button" data-action="delete-global-tool" title="删除当前全局工具定义；已创建实例的工具快照不会被直接删除">删除工具</button>
        </div>
      </div>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>基础信息</strong>
          <span class="muted">ID、显示名、类别和能力边界。</span>
        </div>
        <div class="workspace-tool-editor-grid">
          <label>
            Tool ID
            <input data-manage-tool-field="id" value="${escapeHtml(tool.id || "")}" placeholder="repo.inspect" />
          </label>
          <label>
            显示名
            <input data-manage-tool-field="label" value="${escapeHtml(tool.label || "")}" placeholder="Repo Inspect" />
          </label>
          <label>
            类别
            <input data-manage-tool-field="category" value="${escapeHtml(tool.category || "general")}" placeholder="repo / workflow / env" />
          </label>
          <label>
            能力
            <input data-manage-tool-field="capability" value="${escapeHtml(tool.capability || "read")}" placeholder="read / write / execute" />
          </label>
        </div>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>说明与约束</strong>
          <span class="muted">写清楚它擅长什么，以及不该跨过的边界。</span>
        </div>
        <label>
          描述
          <textarea data-manage-tool-field="description" rows="2" placeholder="这个工具擅长做什么">${escapeHtml(tool.description || "")}</textarea>
        </label>
        <label>
          备注
          <textarea data-manage-tool-field="notes" rows="2" placeholder="边界、审批点或使用说明">${escapeHtml(tool.notes || "")}</textarea>
        </label>
        <label class="check">
          <input data-manage-tool-checkbox="enabled" type="checkbox" ${tool.enabled === false ? "" : "checked"} />
          启用这个工具
        </label>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>安全测试</strong>
          <span class="muted">只读工具执行预览；runtime / dangerous 工具不会直接产生副作用。</span>
        </div>
        <div class="workspace-tool-editor-grid">
          <label>
            Workspace 上下文
            <select id="manageToolTestWorkspaceSelect">
              ${workspaceOptions.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === testState.workspaceId ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("")}
            </select>
          </label>
          ${tool.id === "web.search" ? `
            <label>
              Search Provider Profile
              <select id="manageToolSearchProfileSelect">
                <option value="" ${selectedToolSearchProfileId ? "" : "selected"}>自动 / 环境变量 / 种子 fallback</option>
                ${searchProfilesForTool.map((profile) => `<option value="${escapeHtml(profile.id)}" ${profile.id === selectedToolSearchProfileId ? "selected" : ""}>${escapeHtml(providerProfileLabel(profile))}</option>`).join("")}
              </select>
            </label>
          ` : ""}
          <label>
            测试参数
            <textarea id="manageToolTestArguments" rows="4" spellcheck="false">${escapeHtml(testState.argumentsText || "{}")}</textarea>
          </label>
        </div>
        <div class="button-row">
          <button class="secondary mini" type="button" data-action="reset-global-tool-test" title="按工具类型和当前实例重新生成安全测试参数">重置参数</button>
          <button class="primary mini" type="button" data-action="run-global-tool-test" title="调用后端安全测试接口；不会绕过受控任务队列" ${testState.busy ? "disabled" : ""}>${testState.busy ? "测试中..." : "安全测试"}</button>
        </div>
        ${toolTestResultMarkup(testState)}
      </section>
    </div>
  `;
  }

  window.ConfigCenterToolRenderer = {
    renderManageToolModule,
  };
})();
