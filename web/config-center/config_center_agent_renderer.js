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

  function renderManageAgentModule(deps = {}) {
    const list = element(deps, "manageAgentList");
    const editor = element(deps, "manageAgentEditor");
    const agentDefinitions = listFor(fn(deps, "agentDefinitions", () => [])());
    if (!fn(deps, "selectedGlobalAgent", () => null)() && agentDefinitions.length) {
      const agentId = agentDefinitions[0].id;
      fn(deps, "setSelectedGlobalAgentId", () => {})(agentId);
      const storageKeys = fn(deps, "storageKeys", () => ({}))();
      fn(deps, "saveStoredValue", () => {})(storageKeys.selectedGlobalAgent, agentId);
    }
    const rawDraft = fn(deps, "agentDefinitionDraft", () => ({}))();
    const normalizeAgentDraft = fn(deps, "normalizeGlobalAgentDefinitionDraft", (value) => value || {});
    if (!rawDraft.id && fn(deps, "selectedGlobalAgent", () => null)()) {
      fn(deps, "setAgentDefinitionDraft", () => {})(normalizeAgentDraft(fn(deps, "selectedGlobalAgent", () => null)()));
    }
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const selectedGlobalAgentId = fn(deps, "selectedGlobalAgentId", () => "")();
    const globalAgentHealth = fn(deps, "globalAgentHealth", () => ({}));
    const globalAgentHealthBadgeMarkup = fn(deps, "globalAgentHealthBadgeMarkup", () => "");
    const globalAgentHealthWarningMarkup = fn(deps, "globalAgentHealthWarningMarkup", () => "");
    if (list) {
      list.innerHTML = agentDefinitions.length
        ? agentDefinitions.map((agent) => {
            const active = agent.id === selectedGlobalAgentId ? " active" : "";
            const health = globalAgentHealth(agent);
            return `
            <button class="workspace-template-item${active}" type="button" data-action="select-global-agent" data-agent-id="${escapeHtml(agent.id)}" title="选择这个全局 Agent 定义，编辑后会影响引用它的新模板快照">
              <div class="workspace-template-item-head">
                <strong>${escapeHtml(agent.name || agent.id)}</strong>
                ${globalAgentHealthBadgeMarkup(health)}
              </div>
              <div class="workspace-template-item-meta">${escapeHtml(agent.role || agent.id)} · ${escapeHtml((agent.tools || []).length)} 个工具</div>
              <div class="workspace-template-item-desc">${escapeHtml(agent.description || agent.prompt || "未填写描述")}</div>
            </button>
          `;
          }).join("")
        : '<div class="empty">还没有全局 Agent。</div>';
    }
    if (!editor) return;
    const nextRawDraft = fn(deps, "agentDefinitionDraft", () => ({}))();
    const agent = nextRawDraft && Object.keys(nextRawDraft).length
      ? normalizeAgentDraft(nextRawDraft)
      : null;
    if (!agent) {
      editor.innerHTML = '<div class="empty">选择一个 Agent 后在这里编辑。</div>';
      return;
    }
    const providerProfiles = listFor(fn(deps, "providerProfiles", () => [])());
    const providerProfileKind = fn(deps, "providerProfileKind", () => "");
    const providerProfileLabel = fn(deps, "providerProfileLabel", (profile) => profile?.name || profile?.id || "");
    const manageAgentDebug = fn(deps, "manageAgentDebug", () => ({}))() || {};
    const workflowTemplates = listFor(fn(deps, "workflowTemplates", () => [])());
    const selectedWorkflowTemplateId = fn(deps, "selectedWorkflowTemplateId", () => "")();
    const workspaceAgentDebugResultMarkup = fn(deps, "workspaceAgentDebugResultMarkup", () => "");
    const health = globalAgentHealth(agent, { rawToolIds: nextRawDraft?.tools || agent.tools || [] });
    editor.innerHTML = `
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(agent.name || agent.id)}</h4>
          <p class="muted">全局角色库。模板节点通过 handler.agent_id 引用这里的定义。</p>
        </div>
        <div class="workspace-node-editor-actions">
          ${globalAgentHealthBadgeMarkup(health)}
          <button class="secondary mini" type="button" data-action="save-global-agent" title="保存当前全局 Agent 定义，供模板节点引用">保存 Agent</button>
          <button class="secondary mini danger" type="button" data-action="delete-global-agent" title="删除当前全局 Agent 定义；已创建实例的快照不会被直接删除">删除 Agent</button>
        </div>
      </div>
      ${globalAgentHealthWarningMarkup(health)}
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>基础信息</strong>
          <span class="muted">ID、显示名、角色和 Provider 覆盖。</span>
        </div>
        <div class="workspace-agent-editor-grid">
          <label>
            Agent ID
            <input data-manage-agent-field="id" value="${escapeHtml(agent.id || "")}" placeholder="planner" />
          </label>
          <label>
            显示名
            <input data-manage-agent-field="name" value="${escapeHtml(agent.name || "")}" placeholder="Planner" />
          </label>
          <label>
            角色
            <input data-manage-agent-field="role" value="${escapeHtml(agent.role || "")}" placeholder="planner" />
          </label>
          <label>
            Provider Profile 覆盖
            <select data-manage-agent-field="provider_profile_id">
              <option value="">未覆盖</option>
              ${providerProfiles.filter((profile) => providerProfileKind(profile) === "llm").map((profile) => `<option value="${escapeHtml(profile.id)}" ${profile.id === agent.provider_profile_id ? "selected" : ""}>${escapeHtml(providerProfileLabel(profile))}</option>`).join("")}
            </select>
          </label>
        </div>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>能力边界</strong>
          <span class="muted">说明用途，并明确允许调用哪些工具。</span>
        </div>
        <label>
          描述
          <textarea data-manage-agent-field="description" rows="2" placeholder="这个 Agent 在全局库中的职责">${escapeHtml(agent.description || "")}</textarea>
        </label>
        <label>
          工具 allowlist
          <textarea data-manage-agent-field="tools" rows="2" placeholder="逗号分隔 tool id">${escapeHtml((agent.tools || []).join(", "))}</textarea>
        </label>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>运行边界</strong>
          <span class="muted">作为节点未覆盖时的全局默认值。</span>
        </div>
        <div class="workspace-agent-editor-grid">
          <label>
            最大迭代
            <input data-manage-agent-number="max_iterations" type="number" min="1" step="1" value="${escapeHtml(agent.max_iterations || "")}" placeholder="默认 10" />
          </label>
          <label>
            超时秒数
            <input data-manage-agent-number="timeout_seconds" type="number" min="1" step="1" value="${escapeHtml(agent.timeout_seconds || "")}" placeholder="不限制" />
          </label>
          <label>
            输出格式
            <select data-manage-agent-field="output_format">
              <option value="" ${agent.output_format ? "" : "selected"}>跟随节点</option>
              <option value="text" ${agent.output_format === "text" ? "selected" : ""}>text</option>
              <option value="json" ${agent.output_format === "json" ? "selected" : ""}>json</option>
            </select>
          </label>
        </div>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>系统提示词</strong>
          <span class="muted">保留完整 Prompt，但控制高度和节奏。</span>
        </div>
        <label>
          Prompt
          <textarea data-manage-agent-field="prompt" rows="7" placeholder="给这个 Agent 的系统提示词">${escapeHtml(agent.prompt || "")}</textarea>
        </label>
        <label class="check">
          <input data-manage-agent-checkbox="enabled" type="checkbox" ${agent.enabled === false ? "" : "checked"} />
          启用这个 Agent
        </label>
      </section>
    </div>
    <div class="workspace-agent-debug-panel">
      <div class="workspace-agent-debug-toolbar">
        <strong>Agent 调试</strong>
        <label class="check compact">
          <input id="manageAgentDebugExecuteLlm" type="checkbox" ${manageAgentDebug.executeLlm ? "checked" : ""} />
          调用 AI/工具
        </label>
        <button class="primary mini" type="button" data-action="run-global-agent-debug" title="用当前模板上下文和输入调试这个全局 Agent，不提交任务队列">${manageAgentDebug.busy ? "调试中..." : "运行调试"}</button>
      </div>
      <label>
        模板上下文
        <select id="manageAgentDebugTemplateSelect">
          <option value="">无模板上下文</option>
          ${workflowTemplates.map((template) => `<option value="${escapeHtml(template.id)}" ${template.id === (manageAgentDebug.templateId || selectedWorkflowTemplateId) ? "selected" : ""}>${escapeHtml(template.name || template.id)}</option>`).join("")}
        </select>
      </label>
      <label>
        调试输入
        <textarea id="manageAgentDebugInput" rows="4" placeholder="例如：请判断这个 repo 复现任务下一步应该怎么拆解和使用哪些工具">${escapeHtml(manageAgentDebug.input || "")}</textarea>
      </label>
      ${manageAgentDebug.error ? `<p class="form-message error">${escapeHtml(manageAgentDebug.error)}</p>` : ""}
      ${manageAgentDebug.result?.debug
        ? workspaceAgentDebugResultMarkup(manageAgentDebug.result.debug, { scope: "manage" })
        : '<div class="empty">输入一段任务描述后，调试结果会显示在这里。</div>'}
    </div>
  `;
  }

  window.ConfigCenterAgentRenderer = {
    renderManageAgentModule,
  };
})();
