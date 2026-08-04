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

  function statusFor(deps, status) {
    return typeof deps.zhStatus === "function" ? deps.zhStatus(status) : String(status || "");
  }

  function transferProgressEmptyMarkup() {
    return '<div class="empty compact-empty">暂无文件传输任务。</div>';
  }

  function transferProgressItemMarkup(job = {}, options = {}, deps = {}) {
    const pct = Number(options.pct ?? 0);
    const line = options.line || "";
    const canStop = Boolean(options.canStop);
    return `
        <div class="transfer-progress-item" onclick="showLog('${escapeFor(deps, job.id)}')">
          <div class="transfer-progress-head">
            <span class="transfer-progress-name" title="${escapeFor(deps, job.name)}">${escapeFor(deps, job.name)}</span>
            <span class="transfer-progress-actions">
              <span class="state ${escapeFor(deps, job.status)}">${escapeFor(deps, statusFor(deps, job.status))} · ${pct}%</span>
              ${canStop ? `<button class="stop-button compact" type="button" onclick="stopJob(event, '${escapeFor(deps, job.id)}')" title="取消这条文件传输任务">取消</button>` : ""}
            </span>
          </div>
          <div class="bar"><div class="bar-fill${job.status === "running" ? " busy" : ""}" style="width:${pct}%"></div></div>
          <div class="transfer-progress-line" title="${escapeFor(deps, line)}">${escapeFor(deps, line)}</div>
        </div>
      `;
  }

  window.TransferProgressMarkup = {
    transferProgressEmptyMarkup,
    transferProgressItemMarkup,
  };
})();
