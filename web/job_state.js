(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function parseDateMs(value) {
    const ms = Date.parse(value || "");
    return Number.isFinite(ms) ? ms : 0;
  }

  function formatDurationMs(value) {
    const totalSeconds = Math.max(0, Math.round(Number(value || 0) / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
  }

  function jobDurationMs(job, deps = {}) {
    const parseMs = fn(deps, "parseDateMs", parseDateMs);
    const now = fn(deps, "now", () => Date.now());
    const start = parseMs(job.started_at || job.created_at);
    const end = parseMs(job.finished_at) || now();
    if (!start || end < start) return 0;
    return end - start;
  }

  function isWaitingJob(job) {
    return ["queued", "blocked"].includes(String(job?.status || ""));
  }

  function jobKindGroup(job) {
    const kind = String(job?.kind || "");
    if (kind === "transfer") return "transfer";
    if (kind === "profile") return "profile";
    if (kind.includes("batch")) return "batch";
    return "command";
  }

  function jobQueueRank(job) {
    const rank = Number(job?.queue_rank || 0);
    return Number.isFinite(rank) && rank > 0 ? rank : Number.MAX_SAFE_INTEGER;
  }

  function jobSearchKey(job) {
    return [
      job.id,
      job.name,
      job.kind,
      job.command_display || job.command,
      job.error,
      job.server_id,
      job.requested_server_id,
    ]
      .join(" ")
      .toLowerCase();
  }

  function matchesKindFilter(job, value) {
    if (!value) return true;
    return jobKindGroup(job) === value;
  }

  function matchesStatusFilter(job, value) {
    if (!value) return true;
    const status = String(job.status || "");
    if (value === "running") return ["running", "starting"].includes(status);
    if (value === "waiting") return ["queued", "blocked"].includes(status);
    if (value === "done") return status === "done";
    if (value === "failed") return ["failed", "stopped"].includes(status);
    if (value === "transfer") return job.kind === "transfer";
    return status === value;
  }

  function waitingQueuePositions(jobs = [], deps = {}) {
    const waiting = fn(deps, "isWaitingJob", isWaitingJob);
    const rank = fn(deps, "jobQueueRank", jobQueueRank);
    return new Map(
      jobs
        .filter((job) => waiting(job))
        .slice()
        .sort((left, right) => rank(left) - rank(right))
        .map((job, index) => [job.id, index + 1]),
    );
  }

  function filteredJobs(jobs = [], filters = {}, deps = {}) {
    const searchKey = fn(deps, "jobSearchKey", jobSearchKey);
    const statusFilter = fn(deps, "jobMatchesStatusFilter", matchesStatusFilter);
    const kindFilter = fn(deps, "jobMatchesKindFilter", matchesKindFilter);
    const durationMs = fn(deps, "jobDurationMs", jobDurationMs);
    const parseMs = fn(deps, "parseDateMs", parseDateMs);
    const waiting = fn(deps, "isWaitingJob", isWaitingJob);
    const rank = fn(deps, "jobQueueRank", jobQueueRank);
    const query = filters.query.trim().toLowerCase();
    const serverId = filters.server;
    const status = filters.status;
    const kind = filters.kind;
    const sort = filters.sort || "created_desc";
    const items = jobs
      .filter((job) => {
        if (query && !searchKey(job).includes(query)) return false;
        if (serverId && String(job.server_id || "") !== serverId && String(job.requested_server_id || "") !== serverId) return false;
        if (!statusFilter(job, status)) return false;
        if (!kindFilter(job, kind)) return false;
        return true;
      });
    items.sort((left, right) => {
      if (sort === "queue") {
        const leftWaiting = waiting(left);
        const rightWaiting = waiting(right);
        if (leftWaiting && rightWaiting) return rank(left) - rank(right);
        if (leftWaiting || rightWaiting) return leftWaiting ? -1 : 1;
      }
      if (sort === "duration_desc") {
        const delta = durationMs(right) - durationMs(left);
        if (delta !== 0) return delta;
      }
      const leftCreated = parseMs(left.created_at);
      const rightCreated = parseMs(right.created_at);
      if (sort === "created_asc") return leftCreated - rightCreated;
      return rightCreated - leftCreated;
    });
    return items.slice(0, 100);
  }

  window.JobState = {
    filteredJobs,
    formatDurationMs,
    isWaitingJob,
    jobDurationMs,
    jobKindGroup,
    jobQueueRank,
    jobSearchKey,
    matchesKindFilter,
    matchesStatusFilter,
    parseDateMs,
    waitingQueuePositions,
  };
})();
