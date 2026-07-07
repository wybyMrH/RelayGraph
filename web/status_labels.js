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

  window.StatusLabels = {
    kindText,
    statusText,
    workspaceInputStatusLabel,
    workspaceStatusLabel,
    zhKind,
    zhStatus,
  };
})();
