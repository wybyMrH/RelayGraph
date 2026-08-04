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

  function serverIsReachable(server) {
    if (!server) return false;
    if (typeof server.reachable === "boolean") return server.reachable;
    return Boolean(server.online);
  }

  function serverHasMonitorIssue(server, deps = {}) {
    return Boolean(server)
      && !server.online
      && (typeof deps.serverIsReachable === "function" ? deps.serverIsReachable : serverIsReachable)(server);
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

  function serverOptionLabel(server, deps = {}) {
    const parts = [server.name || server.id || "未命名服务器"];
    const tags = [
      server.online
        ? "在线"
        : (typeof deps.serverIsReachable === "function" ? deps.serverIsReachable : serverIsReachable)(server)
          ? "已连接"
          : "离线",
    ];
    if ((typeof deps.serverHasMonitorIssue === "function" ? deps.serverHasMonitorIssue : serverHasMonitorIssue)(server)) {
      tags.push("GPU 异常");
    }
    const gpuCount = (server.gpus || []).length;
    const busyCount = (typeof deps.serverBusyGpuCount === "function" ? deps.serverBusyGpuCount : serverBusyGpuCount)(server);
    const processCount = (server.processes || []).length;
    if (gpuCount) tags.push(`${busyCount}/${gpuCount} GPU 忙`);
    if (processCount) tags.push(`${processCount} 进程`);
    return `${parts.join("")} · ${tags.join(" · ")}`;
  }

  function serverOptionShortLabel(server, deps = {}) {
    const name = server.name || server.id || "未命名服务器";
    if (server.online) return `${name} · 在线`;
    if ((typeof deps.serverIsReachable === "function" ? deps.serverIsReachable : serverIsReachable)(server)) {
      return (typeof deps.serverHasMonitorIssue === "function" ? deps.serverHasMonitorIssue : serverHasMonitorIssue)(server)
        ? `${name} · 已连接 · GPU 异常`
        : `${name} · 已连接`;
    }
    return `${name} · 离线`;
  }

  function serverOriginalIndex(server, context = {}) {
    const servers = Array.isArray(context.servers) ? context.servers : [];
    return servers.findIndex((item) => item.id === server.id);
  }

  function serverManualIndex(server, context = {}, deps = {}) {
    const serverOrder = Array.isArray(context.serverOrder) ? context.serverOrder : [];
    const index = serverOrder.indexOf(server.id);
    if (index >= 0) return index;
    const originalIndex = typeof deps.serverOriginalIndex === "function" ? deps.serverOriginalIndex : serverOriginalIndex;
    return serverOrder.length + Math.max(originalIndex(server, context), 0);
  }

  function serverPinned(serverId, context = {}) {
    const serverPins = Array.isArray(context.serverPins) ? context.serverPins : [];
    return serverPins.includes(serverId);
  }

  function serverSortScore(server, mode, deps = {}) {
    if (mode === "idle") {
      const idleGpuCount = typeof deps.serverIdleGpuCount === "function" ? deps.serverIdleGpuCount : serverIdleGpuCount;
      return [idleGpuCount(server), (server.gpus || []).length, -((server.processes || []).length)];
    }
    if (mode === "alerts") {
      const busyGpuCount = typeof deps.serverBusyGpuCount === "function" ? deps.serverBusyGpuCount : serverBusyGpuCount;
      return [
        server.online ? 0 : 3,
        server.error ? 2 : 0,
        busyGpuCount(server),
        (server.processes || []).length,
        (server.gpus || []).length,
      ];
    }
    if (mode === "gpus") {
      const idleGpuCount = typeof deps.serverIdleGpuCount === "function" ? deps.serverIdleGpuCount : serverIdleGpuCount;
      return [(server.gpus || []).length, idleGpuCount(server)];
    }
    if (mode === "processes") {
      return [((server.processes || []).length), (server.gpus || []).length];
    }
    return [];
  }

  function compareServerArrays(left, right) {
    const length = Math.max(left.length, right.length);
    for (let index = 0; index < length; index += 1) {
      const delta = Number(right[index] || 0) - Number(left[index] || 0);
      if (delta !== 0) return delta;
    }
    return 0;
  }

  function sortedServersForDisplay(servers, context = {}, deps = {}) {
    const mode = context.serverSort || "default";
    const items = servers.slice();
    const pinned = (serverId) => (typeof deps.serverPinned === "function" ? deps.serverPinned : serverPinned)(serverId, context);
    const manualIndex = (server) => (typeof deps.serverManualIndex === "function" ? deps.serverManualIndex : serverManualIndex)(server, context, deps);
    const originalIndex = (server) => (typeof deps.serverOriginalIndex === "function" ? deps.serverOriginalIndex : serverOriginalIndex)(server, context);
    const sortScore = (server) => (typeof deps.serverSortScore === "function" ? deps.serverSortScore : serverSortScore)(server, mode, deps);
    const compareArrays = (left, right) => (typeof deps.compareServerArrays === "function" ? deps.compareServerArrays : compareServerArrays)(left, right);
    items.sort((a, b) => {
      const pinCompare = Number(pinned(b.id)) - Number(pinned(a.id));
      if (pinCompare !== 0) return pinCompare;
      if (mode === "manual") {
        return manualIndex(a) - manualIndex(b);
      }
      if (mode === "default") {
        return originalIndex(a) - originalIndex(b);
      }
      if (mode === "name") {
        return String(a.name || a.id).localeCompare(String(b.name || b.id), "zh-Hans-CN", {
          numeric: true,
          sensitivity: "base",
        });
      }
      const scoreCompare = compareArrays(sortScore(a), sortScore(b));
      if (scoreCompare !== 0) return scoreCompare;
      const nameCompare = String(a.name || a.id).localeCompare(String(b.name || b.id), "zh-Hans-CN", {
        numeric: true,
        sensitivity: "base",
      });
      if (nameCompare !== 0) return nameCompare;
      return originalIndex(a) - originalIndex(b);
    });
    return items;
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
    compareServerArrays,
    serverCardMarkup,
    serverBusyGpuCount,
    serverHasMonitorIssue,
    serverHostResources,
    serverHostResourceSummary,
    serverIdleGpuCount,
    serverIsReachable,
    serverListEmptyMarkup,
    serverManualIndex,
    serverOnlineEmptyMarkup,
    serverOptionLabel,
    serverOptionShortLabel,
    serverOriginalIndex,
    serverPinned,
    serverSortScore,
    serverSparklineMarkup,
    sortedServersForDisplay,
  };
})();
