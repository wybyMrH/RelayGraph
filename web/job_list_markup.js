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

  function jobListEmptyMarkup(kind = "noJobs") {
    return kind === "noMatches"
      ? '<div class="empty">没有匹配的任务。</div>'
      : '<div class="empty">暂无任务。</div>';
  }

  function jobListItemMarkup(job = {}, options = {}, deps = {}) {
    const active = options.activeClass || "";
    const template = escapeFor(deps, options.templateText || "");
    const commandText = escapeFor(deps, options.commandText || "");
    const progressPct = Number(options.transferProgressPct ?? 0);
    const progress = options.showTransferProgress
      ? `
          <div class="job-progress">
            <div class="bar"><div class="bar-fill${job.status === "running" ? " busy" : ""}" style="width:${progressPct}%"></div></div>
          </div>
        `
      : "";
    return `
        <div class="job-item${active}" onclick="showLog('${escapeFor(deps, job.id)}')">
          <div>
            <div class="job-title" title="${escapeFor(deps, job.name)}">${escapeFor(deps, job.name)}</div>
            <div class="job-line">
              <span class="state ${escapeFor(deps, job.status)}">${escapeFor(deps, options.statusLabel || job.status)}</span>
              <span>${escapeFor(deps, options.kindLabel || job.kind)}${template}</span>
              <span>${escapeFor(deps, options.serverLabel || "-")}</span>
              <span>${escapeFor(deps, options.gpuLabel || "")}</span>
              <span>${escapeFor(deps, options.durationText || "")}</span>
              ${options.queueText ? `<span>${escapeFor(deps, options.queueText)}</span>` : ""}
              <span class="${job.error ? "job-error" : ""}">${escapeFor(deps, options.statusTextLine || "")}</span>
            </div>
            <div class="job-command" title="${commandText}">${commandText}</div>
            ${progress}
          </div>
          <div class="job-actions">
            ${options.canStop ? `<button class="stop-button" type="button" onclick="stopJob(event, '${escapeFor(deps, job.id)}')" title="停止这条任务；不会删除任务记录">停止</button>` : ""}
            ${options.canRetry ? `<button class="secondary mini" type="button" onclick="retryJob(event, '${escapeFor(deps, job.id)}')" title="复制原任务配置并重新加入队列">重试</button>` : ""}
            ${options.canDelete ? `<button class="secondary mini" type="button" onclick="deleteJob(event, '${escapeFor(deps, job.id)}')" title="删除这条已完成或已停止的任务记录">删除</button>` : ""}
            ${options.canReorder ? `<button class="secondary mini" type="button" onclick="reorderQueuedJob(event, '${escapeFor(deps, job.id)}', 'top')" title="把这条排队任务移动到队列最前">置顶</button>` : ""}
            ${options.canReorder ? `<button class="secondary mini" type="button" onclick="reorderQueuedJob(event, '${escapeFor(deps, job.id)}', 'up')" title="把这条排队任务向前移动一位">上移</button>` : ""}
            ${options.canReorder ? `<button class="secondary mini" type="button" onclick="reorderQueuedJob(event, '${escapeFor(deps, job.id)}', 'down')" title="把这条排队任务向后移动一位">下移</button>` : ""}
            <button class="secondary mini" type="button" onclick="loadJobIntoExecution(event, '${escapeFor(deps, job.id)}')" title="把这条任务的命令、服务器、GPU 和目录填回执行面板">填回执行</button>
            <button class="secondary mini" type="button" onclick="copyJob(event, '${escapeFor(deps, job.id)}')" title="把这条任务复制成新的待运行任务">复制入队</button>
          </div>
        </div>
      `;
  }

  window.JobListMarkup = {
    jobListEmptyMarkup,
    jobListItemMarkup,
  };
})();
