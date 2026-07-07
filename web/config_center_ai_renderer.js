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

  function renderManageAiModule(deps = {}) {
    const list = element(deps, "manageProviderProfileList");
    const editor = element(deps, "manageAiEditor");
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const providerProfiles = listFor(fn(deps, "providerProfiles", () => [])());
    const selectedProviderProfileId = fn(deps, "selectedProviderProfileId", () => "")();
    const providerProfileKind = fn(deps, "providerProfileKind", () => "");
    const providerProfileIsValid = fn(deps, "providerProfileIsValid", () => false);
    const providerProfileRequiresApiKey = fn(deps, "providerProfileRequiresApiKey", () => true);
    const providerProfileLabel = fn(deps, "providerProfileLabel", (profile) => profile?.label || profile?.id || "");
    const searchProviderOption = fn(deps, "searchProviderOption", () => ({}));
    const providerVendorOptions = listFor(fn(deps, "providerVendorOptions", () => [])());

    if (list) {
      list.innerHTML = providerProfiles.length
        ? providerProfiles.map((profile) => {
          const active = profile.id === selectedProviderProfileId ? " active" : "";
          const kind = providerProfileKind(profile);
          const vendorLabel = kind === "search"
            ? searchProviderOption(profile.vendor).label || profile.vendor || "Search"
            : providerVendorOptions.find((item) => item.value === profile.vendor)?.label || profile.vendor || "custom";
          const meta = kind === "search"
            ? `${providerProfileIsValid(profile) ? "搜索接入可用" : "搜索接入待配置"}${profile.is_default ? " · 默认" : ""}`
            : `${profile.model || "未填 model"}${profile.is_default ? " · 默认" : ""}`;
          return `
            <button class="workspace-template-item${active}" type="button" data-action="select-provider-profile" data-profile-id="${escapeHtml(profile.id)}" title="选择这个 Provider Profile，编辑模型接入和默认路由">
              <div class="workspace-template-item-head">
                <strong>${escapeHtml(profile.label || "(未命名)")}</strong>
                <span class="server-badge subtle">${escapeHtml(kind === "search" ? "Search" : "LLM")}</span>
                <span class="server-badge subtle">${escapeHtml(vendorLabel)}</span>${profile.is_new ? '<span class="server-badge">草稿</span>' : ""}
              </div>
              <div class="workspace-template-item-meta">${escapeHtml(meta)}</div>
              <div class="workspace-template-item-desc">${escapeHtml(profile.base_url || "默认 base URL")}</div>
            </button>
          `;
        }).join("")
        : '<div class="empty">还没有 Provider Profile。</div>';
    }

    if (!editor) return;

    const profile = fn(deps, "selectedProviderProfile", () => null)();
    const profileKind = providerProfileKind(profile || {});
    const isSearchProfile = profileKind === "search";
    const searchOption = searchProviderOption(profile?.vendor || "");
    const normalizeWorkflowTemplateDraft = fn(deps, "normalizeWorkflowTemplateDraft", (value) => value || {});
    const workflowTemplateDraft = fn(deps, "workflowTemplateDraft", () => null)();
    const selectedWorkflowTemplate = fn(deps, "selectedWorkflowTemplate", () => null)();
    const defaultWorkflowTemplateDraft = fn(deps, "defaultWorkflowTemplateDraft", () => ({}));
    const draft = normalizeWorkflowTemplateDraft(
      workflowTemplateDraft || selectedWorkflowTemplate || defaultWorkflowTemplateDraft("repo"),
    );
    const providerRouteHealthMarkup = fn(deps, "providerRouteHealthMarkup", () => "");
    const searchProviderOptionsMarkup = fn(deps, "searchProviderOptionsMarkup", () => "");
    const providerVendorOptionsMarkup = fn(deps, "providerVendorOptionsMarkup", () => "");
    const providerAvailableModels = listFor(fn(deps, "providerAvailableModels", () => [])());
    const providerKeyVisible = Boolean(fn(deps, "providerKeyVisible", () => false)());
    const providerTestResult = fn(deps, "providerTestResult", () => null)();
    const agentDefinitions = listFor(fn(deps, "agentDefinitions", () => [])());

    editor.innerHTML = `
    ${providerRouteHealthMarkup()}
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(profile?.label || "Provider Profile")}</h4>
          <p class="muted">这里管理全局模型接入信息，以及当前模板的默认路由。</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="test-provider-profile" title="用当前接入信息向模型发一个最小请求，验证连通性（不需要先保存）">测试连接</button>
          <button class="secondary mini" type="button" data-action="save-provider-profile" title="保存当前 Provider Profile 接入配置">保存 Profile</button>
          ${profile ? '<button class="secondary mini danger" type="button" data-action="delete-provider-profile-manage" title="删除当前 Provider Profile，并清理相关路由引用">删除 Profile</button>' : ""}
        </div>
      </div>
      ${profile ? `
        <section class="workspace-manage-group">
          <div class="workspace-manage-group-head">
            <strong>接入信息</strong>
            <span class="muted">${isSearchProfile ? "Search Profile 供 web.search 安全测试和 Agent 搜索工具使用。" : "选厂商会自动填 Base URL；模型可点“拉取”从端点获取，标红为必填。"}</span>
          </div>
          <div class="workspace-provider-editor-grid">
            <label>
              显示名
              <input data-manage-provider-field="label" class="${String(profile.label || "").trim() ? "" : "invalid"}" value="${escapeHtml(profile.label || "")}" placeholder="必填，如 DeepSeek 主号" />
            </label>
            <label>
              类型
              <select data-manage-provider-field="kind">
                <option value="llm" ${profileKind === "llm" ? "selected" : ""}>LLM</option>
                <option value="search" ${profileKind === "search" ? "selected" : ""}>Search</option>
              </select>
            </label>
            ${isSearchProfile ? `
              <label>
                Search Provider
                <select data-manage-provider-field="vendor" class="${String(profile.vendor || "").trim() ? "" : "invalid"}">
                  ${searchProviderOptionsMarkup(profile.vendor)}
                </select>
              </label>
              <label>
                Endpoint / Base URL
                <input data-manage-provider-field="base_url" class="${searchOption.endpoint_required && !String(profile.base_url || "").trim() ? "invalid" : ""}" value="${escapeHtml(profile.base_url || "")}" placeholder="${searchOption.endpoint_required ? "必填，如 https://search.example.com?q={query}" : "可选，留空使用默认端点"}" />
              </label>
            ` : `
            <label>
              厂商
              <select data-manage-provider-field="vendor" class="${String(profile.vendor || "").trim() ? "" : "invalid"}">
                ${providerVendorOptionsMarkup(profile.vendor)}
              </select>
            </label>
            <label>
              Base URL
              <input data-manage-provider-field="base_url" class="${String(profile.base_url || "").trim() ? "" : "invalid"}" value="${escapeHtml(profile.base_url || "")}" placeholder="必填，如 https://api.deepseek.com/v1" />
            </label>
            <label>
              Model
              <span class="provider-model-row">
                <input data-manage-provider-field="model" class="${String(profile.model || "").trim() ? "" : "invalid"}" value="${escapeHtml(profile.model || "")}" placeholder="必填，如 deepseek-chat" list="providerModelOptions" />
                <button type="button" class="mini" data-action="fetch-provider-models" title="从端点 GET /models 拉取可用模型列表">拉取</button>
              </span>
            </label>
            `}
          </div>
          ${isSearchProfile ? "" : `<datalist id="providerModelOptions">${providerAvailableModels.map((m) => `<option value="${escapeHtml(m)}">`).join("")}</datalist>`}
          <label class="provider-key-field">
            API Key
            <span class="provider-key-row">
              <input data-manage-provider-field="api_key" class="${providerProfileRequiresApiKey(profile) && !String(profile.api_key || "").trim() && !profile.has_api_key ? "invalid" : ""}" type="${providerKeyVisible ? "text" : "password"}" value="${escapeHtml(profile.api_key || "")}" placeholder="${providerProfileRequiresApiKey(profile) ? (profile.api_key_masked ? `已保存 ${profile.api_key_masked}，输入新值覆盖` : "必填 sk-...") : (isSearchProfile ? "当前搜索 provider 可免密" : "本地免密，可留空")}" autocomplete="off" />
              <button type="button" class="provider-key-toggle mini" data-action="toggle-provider-key-visibility">${providerKeyVisible ? "隐藏" : "显示"}</button>
            </span>
          </label>
          <label class="check">
            <input data-manage-provider-checkbox="is_default" type="checkbox" ${profile.is_default ? "checked" : ""} />
            设为当前类型默认 Profile
          </label>
          ${providerTestResult ? `<p class="provider-test-result ${providerTestResult.isError ? "error" : "ok"}">${escapeHtml(providerTestResult.text)}${(providerTestResult.models || []).length ? `<br><span class="muted">点模型名填入：${providerTestResult.models.map((m) => ` <a href="#" data-action="pick-provider-model" data-model="${escapeHtml(m)}">${escapeHtml(m)}</a>`).join("")}</span>` : ""}</p>` : ""}
        </section>
      ` : '<div class="empty">先新增一个 Provider Profile。</div>'}
    </div>
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>当前模板默认路由</h4>
          <p class="muted">正在编辑：${escapeHtml(draft.name || "未命名模板")}</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="save-template-routing" title="把当前 Provider、路由模式和聊天 Agent 保存到模板默认配置">保存模板 AI 路由</button>
        </div>
      </div>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>模板默认路由</strong>
          <span class="muted">这里决定实例默认用哪个 Profile、路由模式和聊天 Agent。</span>
        </div>
        <div class="workspace-provider-editor-grid">
          <label>
            默认 Profile
            <select id="manageAiTemplateProfileSelect">
              <option value="">未选择</option>
              ${providerProfiles.filter((item) => providerProfileKind(item) === "llm").map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === draft.model?.provider_profile_id ? "selected" : ""}>${escapeHtml(providerProfileLabel(item))}</option>`).join("")}
            </select>
          </label>
          <label>
            路由模式
            <select id="manageAiTemplateRoutingSelect">
              <option value="workspace_default" ${draft.model?.routing_mode === "workspace_default" ? "selected" : ""}>workspace_default</option>
              <option value="agent_override" ${draft.model?.routing_mode === "agent_override" ? "selected" : ""}>agent_override</option>
            </select>
          </label>
          <label>
            默认聊天 Agent
            <select id="manageAiTemplateChatAgentSelect">
              <option value="">未选择</option>
              ${agentDefinitions.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === draft.model?.chat_agent_id ? "selected" : ""}>${escapeHtml(item.name || item.id)}</option>`).join("")}
            </select>
          </label>
        </div>
      </section>
    </div>
  `;
  }

  window.ConfigCenterAiRenderer = {
    renderManageAiModule,
  };
})();
