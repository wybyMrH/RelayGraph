(function () {
  "use strict";

  const statusText = {
    draft: "草稿",
    ready: "已就绪",
    preview: "预览",
    pending: "未运行",
    idle: "空闲",
    busy: "忙碌",
    blocked: "等待 Profile",
    queued: "等待中",
    starting: "启动中",
    running: "运行中",
    done: "已完成",
    completed: "已完成",
    failed: "失败",
    stopped: "已停止",
    offline: "离线",
  };

  const kindText = {
    command: "单命令",
    "batch-item": "批量",
    "profiled-batch-item": "批量",
    profile: "Profile",
    transfer: "文件传输",
  };

  function zhStatus(value) {
    return statusText[value] || value || "-";
  }

  function zhKind(value) {
    return kindText[value] || value || "任务";
  }

  function workspaceStatusLabel(value, deps = {}) {
    const labelStatus = typeof deps.zhStatus === "function" ? deps.zhStatus : zhStatus;
    const text = String(value || "");
    if (text === "blocked") return "阻塞";
    return labelStatus(text);
  }

  function workspaceInputStatusLabel(status = "", deps = {}) {
    const labelWorkspaceStatus = typeof deps.workspaceStatusLabel === "function"
      ? deps.workspaceStatusLabel
      : workspaceStatusLabel;
    const value = String(status || "").trim();
    if (["ready", "done"].includes(value)) return "已连通";
    if (["blocked", "failed", "stopped"].includes(value)) return "输入断点";
    if (["warning", "pending", "draft"].includes(value)) return "待确认";
    return labelWorkspaceStatus(value || "draft");
  }

  function workspaceArtifactStatusLabel(status = "") {
    const value = String(status || "").trim();
    if (value === "found") return "已找到";
    if (value === "expected") return "待生成";
    if (value === "missing") return "缺失";
    if (value === "unreadable") return "不可读";
    if (value === "planned") return "计划中";
    return value || "未知";
  }

  function workspaceTraceStatusLabel(status = "", deps = {}) {
    const labelWorkspaceStatus = typeof deps.workspaceStatusLabel === "function"
      ? deps.workspaceStatusLabel
      : workspaceStatusLabel;
    const value = String(status || "").trim();
    if (value === "planned") return "已编排";
    if (value === "queued") return "排队";
    if (value === "blocked") return "等待";
    if (value === "running") return "运行";
    if (value === "done") return "完成";
    if (value === "failed") return "失败";
    if (value === "stopped") return "停止";
    return labelWorkspaceStatus(value || "pending");
  }

  window.StatusLabels = {
    kindText,
    statusText,
    workspaceArtifactStatusLabel,
    workspaceInputStatusLabel,
    workspaceStatusLabel,
    workspaceTraceStatusLabel,
    zhKind,
    zhStatus,
  };
})();
