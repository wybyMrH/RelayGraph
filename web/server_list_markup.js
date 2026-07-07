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

  function serverListEmptyMarkup() {
    return '<div class="empty">暂无服务器配置。</div>';
  }

  function serverOnlineEmptyMarkup() {
    return '<div class="empty">暂无已连接服务器。</div>';
  }

  function fallbackFormatPercent(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "--";
    return `${Math.max(0, Math.min(100, n)).toFixed(n % 1 === 0 ? 0 : 1)}%`;
  }

  function formatPercentFor(deps, value) {
    return (typeof deps.formatPercent === "function" ? deps.formatPercent : fallbackFormatPercent)(value);
  }

  function serverBusyGpuCount(server) {
    return (server.gpus || []).filter((gpu) => gpu.state === "busy").length;
  }

  function serverIdleGpuCount(server, deps = {}) {
    const countBusy = typeof deps.serverBusyGpuCount === "function"
      ? deps.serverBusyGpuCount
      : serverBusyGpuCount;
    return Math.max((server.gpus || []).length - countBusy(server), 0);
  }

  function serverHostResources(server) {
    const resources = server?.host_resources;
    return resources && typeof resources === "object" ? resources : {};
  }

  function serverHostResourceSummary(server, deps = {}) {
    const resources = typeof deps.serverHostResources === "function"
      ? deps.serverHostResources(server)
      : serverHostResources(server);
    if (!Object.keys(resources).length) {
      return {
        badge: "主机待采集",
        title: "等待主机 CPU、内存、磁盘和网络资源快照",
        state: "muted",
      };
    }
    if (resources.ok === false) {
      return {
        badge: "主机异常",
        title: resources.error || "主机资源采集失败",
        state: "warning",
      };
    }
    const cpu = resources.cpu || {};
    const memory = resources.memory || {};
    const cpuText = formatPercentFor(deps, cpu.util_percent);
    const memText = formatPercentFor(deps, memory.used_percent);
    return {
      badge: `主机 ${cpuText}/${memText}`,
      title: `CPU ${cpuText} · 内存 ${memText} · 悬停查看磁盘和网络`,
      state: "ok",
    };
  }

  function serverSparklineMarkup(series = [], maxValue = 1, variant = "", deps = {}) {
    return `
    <div class="server-sparkline${variant ? ` ${escapeFor(deps, variant)}` : ""}">
      ${(series.length ? series : [0]).map((value) => {
        const ratio = maxValue > 0 ? value / maxValue : 0;
        const height = Math.max(3, Math.round(ratio * 100));
        return `<span style="height:${height}%"></span>`;
      }).join("")}
    </div>
  `;
  }

  function serverHostBadgeMarkup(options = {}, deps = {}) {
    return `<span class="server-badge${options.hostBadgeClass || ""}" title="${escapeFor(deps, options.hostBadgeTitle)}">${escapeFor(deps, options.hostBadge)}</span>`;
  }

  function serverHealthMarkup(options = {}, deps = {}) {
    const hostBadge = serverHostBadgeMarkup(options, deps);
    const errorText = options.errorText || "";
    if (options.compact) {
      return `
          <div class="server-health">
            <span class="server-badge danger">连接失败</span>
            ${hostBadge}
            ${errorText ? `<span class="server-badge danger" title="${escapeFor(deps, errorText)}">异常</span>` : ""}
          </div>
          ${errorText ? `<div class="server-error" title="${escapeFor(deps, errorText)}">${escapeFor(deps, errorText)}</div>` : ""}
        `;
    }
    if (options.monitorBlocked) {
      const monitorText = errorText || "GPU 监控未上线";
      return `
          <div class="server-health">
            <span class="server-badge warning">${escapeFor(deps, options.connectivityText)}</span>
            <span class="server-badge danger" title="GPU / CUDA 监控采集失败">GPU 异常</span>
            ${hostBadge}
          </div>
          <div class="server-error" title="${escapeFor(deps, monitorText)}">${escapeFor(deps, monitorText)}</div>
        `;
    }
    return `
          <div class="server-health">
            <span class="server-badge" title="${escapeFor(deps, `${options.idleCount} 空闲 / ${options.gpuCount} GPU`)}">${escapeFor(deps, `${options.idleCount}闲/${options.gpuCount}卡`)}</span>
            <span class="server-badge subtle" title="${escapeFor(deps, `${options.busyGpuCount} 张 GPU 忙碌`)}">${escapeFor(deps, `${options.busyGpuCount}忙`)}</span>
            <span class="server-badge subtle" title="${escapeFor(deps, `${options.processCount} 个进程`)}">${escapeFor(deps, `${options.processCount}进程`)}</span>
            ${hostBadge}
            ${errorText ? `<span class="server-badge danger" title="${escapeFor(deps, errorText)}">${escapeFor(deps, errorText)}</span>` : ""}
          </div>
          <div class="server-trends">
            <div class="server-trend">
              <span>忙碌 GPU</span>
              ${serverSparklineMarkup(options.busySeries || [], options.busyMax, "", deps)}
              <strong>${escapeFor(deps, options.busyGpuCount)}</strong>
            </div>
            <div class="server-trend">
              <span>进程数</span>
              ${serverSparklineMarkup(options.processSeries || [], options.processMax, "process", deps)}
              <strong>${escapeFor(deps, options.processCount)}</strong>
            </div>
          </div>
        `;
  }

  function serverCardMarkup(server = {}, options = {}, deps = {}) {
    const health = serverHealthMarkup(options, deps);
    return `
      <div
        class="server-item${options.activeClass || ""}${options.manual ? " manual" : ""}${options.compact ? " compact" : ""}${options.monitorBlocked ? " degraded" : ""}"
        data-id="${escapeFor(deps, server.id)}"
        draggable="${options.manual ? "true" : "false"}"
      >
        <div class="server-item-head">
          <div class="server-name">
            <span title="${escapeFor(deps, server.name)}">${escapeFor(deps, server.name)}</span>
            <span class="dot${options.dotState || ""}"></span>
          </div>
          <div class="server-item-actions">
            <button
              class="server-refresh${options.refreshing ? " busy" : ""}"
              type="button"
              title="只刷新这台服务器的 GPU、显存、进程和连接状态；不会重画工作台"
              data-action="refresh-server"
              data-id="${escapeFor(deps, server.id)}"
              ${options.refreshing ? "disabled" : ""}
            >${options.refreshing ? "…" : "↻"}</button>
            <button
              class="server-pin${options.pinned ? " active" : ""}"
              type="button"
              title="${options.pinned ? "取消置顶" : "置顶"}"
              data-action="pin-server"
              data-id="${escapeFor(deps, server.id)}"
            >★</button>
            <button class="server-drag" type="button" title="拖拽排序" tabindex="-1">⋮⋮</button>
          </div>
        </div>
        <div class="server-meta-row">
          <div class="server-meta" title="${escapeFor(deps, options.target)}">${escapeFor(deps, options.target)}</div>
          <span class="server-rank">${escapeFor(deps, options.rankText)}</span>
        </div>
        ${health}
      </div>
    `;
  }

  function offlineServerGroupMarkup(offlineHtml = "", count = 0, open = false, deps = {}) {
    return `
        <details
          id="offlineServerGroup"
          class="offline-group"
          ${open ? "open" : ""}
        >
          <summary>
            <span>连接失败</span>
            <strong>${escapeFor(deps, count)}</strong>
          </summary>
          <div class="offline-list">
            ${offlineHtml}
          </div>
        </details>
      `;
  }

  window.ServerListMarkup = {
    offlineServerGroupMarkup,
    serverCardMarkup,
    serverBusyGpuCount,
    serverHostResources,
    serverHostResourceSummary,
    serverIdleGpuCount,
    serverListEmptyMarkup,
    serverOnlineEmptyMarkup,
    serverSparklineMarkup,
  };
})();
