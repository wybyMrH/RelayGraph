(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function call(callbacks, name, ...args) {
    return fn(callbacks, name, () => {})(...args);
  }

  function callAsync(callbacks, name, ...args) {
    void fn(callbacks, name, async () => {})(...args);
  }

  function handleTerminalSessionClick(event, callbacks = {}) {
    const button = eventTarget(event)?.closest("[data-action]");
    if (!button) return;
    const key = button.dataset.outputKey || "";
    if (button.dataset.action === "activate-output-tab" && key) {
      call(callbacks, "activateOutputTab", key);
      return;
    }
    if (button.dataset.action === "close-output-tab" && key) {
      call(callbacks, "closeOutputTab", event, key);
    }
  }

  function bindLogControls(callbacks = {}) {
    element(callbacks, "logRefreshBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "refreshActiveOutput", { forceBottom: true });
    });
    element(callbacks, "logFollow")?.addEventListener("change", () => {
      call(callbacks, "updateLogFollowHint");
    });
    element(callbacks, "logView")?.addEventListener("scroll", () => {
      call(callbacks, "updateLogFollowHint");
    }, { passive: true });
    element(callbacks, "logSearchInput")?.addEventListener("input", (event) => {
      const value = eventTarget(event)?.value || "";
      call(callbacks, "setLogSearchQuery", value, { focusMatch: Boolean(value) });
    });
    element(callbacks, "logSearchPrevBtn")?.addEventListener("click", () => {
      call(callbacks, "moveLogSearch", -1);
    });
    element(callbacks, "logSearchNextBtn")?.addEventListener("click", () => {
      call(callbacks, "moveLogSearch", 1);
    });
    element(callbacks, "logDownloadBtn")?.addEventListener("click", () => {
      call(callbacks, "downloadActiveOutput");
    });
    element(callbacks, "logClearBtn")?.addEventListener("click", () => {
      call(callbacks, "collapseLogPane");
    });
    element(callbacks, "outputCloseActiveBtn")?.addEventListener("click", (event) => {
      call(callbacks, "closeActiveOutputTab", event);
    });
    element(callbacks, "outputCloseAllBtn")?.addEventListener("click", (event) => {
      call(callbacks, "closeAllOutputTabs", event);
    });
  }

  function bindTerminalControls(callbacks = {}) {
    element(callbacks, "terminalInputForm")?.addEventListener("submit", (event) => {
      callAsync(callbacks, "submitTerminalInput", event);
    });
    element(callbacks, "terminalCtrlCBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "sendTerminalSignal", 2);
    });
    element(callbacks, "terminalCloseBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "closeCurrentTerminal");
    });
    element(callbacks, "terminalSessionList")?.addEventListener("click", (event) => {
      handleTerminalSessionClick(event, callbacks);
    });
  }

  function bind(callbacks = {}) {
    bindLogControls(callbacks);
    bindTerminalControls(callbacks);
  }

  window.OutputTerminalActions = {
    bind,
    bindLogControls,
    bindTerminalControls,
    handleTerminalSessionClick,
  };
})();
