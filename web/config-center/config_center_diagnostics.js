(function () {
  "use strict";

  function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeFor(deps, value) {
    return (typeof deps.escapeHtml === "function" ? deps.escapeHtml : fallbackEscapeHtml)(value);
  }

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function defaultToolTestArguments(options = {}) {
    const tool = options.tool && typeof options.tool === "object" ? options.tool : {};
    const workspace = options.workspace && typeof options.workspace === "object" ? options.workspace : {};
    const toolId = String(tool.id || "").trim();
    const inputs = workspace.inputs && typeof workspace.inputs === "object" ? workspace.inputs : {};
    const source = workspace.source && typeof workspace.source === "object" ? workspace.source : {};
    const goal = String(inputs.goal_text || workspace.brief || source.idea_text || "").trim();
    const workspaceDir = String(workspace.workspace_dir || "").trim();
    const firstRef = Array.isArray(workspace.references) ? String(workspace.references[0] || "").trim() : "";
    const firstRepo = String(source.repo_url || (Array.isArray(inputs.repo_urls) ? inputs.repo_urls[0] : "") || "").trim();
    if (toolId === "web.search") {
      const args = { query: goal || firstRepo || "RelayGraph smoke", limit: 3 };
      const profileId = String(tool.provider_profile_id || options.selectedSearchProviderProfileId || "").trim();
      if (profileId) args.provider_profile_id = profileId;
      return args;
    }
    if (toolId === "repo.search") return { query: goal || firstRepo || "RelayGraph smoke" };
    if (toolId === "file.read") return { path: firstRef || "README.md", limit: 4000 };
    if (toolId === "file.browse" || toolId === "dir.scan") return { path: workspaceDir || ".", max_entries: 24 };
    if (toolId === "repo.read" || toolId === "repo.inspect") return { path: workspaceDir || ".", focus_paths: ["README.md", "requirements.txt"] };
    if (toolId === "path.resolve") return { workspace_dir: workspaceDir || ".", data_roots: [] };
    if (toolId === "dataset.find") return { query: goal || "dataset", data_roots: [] };
    if (toolId === "gpu.inspect" || toolId === "gpu.allocate") return { min_free_memory_gib: 1 };
    if (toolId === "env.inspect" || toolId === "env.infer") return { manifest_paths: ["requirements.txt", "environment.yml"] };
    if (toolId === "artifact.read" || toolId === "artifact.collect") return { artifact_paths: ["runs", "outputs", "logs"] };
    if (toolId === "log.read" || toolId === "execution.package" || toolId === "workflow.plan") return {};
    if (toolId === "job.run" || toolId === "host.exec") return { command: "echo relaygraph-tool-test", cwd: workspaceDir || "." };
    if (toolId === "repo.clone") return { repo_url: firstRepo, workspace_dir: workspaceDir };
    if (toolId === "env.prepare" || toolId === "env.create") return { command: "python --version", env_name: workspace.env?.name || "" };
    if (toolId === "job.stop" || toolId === "job.reorder") return { latest: true };
    return {};
  }

  function toolTestResultMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const testState = options.testState && typeof options.testState === "object" ? options.testState : {};
    if (testState.busy) return '<div class="workspace-agent-debug-warning">正在执行安全测试...</div>';
    if (testState.error) return `<div class="workspace-agent-debug-warning">${escapeFor(deps, testState.error)}</div>`;
    const result = testState.result;
    if (!result) return '<div class="empty">只读工具会执行安全预览；runtime / dangerous 工具只返回 blocked，不会直接提交任务。</div>';
    const status = String(result.status || "draft");
    const safeText = result.safe ? "safe read-only" : "blocked / plan-only";
    const body = JSON.stringify(result.result ?? result, null, 2);
    return `
    <div class="workspace-agent-debug-result">
      <div class="workspace-agent-debug-actions">
        <button class="secondary mini" type="button" data-action="copy-tool-test-result" title="复制完整工具安全测试结果 JSON">复制结果</button>
      </div>
      <div class="workspace-agent-debug-summary">
        <article class="workspace-agent-debug-card status-${escapeFor(deps, status)}">
          <span>测试状态</span>
          <strong>${escapeFor(deps, status)}</strong>
          <em>${escapeFor(deps, safeText)} · ${escapeFor(deps, result.side_effect || "read")}${result.latency_ms ? ` · ${escapeFor(deps, String(result.latency_ms))}ms` : ""}</em>
        </article>
        <article class="workspace-agent-debug-card">
          <span>上下文</span>
          <strong>${escapeFor(deps, result.workspace?.name || result.workspace?.id || "无实例")}</strong>
          <em>${escapeFor(deps, result.tool_id || testState.toolId || "")}</em>
        </article>
      </div>
      <pre class="workspace-agent-debug-pre">${escapeFor(deps, body.slice(0, 6000))}</pre>
    </div>
  `;
  }

  function providerRouteHealthMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      issueLabel: options.issueLabel,
      statusLabel: options.statusLabel,
    };
    const health = options.health && typeof options.health === "object" ? options.health : {};
    const issues = Array.isArray(health.issues) ? health.issues : [];
    const status = String(health.effective_status || health.status || "draft");
    const firstIssues = issues.slice(0, 5);
    const blockingCount = Number(health.effective_blocking_count ?? health.blocking_count ?? 0);
    const healthLabel = blockingCount
      ? fn(deps, "statusLabel", (value) => value)("blocked")
      : Number(health.configured_profile_count || 0)
        ? "可用"
        : fn(deps, "statusLabel", (value) => value)(status);
    const configuredSearchCount = Number(health.configured_search_profile_count || options.configuredSearchProfileCount || 0);
    const searchCount = Number(health.search_profile_count || options.searchProfileCount || 0);
    const issueLabel = fn(deps, "issueLabel", (issue) => issue?.message || issue?.code || "");
    return `
    <div class="workspace-node-editor-card workspace-manage-editor-stack status-${escapeFor(deps, status)}">
      <div class="workspace-node-editor-head">
        <div>
          <h4>Provider 路由健康</h4>
          <p class="muted">${escapeFor(deps, `LLM ${Number(health.configured_profile_count || 0)}/${Number(health.profile_count || 0)} · Search ${configuredSearchCount}/${searchCount} · ${blockingCount} 阻塞 · ${Number(health.warning_count || 0)} 提示`)}</p>
        </div>
        <span class="state ${escapeFor(deps, status)}">${escapeFor(deps, healthLabel)}</span>
      </div>
      ${firstIssues.length ? `
        <div class="workspace-agent-debug-warning-list">
          ${firstIssues.map((issue) => `<div class="workspace-agent-debug-warning">${escapeFor(deps, issueLabel(issue))}</div>`).join("")}
        </div>
      ` : '<div class="empty">当前 Provider / Agent / 模板路由没有发现明显缺口。</div>'}
    </div>
  `;
  }

  window.ConfigCenterDiagnostics = {
    defaultToolTestArguments,
    providerRouteHealthMarkup,
    toolTestResultMarkup,
  };
})();
