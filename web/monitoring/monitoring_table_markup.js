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

  function gpuRowsEmptyMarkup() {
    return '<tr><td colspan="6" class="empty">暂无 GPU 数据。</td></tr>';
  }

  function gpuRowMarkup(server = {}, gpu = {}, options = {}, deps = {}) {
    const serverSelected = options.serverSelectedClass || "";
    const selected = options.selectedClass || "";
    const busy = options.busyClass || "";
    const pct = options.pct ?? 0;
    const utilText = options.utilText ?? "";
    const utilTitle = options.utilTitle ?? "";
    const stateTitle = options.stateTitle ?? "";
    const memoryText = options.memoryText ?? "";
    const temperatureText = options.temperatureText ?? "";
    return `
        <tr class="gpu-row${serverSelected}${selected}" data-server-id="${escapeFor(deps, server.id)}" data-gpu-index="${escapeFor(deps, gpu.index)}" onclick="selectGpu('${escapeFor(deps, server.id)}', '${escapeFor(deps, gpu.index)}')" title="点击后在右侧高亮这张 GPU 上的进程">
          <td>${escapeFor(deps, server.name)}</td>
          <td><div class="gpu-name" title="${escapeFor(deps, gpu.name)}">#${escapeFor(deps, gpu.index)} ${escapeFor(deps, gpu.name)}</div></td>
          <td class="mem-cell">
            <div class="bar"><div class="bar-fill${busy}" style="width:${pct}%"></div></div>
            <span class="muted">${escapeFor(deps, memoryText)}</span>
          </td>
          <td title="${escapeFor(deps, utilTitle)}">${escapeFor(deps, utilText)}</td>
          <td>${escapeFor(deps, temperatureText)}</td>
          <td><span class="state ${escapeFor(deps, gpu.state)}" title="${escapeFor(deps, stateTitle)}">${escapeFor(deps, stateTitle)}</span></td>
        </tr>
      `;
  }

  function processRowsEmptyMarkup(kind = "noProcesses") {
    return kind === "noMatches"
      ? '<tr><td colspan="7" class="empty">没有匹配的进程。</td></tr>'
      : '<tr><td colspan="7" class="empty">当前在线服务器未报告 CUDA 计算进程。</td></tr>';
  }

  function processRowMarkup(server = {}, process = {}, options = {}, deps = {}) {
    const focusClass = options.focusClass || "";
    const gpuText = options.gpuText ?? "";
    const pidText = options.pidText ?? "";
    const userText = options.userText ?? "";
    const memoryText = options.memoryText ?? "";
    const commandText = options.commandText ?? "";
    const serverTitle = options.serverTitle ?? server.name ?? server.id ?? "";
    return `
      <tr class="process-row${focusClass}" data-server-id="${escapeFor(deps, server.id)}" data-gpu-index="${escapeFor(deps, process.gpu_index ?? "")}" data-pid="${escapeFor(deps, process.pid)}" onclick="showProcessCommand('${escapeFor(deps, server.id)}', '${escapeFor(deps, process.pid)}')">
        <td class="process-action-cell">
          <button class="stop-button compact" type="button" onclick="stopProcess(event, '${escapeFor(deps, server.id)}', '${escapeFor(deps, process.pid)}')" title="向这个 CUDA 进程发送停止信号">关闭</button>
        </td>
        <td class="process-server-cell" title="${escapeFor(deps, serverTitle)}">${escapeFor(deps, server.name)}</td>
        <td>${escapeFor(deps, gpuText)}</td>
        <td>${escapeFor(deps, pidText)}</td>
        <td title="${escapeFor(deps, userText)}">${escapeFor(deps, userText)}</td>
        <td>${escapeFor(deps, memoryText)}</td>
        <td class="process-command-cell"><div class="cmd" title="${escapeFor(deps, commandText)}">${escapeFor(deps, commandText)}</div></td>
      </tr>
    `;
  }

  window.MonitoringTableMarkup = {
    gpuRowMarkup,
    gpuRowsEmptyMarkup,
    processRowMarkup,
    processRowsEmptyMarkup,
  };
})();
