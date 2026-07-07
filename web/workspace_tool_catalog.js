(function () {
  "use strict";

  const CATEGORY_LABELS = {
    workflow: "工作流",
    research: "检索",
    data: "数据",
    repo: "仓库",
    path: "路径",
    file: "文件",
    host: "主机",
    gpu: "GPU",
    env: "环境",
    run: "运行",
    log: "日志",
    artifact: "产物",
    notify: "通知",
    chat: "对话",
    general: "通用",
  };

  function workspaceToolById(toolId, list) {
    return list.find((item) => item.id === toolId) || null;
  }

  function workspaceToolLabel(toolId, list) {
    return workspaceToolById(toolId, list)?.label || toolId || "未命名工具";
  }

  function workspaceToolCategoryLabel(category) {
    return CATEGORY_LABELS[String(category || "general")] || String(category || "通用");
  }

  function workspaceToolsByCategory(tools) {
    const buckets = new Map();
    tools.forEach((tool) => {
      const key = String(tool.category || "general");
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(tool);
    });
    return Array.from(buckets.entries()).map(([category, items]) => ({
      category,
      label: workspaceToolCategoryLabel(category),
      items,
    }));
  }

  function workspaceToolSummary(tool) {
    if (!tool) return "";
    const parts = [
      workspaceToolCategoryLabel(tool.category || "general"),
      tool.capability || "read",
    ];
    if (tool.description) parts.push(tool.description);
    return parts.join(" · ");
  }

  function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeFor(options, value) {
    return (typeof options.escapeHtml === "function" ? options.escapeHtml : fallbackEscapeHtml)(value);
  }

  function workspaceToolPolicyBadge(sideEffect = "", controlled = false, options = {}) {
    const tier = String(sideEffect || "").trim();
    if (!tier) return "";
    const map = {
      read: { label: "读", cls: "policy-read" },
      mutate_config: { label: "改配置", cls: "policy-config" },
      mutate_runtime: { label: controlled ? "受控运行" : "运行", cls: "policy-runtime" },
      dangerous: { label: "危险", cls: "policy-dangerous" },
    };
    const entry = map[tier];
    if (!entry) return "";
    return `<span class="tool-policy-badge ${entry.cls}" title="工具权限策略：${escapeFor(options, tier)}${controlled ? "（经 job 队列受控）" : ""}">${escapeFor(options, entry.label)}</span>`;
  }

  window.WorkspaceToolCatalog = {
    workspaceToolById,
    workspaceToolCategoryLabel,
    workspaceToolLabel,
    workspaceToolPolicyBadge,
    workspaceToolSummary,
    workspaceToolsByCategory,
  };
})();
