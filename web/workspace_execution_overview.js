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

  function statusClass(status = "") {
    const value = String(status || "pending");
    if (["done", "ready", "completed"].includes(value)) return "ready";
    if (["running", "queued", "starting", "pending"].includes(value)) return "running";
    if (["failed", "blocked", "stopped"].includes(value)) return "blocked";
    return "draft";
  }

  function statusGroup(status = "") {
    const value = String(status || "pending").trim().toLowerCase();
    if (["done", "ready", "completed", "success", "succeeded"].includes(value)) return "done";
    if (["failed", "blocked", "stopped", "cancelled", "canceled"].includes(value)) return "failed";
    if (["running", "queued", "starting", "pending"].includes(value)) return "active";
    return "active";
  }

  function recordSearchText(record = {}, type = "") {
    const progress = record.progress && typeof record.progress === "object" ? record.progress : {};
    return [
      type,
      record.id,
      record.run_id,
      record.execution_run_id,
      record.job_id,
      record.workspace_id,
      record.workspace_name,
      record.summary,
      record.kind,
      record.status,
      record.server_id,
      record.node_id,
      record.agent_id,
      Array.isArray(record.job_ids) ? record.job_ids.join(" ") : "",
      Array.isArray(record.agent_execution_ids) ? record.agent_execution_ids.join(" ") : "",
      progress.done,
      progress.total,
      progress.percent,
    ].map((item) => String(item || "").toLowerCase()).join(" ");
  }

  function recordMatches(record = {}, type = "run", filters = {}) {
    const normalized = {
      query: String(filters.query || "").trim().toLowerCase(),
      status: String(filters.status || "").trim(),
    };
    if (normalized.status && statusGroup(record.status) !== normalized.status) return false;
    if (normalized.query && !recordSearchText(record, type).includes(normalized.query)) return false;
    return true;
  }

  function filteredItems(runs = [], jobs = [], filters = {}) {
    const kind = String(filters.kind || "all");
    const showRuns = kind !== "jobs";
    const showJobs = kind !== "runs";
    return {
      runs: showRuns ? (Array.isArray(runs) ? runs : []).filter((run) => recordMatches(run, "run", filters)) : [],
      jobs: showJobs ? (Array.isArray(jobs) ? jobs : []).filter((job) => recordMatches(job, "job", filters)) : [],
      showRuns,
      showJobs,
    };
  }

  function summaryCardsMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const summary = options.summary && typeof options.summary === "object" ? options.summary : {};
    const runs = Array.isArray(options.runs) ? options.runs : [];
    const jobs = Array.isArray(options.jobs) ? options.jobs : [];
    const cards = [
      { label: "Runs", value: Number(summary.run_count || runs.length), status: summary.active_run_count ? "running" : "ready" },
      { label: "Jobs", value: Number(summary.job_count || jobs.length), status: summary.active_job_count ? "running" : "ready" },
      { label: "活跃任务", value: Number(summary.active_job_count || 0), status: summary.active_job_count ? "running" : "ready" },
      { label: "失败/停止", value: Number(summary.failed_run_count || 0) + Number(summary.failed_job_count || 0), status: (summary.failed_run_count || summary.failed_job_count) ? "blocked" : "ready" },
    ];
    return cards.map((item) => `
        <article class="workspace-agent-coverage-card status-${escapeFor(deps, item.status)}">
          <span>${escapeFor(deps, item.label)}</span>
          <strong>${escapeFor(deps, String(item.value))}</strong>
        </article>
      `).join("");
  }

  function runItemMarkup(run = {}, options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      fmtDate: options.fmtDate,
      statusLabel: options.statusLabel,
      runKindLabel: options.runKindLabel,
    };
    const progress = run.progress && typeof run.progress === "object" ? run.progress : {};
    const status = statusClass(run.status);
    const statusLabel = fn(deps, "statusLabel", (value) => value);
    const runKindLabel = fn(deps, "runKindLabel", (value) => value);
    const fmtDate = fn(deps, "fmtDate", (value) => String(value || ""));
    return `
    <button class="workspace-execution-run-item workspace-template-item status-${escapeFor(deps, status)}" type="button" data-action="open-overview-workspace" data-workspace-id="${escapeFor(deps, run.workspace_id || "")}" title="打开所属实例驾驶舱">
      <div class="workspace-template-item-head">
        <strong>${escapeFor(deps, run.summary || runKindLabel(run.kind) || run.id || "Run")}</strong>
        <span class="state ${escapeFor(deps, status)}">${escapeFor(deps, statusLabel(run.status || "pending"))}</span>
      </div>
      <div class="workspace-template-item-meta">${escapeFor(deps, run.workspace_name || run.workspace_id || "未绑定实例")} · ${escapeFor(deps, fmtDate(run.updated_at || run.created_at))}</div>
      <div class="workspace-template-item-desc">${escapeFor(deps, `${Number(progress.done || 0)}/${Number(progress.total || run.step_count || 0)} 步 · ${Number(progress.percent || 0)}% · ${run.job_ids?.length || 0} job · ${run.agent_execution_ids?.length || 0} agent`)}</div>
    </button>
  `;
  }

  function jobItemMarkup(job = {}, options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      fmtDate: options.fmtDate,
      zhStatus: options.zhStatus,
    };
    const status = statusClass(job.status);
    const zhStatus = fn(deps, "zhStatus", (value) => value);
    const fmtDate = fn(deps, "fmtDate", (value) => String(value || ""));
    return `
    <button class="workspace-execution-run-item workspace-template-item status-${escapeFor(deps, status)}" type="button" data-action="open-overview-workspace" data-workspace-id="${escapeFor(deps, job.workspace_id || "")}" title="打开所属实例驾驶舱">
      <div class="workspace-template-item-head">
        <strong>${escapeFor(deps, job.summary || job.kind || job.id || "Job")}</strong>
        <span class="state ${escapeFor(deps, status)}">${escapeFor(deps, zhStatus(job.status || "pending"))}</span>
      </div>
      <div class="workspace-template-item-meta">${escapeFor(deps, job.workspace_name || job.workspace_id || "未绑定实例")} · ${escapeFor(deps, job.server_id || "server auto")} · ${escapeFor(deps, fmtDate(job.updated_at || job.created_at))}</div>
      <div class="workspace-template-item-desc">${escapeFor(deps, job.execution_run_id ? `run ${job.execution_run_id}` : job.id || "")}</div>
    </button>
  `;
  }

  window.WorkspaceExecutionOverview = {
    filteredItems,
    jobItemMarkup,
    recordMatches,
    recordSearchText,
    runItemMarkup,
    statusClass,
    statusGroup,
    summaryCardsMarkup,
  };
})();
