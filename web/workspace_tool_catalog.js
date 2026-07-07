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

  window.WorkspaceToolCatalog = {
    workspaceToolById,
    workspaceToolCategoryLabel,
    workspaceToolLabel,
    workspaceToolSummary,
    workspaceToolsByCategory,
  };
})();
