(function () {
  "use strict";

  function updateList(root, markup) {
    if (!root) return;
    // Compare browser-normalized markup without retaining a second payload/cache.
    const template = document.createElement("template");
    template.innerHTML = markup;
    if (root.innerHTML === template.innerHTML) return;
    const active = document.activeElement;
    const key = root.contains(active) ? active.closest("[data-overview-record]")?.dataset.overviewRecord : null;
    root.replaceChildren(template.content);
    if (key) Array.from(root.querySelectorAll("[data-overview-record]"))
      .find((item) => item.dataset.overviewRecord === key)?.focus({ preventScroll: true });
  }

  function render(deps) {
    const root = deps.element("workspaceExecutionOverviewPanel");
    if (!root || root.hidden) return;
    const api = deps.overviewModule;
    const overview = deps.executionOverview();
    const filters = deps.executionOverviewFilters();
    const loading = deps.loading();
    const current = Boolean(overview && api.filtersMatch(overview.filters || {}, filters));
    const error = current && !loading ? overview?.error || "" : "";
    const waiting = !error && (!current || loading);
    const runs = current ? overview.runs || [] : [];
    const jobs = current ? overview.jobs || [] : [];
    const summary = overview?.summary || {};
    const result = current ? overview.result || {} : {};
    deps.syncExecutionOverviewFilterControls(filters, {
      totalRuns: Number(summary.run_count || 0), totalJobs: Number(summary.job_count || 0),
      matchedRuns: Number(result.run_count || 0), matchedJobs: Number(result.job_count || 0),
      visibleRuns: runs.length, visibleJobs: jobs.length, limited: Boolean(result.limited),
    });
    const summaryRoot = deps.element("workspaceExecutionOverviewSummary");
    if (summaryRoot) {
      const markup = error
        ? `<p class="workspace-global-runs-error" role="alert">加载失败：${deps.escapeHtml(error)}。请点击刷新重试。</p>`
        : `${waiting ? '<p role="status">正在读取运行记录…</p>' : ""}${overview ? api.summaryMarkup({ summary, escapeHtml: deps.escapeHtml }) : ""}`;
      if (summaryRoot.innerHTML !== markup) summaryRoot.innerHTML = markup;
    }
    const options = {
      escapeHtml: deps.escapeHtml, fmtDate: deps.fmtDate, statusLabel: deps.workspaceStatusLabel,
      runKindLabel: deps.workspaceRunKindLabel, zhStatus: deps.zhStatus,
    };
    const showRuns = filters.kind !== "jobs";
    const showJobs = filters.kind !== "runs";
    const runSection = deps.element("workspaceExecutionOverviewRunSection");
    const jobSection = deps.element("workspaceExecutionOverviewJobSection");
    if (runSection) runSection.hidden = !showRuns;
    if (jobSection) jobSection.hidden = !showJobs;
    const empty = (kind) => error ? '<div class="empty">记录尚未读取成功。</div>'
      : waiting && !current ? '<div class="empty">正在按当前筛选读取…</div>'
        : `<div class="empty">${filters.query || filters.status ? "没有匹配的" : "还没有"}${kind}记录。</div>`;
    updateList(deps.element("workspaceExecutionOverviewRunList"), runs.length
      ? runs.map((run) => api.runItemMarkup(run, options)).join("") : empty("运行"));
    updateList(deps.element("workspaceExecutionOverviewJobList"), jobs.length
      ? jobs.map((job) => api.jobItemMarkup(job, options)).join("") : empty("任务"));
    const button = root.querySelector("[data-action='refresh-execution-overview']");
    if (button) button.setAttribute("aria-busy", String(loading));
  }

  window.WorkspaceExecutionOverviewRenderer = { render };
})();
