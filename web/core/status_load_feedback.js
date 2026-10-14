(function () {
  "use strict";

  function describe(feedback = {}, busy = false) {
    const phase = feedback.phase || "idle";
    const failure = feedback.failure;
    const budget = feedback.seconds ? `状态读取最多等待 ${feedback.seconds} 秒。` : "";
    let label = "等待读取状态";
    let detail = "使用“刷新状态”读取最新监控信息。";
    if (phase === "loading") {
      label = failure ? "正在重试读取" : "正在读取状态";
      detail = budget + "后台任务独立运行。";
    } else if (phase === "timeout" || phase === "error") {
      label = phase === "timeout" ? "状态读取超时" : "状态读取失败";
      detail = (busy ? "仍有状态读取进行中，结束后可重试。" : "可以重试刷新。") + "后台任务不会因此停止。";
    } else if (phase === "ready") {
      label = busy ? "仍有状态读取进行中" : "状态读取完成";
      detail = busy ? "最新一次读取已完成，仍在等待其他状态读取结束。" : budget + "后台任务独立运行。";
    } else if (phase === "replaced") {
      label = "读取已被更新操作替代";
      detail = "本次读取未用于确认完整状态，可刷新重新读取。";
    }
    return {
      phase,
      label,
      detail,
      error: failure ? String(failure.message || "") : "",
      button: busy ? "读取中" : failure ? "重试刷新" : "刷新状态",
    };
  }

  function render(feedback, options = {}) {
    const { elements = {}, busy = false, announce = false } = options;
    const view = describe(feedback, busy);
    if (elements.root) elements.root.dataset.phase = view.phase;
    if (elements.label) elements.label.textContent = view.label;
    if (elements.detail) {
      elements.detail.textContent = view.detail;
      elements.detail.hidden = !view.detail;
    }
    if (elements.error) {
      elements.error.textContent = view.error;
      elements.error.hidden = !view.error;
    }
    if (elements.button) {
      elements.button.disabled = busy;
      elements.button.setAttribute("aria-busy", String(busy));
      elements.button.setAttribute("aria-label", view.button);
      elements.button.title = busy ? "正在读取状态，请等待本次读取结束" : "读取最新监控状态，保留正在编辑的选项卡";
    }
    if (elements.buttonLabel) elements.buttonLabel.textContent = view.button;
    // Routine polling stays quiet; initial/manual reads, failures and recovery can announce.
    if (announce && elements.announcement && elements.announcement.textContent !== view.label) {
      elements.announcement.textContent = view.label;
    }
  }

  window.AppStatusFeedback = { describe, render };
})();
