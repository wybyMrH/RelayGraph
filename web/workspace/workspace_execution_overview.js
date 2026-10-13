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

  function statusClass(status = "") {
    const value = String(status || "pending");
    if (["done", "ready", "completed"].includes(value)) return "ready";
    if (["running", "queued", "starting", "pending"].includes(value)) return "running";
    if (["failed", "blocked", "stopped"].includes(value)) return "blocked";
    return "draft";
  }

  function normalizeFilters(filters = {}) {
    const source = filters && typeof filters === "object" ? filters : {};
    const kind = String(source.kind || "all").trim();
    return {
      query: String(source.query || "").trim().toLowerCase(),
      status: String(source.status || "").trim(),
      kind: ["all", "runs", "jobs"].includes(kind) ? kind : "all",
    };
  }

  function filtersMatch(a = {}, b = {}) {
    const left = normalizeFilters(a);
    const right = normalizeFilters(b);
    return left.query === right.query && left.status === right.status && left.kind === right.kind;
  }

  function summaryMarkup(options = {}) {
    const summary = options.summary || {};
    const escape = options.escapeHtml;
    return `<p>累计 ${escape(Number(summary.run_count || 0))} 次运行、${escape(Number(summary.job_count || 0))} 个任务；
      活跃运行 ${escape(Number(summary.active_run_count || 0))}、活跃任务 ${escape(Number(summary.active_job_count || 0))}；
      失败或停止的运行 ${escape(Number(summary.failed_run_count || 0))}、任务 ${escape(Number(summary.failed_job_count || 0))}。</p>`;
  }

  function recordMarkup(record, options, type) {
    const isRun = type === "run";
    const runId = isRun ? record.id : record.execution_run_id;
    const jobId = isRun ? "" : record.id;
    const progress = record.progress || {};
    const status = statusClass(record.status);
    const statusLabel = isRun ? options.statusLabel : options.zhStatus;
    const title = record.summary || (isRun ? options.runKindLabel(record.kind) : record.kind) || record.id;
    const detail = isRun
      ? `${Number(progress.done || 0)}/${Number(progress.total || record.step_count || 0)} 步 · ${Number(progress.percent || 0)}%`
      : `主机 ${record.server_id || "尚未分配"}${runId ? ` · 运行 ${runId}` : " · 独立任务"}`;
    const escape = (value) => escapeFor(options, value);
    return `<button class="workspace-global-run-item status-${escape(status)}" type="button"
      data-action="open-overview-workspace" data-overview-record="${escape(type + ":" + record.id)}"
      data-workspace-id="${escape(record.workspace_id || "")}" data-run-id="${escape(runId || "")}" data-job-id="${escape(jobId)}"
      title="${isRun ? "阅读这次运行的步骤与结果" : "打开这个任务的日志"}">
      <span class="workspace-global-run-item-head"><strong>${escape(title)}</strong>
        <span class="state ${escape(status)}">${escape(statusLabel(record.status || "pending"))}</span></span>
      <span class="workspace-global-run-item-meta">${escape(record.workspace_name || record.workspace_id || "未绑定实例")} · ${escape(options.fmtDate(record.updated_at || record.created_at))}</span>
      <span class="workspace-global-run-item-meta">${escape(detail)}</span>
      <span class="workspace-global-run-item-id">${escape(record.id || "")}</span>
    </button>`;
  }

  function runItemMarkup(run = {}, options = {}) {
    return recordMarkup(run, options, "run");
  }

  function jobItemMarkup(job = {}, options = {}) {
    return recordMarkup(job, options, "job");
  }

  window.WorkspaceExecutionOverview = {
    filtersMatch,
    jobItemMarkup,
    normalizeFilters,
    runItemMarkup,
    statusClass,
    summaryMarkup,
  };
})();
