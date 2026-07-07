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

  window.JobState = {
    formatDurationMs,
    isWaitingJob,
    jobDurationMs,
    jobKindGroup,
    jobQueueRank,
    jobSearchKey,
    matchesKindFilter,
    matchesStatusFilter,
    parseDateMs,
  };
})();
