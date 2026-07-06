(function () {
  "use strict";

  const STATUS_ORDER = ["queued", "starting", "running", "blocked", "failed", "stopped", "done"];

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

  function normalizeFilters(filters = {}) {
    return {
      status: String(filters.status || "").trim(),
      nodeKind: String(filters.nodeKind || "").trim(),
      jobId: String(filters.jobId || "").trim().toLowerCase(),
      agentExecutionId: String(filters.agentExecutionId || "").trim().toLowerCase(),
    };
  }

  function activeCount(filters = {}) {
    const normalized = normalizeFilters(filters);
    return [
      normalized.status,
      normalized.nodeKind,
      normalized.jobId,
      normalized.agentExecutionId,
    ].filter(Boolean).length;
  }

  function stepList(run = {}) {
    return Array.isArray(run.steps) ? run.steps.filter((step) => step && typeof step === "object") : [];
  }

  function stepJobIds(step = {}) {
    return [
      step.job_id,
      ...(Array.isArray(step.child_job_ids) ? step.child_job_ids : []),
    ].map((item) => String(item || "").trim()).filter(Boolean);
  }

  function stepAgentExecutionIds(step = {}) {
    return [
      step.agent_execution_id,
      ...(Array.isArray(step.agent_execution_ids) ? step.agent_execution_ids : []),
    ].map((item) => String(item || "").trim()).filter(Boolean);
  }

  function matches(run = {}, filters = {}) {
    const normalized = normalizeFilters(filters);
    const steps = stepList(run);
    if (normalized.status && String(run.status || "").trim() !== normalized.status) return false;
    if (normalized.nodeKind && !steps.some((step) => String(step.node_kind || "").trim() === normalized.nodeKind)) return false;
    if (normalized.jobId) {
      const jobIds = steps.flatMap((step) => stepJobIds(step));
      if (!jobIds.some((jobId) => jobId.toLowerCase().includes(normalized.jobId))) return false;
    }
    if (normalized.agentExecutionId) {
      const agentIds = steps.flatMap((step) => stepAgentExecutionIds(step));
      if (!agentIds.some((agentId) => agentId.toLowerCase().includes(normalized.agentExecutionId))) return false;
    }
    return true;
  }

  function filterRuns(runs = [], filters = {}) {
    const list = Array.isArray(runs) ? runs : [];
    const normalized = normalizeFilters(filters);
    if (!activeCount(normalized)) return list;
    return list.filter((run) => matches(run, normalized));
  }

  function options(runs = []) {
    const statuses = new Set();
    const nodeKinds = new Set();
    (Array.isArray(runs) ? runs : []).forEach((run) => {
      const status = String(run?.status || "").trim();
      if (status) statuses.add(status);
      stepList(run).forEach((step) => {
        const kind = String(step.node_kind || "").trim();
        if (kind) nodeKinds.add(kind);
      });
    });
    return {
      statuses: Array.from(statuses).sort((left, right) => {
        const leftIndex = STATUS_ORDER.indexOf(left);
        const rightIndex = STATUS_ORDER.indexOf(right);
        if (leftIndex !== rightIndex) return (leftIndex < 0 ? 999 : leftIndex) - (rightIndex < 0 ? 999 : rightIndex);
        return left.localeCompare(right);
      }),
      nodeKinds: Array.from(nodeKinds).sort((left, right) => left.localeCompare(right)),
    };
  }

  function barMarkup(config = {}) {
    const deps = {
      escapeHtml: config.escapeHtml,
      statusLabel: config.statusLabel,
      nodeLabel: config.nodeLabel,
    };
    const runs = Array.isArray(config.runs) ? config.runs : [];
    const filteredRuns = Array.isArray(config.filteredRuns) ? config.filteredRuns : [];
    const filters = normalizeFilters(config.filters || {});
    const count = activeCount(filters);
    const runOptions = options(runs);
    const statusLabel = typeof deps.statusLabel === "function" ? deps.statusLabel : (status) => status;
    const nodeLabel = typeof deps.nodeLabel === "function" ? deps.nodeLabel : (kind) => kind;
    return `
      <div class="workspace-run-filterbar">
        <label>
          状态
          <select data-workspace-run-filter="status" title="按 run 状态过滤">
            <option value="">全部</option>
            ${runOptions.statuses.map((status) => `<option value="${escapeFor(deps, status)}" ${filters.status === status ? "selected" : ""}>${escapeFor(deps, statusLabel(status))}</option>`).join("")}
          </select>
        </label>
        <label>
          节点
          <select data-workspace-run-filter="nodeKind" title="按 run step 的 node_kind 过滤">
            <option value="">全部节点</option>
            ${runOptions.nodeKinds.map((kind) => `<option value="${escapeFor(deps, kind)}" ${filters.nodeKind === kind ? "selected" : ""}>${escapeFor(deps, nodeLabel(kind))}</option>`).join("")}
          </select>
        </label>
        <label>
          Job
          <input data-workspace-run-filter="jobId" value="${escapeFor(deps, filters.jobId)}" placeholder="job id" />
        </label>
        <label>
          Agent
          <input data-workspace-run-filter="agentExecutionId" value="${escapeFor(deps, filters.agentExecutionId)}" placeholder="agent execution id" />
        </label>
        <span class="workspace-run-filter-count">${escapeFor(deps, count ? `${filteredRuns.length}/${runs.length}` : `${runs.length}`)} 条</span>
        <button class="secondary mini" type="button" data-action="reset-workspace-run-filters" title="清空运行记录筛选" ${count ? "" : "disabled"}>重置</button>
      </div>
    `;
  }

  window.WorkspaceRunFilter = {
    activeCount,
    barMarkup,
    filterRuns,
    matches,
    normalizeFilters,
    options,
    stepAgentExecutionIds,
    stepJobIds,
    stepList,
  };
})();
