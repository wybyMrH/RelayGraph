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

  function formatBytesFor(deps, value) {
    if (typeof deps.formatBytes === "function") return deps.formatBytes(value);
    const bytes = Number(value || 0);
    if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
    if (bytes < 1024) return `${Math.round(bytes)} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GiB`;
  }

  function runtimeStorageStatsMarkup(payload = {}, options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      formatBytes: options.formatBytes,
    };
    const preview = payload.preview_cache || {};
    const localLogs = payload.local_logs || {};
    const remoteLogs = Array.isArray(payload.remote_logs) ? payload.remote_logs : [];
    const remoteOk = remoteLogs.filter((item) => !item.error && !item.skipped);
    const remoteIssues = remoteLogs.length - remoteOk.length;
    const remoteBytes = remoteOk.reduce((sum, item) => sum + Number(item.total_bytes || 0), 0);
    const remoteFiles = remoteOk.reduce((sum, item) => sum + Number(item.file_count || 0), 0);
    const paths = payload.paths || {};
    const localNewest = localLogs.newest_path
      ? `本机最新日志：<code>${escapeFor(deps, localLogs.newest_path)}</code>${localLogs.newest_at ? ` · ${escapeFor(deps, localLogs.newest_at)}` : ""}`
      : "本机最新日志：暂无";
    const localLargest = localLogs.largest_path
      ? `本机最大日志：<code>${escapeFor(deps, localLogs.largest_path)}</code> · ${escapeFor(deps, localLogs.largest_text || formatBytesFor(deps, localLogs.largest_bytes))}`
      : "";
    const remoteNewestLines = remoteOk
      .filter((item) => item.newest_path)
      .slice(0, 3)
      .map((item) => {
        const serverName = item.server_name || item.server_id || "远程";
        const newestAt = item.newest_at ? ` · ${escapeFor(deps, item.newest_at)}` : "";
        return `远程最新日志：${escapeFor(deps, serverName)} <code>${escapeFor(deps, item.newest_path)}</code>${newestAt}`;
      });
    const lines = [
      `本机日志 <code>${escapeFor(deps, paths.local_logs || localLogs.log_dir || "data/logs")}</code>：${Number(localLogs.file_count || 0)} 个文件 · ${escapeFor(deps, localLogs.total_text || formatBytesFor(deps, localLogs.total_bytes))}`,
      `远程日志 <code>${escapeFor(deps, paths.remote_logs || "$HOME/.total_control/logs")}</code>：${remoteOk.length} 台可读 · ${remoteFiles} 个文件 · ${escapeFor(deps, formatBytesFor(deps, remoteBytes))}${remoteIssues ? ` · ${remoteIssues} 台不可读/已跳过` : ""}`,
      `预览缓存 <code>${escapeFor(deps, paths.preview_cache || preview.cache_dir || "/tmp/total-control-file-preview")}</code>：${Number(preview.entry_count || 0)} 项 · ${escapeFor(deps, preview.total_text || formatBytesFor(deps, preview.total_bytes))}`,
    ];
    const detailLines = [localNewest, localLargest, ...remoteNewestLines].filter(Boolean);
    return `${lines.join("<br>")}${detailLines.length ? `<br>${detailLines.join("<br>")}` : ""}`;
  }

  function runtimeStateStatsMarkup(payload = {}, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const jobs = payload.jobs || {};
    const workspaces = payload.workspaces || {};
    const top = Array.isArray(workspaces.items) ? workspaces.items : [];
    const topRuns = top
      .filter((item) => Number(item.run_count || 0) > 0)
      .slice(0, 3)
      .map((item) => `${escapeFor(deps, item.name || item.workspace_id || "项目")} ${Number(item.run_count || 0)} 条`)
      .join(" · ");
    const lines = [
      `任务记录：${Number(jobs.total || 0)} 条 · 可清理 ${Number(jobs.completed || 0)} 条 · 活跃 ${Number(jobs.active || 0)} 条`,
      `项目运行记录：${Number(workspaces.total_runs || 0)} 条 · 活跃 ${Number(workspaces.active_runs || 0)} 条 · 事件 ${Number(workspaces.total_events || 0)} 条`,
    ];
    if (topRuns) lines.push(`记录较多：${topRuns}`);
    return lines.join("<br>");
  }

  function runtimeStorageCleanupMessage(payload = {}, removeAll = false, options = {}) {
    const deps = { formatBytes: options.formatBytes };
    const previewRemoved = payload.preview_cache?.removed_text || "0 B";
    const localRemoved = payload.local_logs?.removed_text || "0 B";
    const remoteRemoved = (Array.isArray(payload.remote_logs) ? payload.remote_logs : [])
      .reduce((sum, item) => sum + Number(item.removed_bytes || 0), 0);
    const localPreserved = Number(payload.local_logs?.preserved_count || 0);
    const remotePreserved = (Array.isArray(payload.remote_logs) ? payload.remote_logs : [])
      .reduce((sum, item) => sum + Number(item.preserved_count || 0), 0);
    const preservedText = localPreserved || remotePreserved
      ? ` 已保留活跃任务或运行证据日志 ${localPreserved + remotePreserved} 个。`
      : "";
    return `${removeAll ? "已清空" : "已按策略清理"}：预览缓存 ${previewRemoved}，本机日志 ${localRemoved}，远程日志 ${formatBytesFor(deps, remoteRemoved)}。${preservedText}`;
  }

  window.RuntimeStorageSummary = {
    runtimeStateStatsMarkup,
    runtimeStorageCleanupMessage,
    runtimeStorageStatsMarkup,
  };
})();
