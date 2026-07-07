(function () {
  "use strict";

  function parseTransferProgress(job, log) {
    if (job.status === "done") return 100;
    const matches = Array.from(String(log || "").matchAll(/(?:^|\s)(\d{1,3})%\s/g));
    const last = matches.length ? Number(matches[matches.length - 1][1]) : 0;
    return Math.max(0, Math.min(100, Number.isFinite(last) ? last : 0));
  }

  function lastTransferLine(log) {
    const lines = String(log || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => !line.startsWith("[total-control] command:"));
    return lines.slice(-1)[0] || "等待输出...";
  }

  window.TransferProgressState = {
    lastTransferLine,
    parseTransferProgress,
  };
})();
