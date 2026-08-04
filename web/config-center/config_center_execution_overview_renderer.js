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

  function objectFor(value) {
    return value && typeof value === "object" ? value : {};
  }

  function manageRunOverviewItemMarkup(run = {}, deps = {}) {
    const module = fn(deps, "workspaceExecutionOverviewModule", () => null)();
    if (typeof module?.runItemMarkup === "function") {
      return module.runItemMarkup(run, {
        escapeHtml: fn(deps, "escapeHtml", (value) => String(value ?? "")),
        fmtDate: fn(deps, "fmtDate", (value) => String(value || "")),
        statusLabel: fn(deps, "workspaceStatusLabel", (value) => value),
        runKindLabel: fn(deps, "workspaceRunKindLabel", (value) => value),
      });
    }
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const fmtDate = fn(deps, "fmtDate", (value) => String(value || ""));
    const workspaceStatusLabel = fn(deps, "workspaceStatusLabel", (value) => value);
    const workspaceRunKindLabel = fn(deps, "workspaceRunKindLabel", (value) => value);
    const executionOverviewStatusClass = fn(deps, "executionOverviewStatusClass", (value) => value || "draft");
    const progress = run.progress && typeof run.progress === "object" ? run.progress : {};
    const status = executionOverviewStatusClass(run.status);
    return `
    <button class="workspace-execution-run-item workspace-template-item status-${escapeHtml(status)}" type="button" data-action="open-overview-workspace" data-workspace-id="${escapeHtml(run.workspace_id || "")}" title="打开所属实例驾驶舱">
      <div class="workspace-template-item-head">
        <strong>${escapeHtml(run.summary || workspaceRunKindLabel(run.kind) || run.id || "Run")}</strong>
        <span class="state ${escapeHtml(status)}">${escapeHtml(workspaceStatusLabel(run.status || "pending"))}</span>
      </div>
      <div class="workspace-template-item-meta">${escapeHtml(run.workspace_name || run.workspace_id || "未绑定实例")} · ${escapeHtml(fmtDate(run.updated_at || run.created_at))}</div>
      <div class="workspace-template-item-desc">${escapeHtml(`${Number(progress.done || 0)}/${Number(progress.total || run.step_count || 0)} 步 · ${Number(progress.percent || 0)}% · ${run.job_ids?.length || 0} job · ${run.agent_execution_ids?.length || 0} agent`)}</div>
    </button>
  `;
  }

  function manageJobOverviewItemMarkup(job = {}, deps = {}) {
    const module = fn(deps, "workspaceExecutionOverviewModule", () => null)();
    if (typeof module?.jobItemMarkup === "function") {
      return module.jobItemMarkup(job, {
        escapeHtml: fn(deps, "escapeHtml", (value) => String(value ?? "")),
        fmtDate: fn(deps, "fmtDate", (value) => String(value || "")),
        zhStatus: fn(deps, "zhStatus", (value) => value),
      });
    }
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const fmtDate = fn(deps, "fmtDate", (value) => String(value || ""));
    const zhStatus = fn(deps, "zhStatus", (value) => value);
    const executionOverviewStatusClass = fn(deps, "executionOverviewStatusClass", (value) => value || "draft");
    const status = executionOverviewStatusClass(job.status);
    return `
    <button class="workspace-execution-run-item workspace-template-item status-${escapeHtml(status)}" type="button" data-action="open-overview-workspace" data-workspace-id="${escapeHtml(job.workspace_id || "")}" title="打开所属实例驾驶舱">
      <div class="workspace-template-item-head">
        <strong>${escapeHtml(job.summary || job.kind || job.id || "Job")}</strong>
        <span class="state ${escapeHtml(status)}">${escapeHtml(zhStatus(job.status || "pending"))}</span>
      </div>
      <div class="workspace-template-item-meta">${escapeHtml(job.workspace_name || job.workspace_id || "未绑定实例")} · ${escapeHtml(job.server_id || "server auto")} · ${escapeHtml(fmtDate(job.updated_at || job.created_at))}</div>
      <div class="workspace-template-item-desc">${escapeHtml(job.execution_run_id ? `run ${job.execution_run_id}` : job.id || "")}</div>
    </button>
  `;
  }

  function renderManageRunsModule(deps = {}) {
    const summaryRoot = element(deps, "workspaceManageRunSummary");
    const runList = element(deps, "workspaceManageRunList");
    const jobList = element(deps, "workspaceManageJobList");
    if (!summaryRoot && !runList && !jobList) return;
    const escapeHtml = fn(deps, "escapeHtml", (value) => String(value ?? ""));
    const overview = objectFor(fn(deps, "executionOverview", () => ({}))());
    const summary = objectFor(overview.summary);
    const result = objectFor(overview.result);
    const runs = listFor(overview.runs);
    const jobs = listFor(overview.jobs);
    const filters = fn(deps, "executionOverviewFilters", () => ({}))();
    const backendFilters = overview.filters && typeof overview.filters === "object" ? overview.filters : null;
    const filtered = backendFilters && fn(deps, "executionOverviewFiltersMatch", () => false)(backendFilters, filters)
      ? fn(deps, "backendFilteredExecutionOverviewItems", () => ({ runs: [], jobs: [], showRuns: true, showJobs: true }))(runs, jobs, filters)
      : fn(deps, "filteredExecutionOverviewItems", () => ({ runs, jobs, showRuns: true, showJobs: true }))(runs, jobs, filters);
    fn(deps, "syncExecutionOverviewFilterControls", () => {})(filters, {
      totalRuns: Number(summary.run_count ?? runs.length),
      totalJobs: Number(summary.job_count ?? jobs.length),
      matchedRuns: Number(result.run_count ?? filtered.runs.length),
      matchedJobs: Number(result.job_count ?? filtered.jobs.length),
      visibleRuns: filtered.runs.length,
      visibleJobs: filtered.jobs.length,
      limited: Boolean(result.limited),
    });
    if (summaryRoot) {
      if (overview.error) {
        summaryRoot.innerHTML = `<article class="workspace-agent-coverage-card status-failed"><strong>加载失败</strong><span>${escapeHtml(overview.error)}</span></article>`;
      } else {
        const module = fn(deps, "workspaceExecutionOverviewModule", () => null)();
        summaryRoot.innerHTML = typeof module?.summaryCardsMarkup === "function"
          ? module.summaryCardsMarkup({ summary, runs, jobs, escapeHtml })
          : [
            { label: "Runs", value: Number(summary.run_count || runs.length), status: summary.active_run_count ? "running" : "ready" },
            { label: "Jobs", value: Number(summary.job_count || jobs.length), status: summary.active_job_count ? "running" : "ready" },
            { label: "活跃任务", value: Number(summary.active_job_count || 0), status: summary.active_job_count ? "running" : "ready" },
            { label: "失败/停止", value: Number(summary.failed_run_count || 0) + Number(summary.failed_job_count || 0), status: (summary.failed_run_count || summary.failed_job_count) ? "blocked" : "ready" },
          ].map((item) => `
          <article class="workspace-agent-coverage-card status-${escapeHtml(item.status)}">
            <span>${escapeHtml(item.label)}</span>
            <strong>${escapeHtml(String(item.value))}</strong>
          </article>
        `).join("");
      }
    }
    if (runList) {
      runList.innerHTML = !filtered.showRuns
        ? '<div class="empty">当前类型筛选只显示 Jobs。</div>'
        : filtered.runs.length
          ? filtered.runs.slice(0, 30).map((run) => manageRunOverviewItemMarkup(run, deps)).join("")
          : runs.length
            ? '<div class="empty">没有匹配的 run 记录。</div>'
            : '<div class="empty">还没有全局 run 记录。</div>';
    }
    if (jobList) {
      jobList.innerHTML = !filtered.showJobs
        ? '<div class="empty">当前类型筛选只显示 Runs。</div>'
        : filtered.jobs.length
          ? filtered.jobs.slice(0, 30).map((job) => manageJobOverviewItemMarkup(job, deps)).join("")
          : jobs.length
            ? '<div class="empty">没有匹配的队列任务。</div>'
            : '<div class="empty">还没有队列任务。</div>';
    }
  }

  window.ConfigCenterExecutionOverviewRenderer = {
    manageJobOverviewItemMarkup,
    manageRunOverviewItemMarkup,
    renderManageRunsModule,
  };
})();
