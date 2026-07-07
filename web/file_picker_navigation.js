(function () {
  "use strict";

  function normalizeFor(options = {}, value = "") {
    const normalize = typeof options.normalizePathForCompare === "function"
      ? options.normalizePathForCompare
      : (item) => String(item || "").trim().replace(/\/+$/, "").toLowerCase();
    return normalize(value);
  }

  function resetNavigationState(filePicker = {}) {
    return {
      ...(filePicker && typeof filePicker === "object" ? filePicker : {}),
      navStack: [],
      forwardStack: [],
      selectedPath: "",
      scrollAnchorPath: "",
    };
  }

  function rememberForwardPath(forwardStack = [], path = "", options = {}) {
    const value = String(path || "").trim();
    if (!value) return Array.isArray(forwardStack) ? forwardStack.slice() : [];
    const limit = Math.max(1, Number(options.limit || 8));
    const normalized = normalizeFor(options, value);
    return [
      value,
      ...(Array.isArray(forwardStack) ? forwardStack : [])
        .filter((item) => normalizeFor(options, item) !== normalized),
    ].slice(0, limit);
  }

  function navigationButtonState(filePicker = {}) {
    return {
      canGoUp: Boolean(filePicker?.parent),
      canGoForward: Boolean(Array.isArray(filePicker?.forwardStack) && filePicker.forwardStack.length),
    };
  }

  function updateNavigationButtons(deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : {};
    const filePicker = state.filePicker && typeof state.filePicker === "object" ? state.filePicker : {};
    const getElement = typeof deps.getElement === "function" ? deps.getElement : () => null;
    const upBtn = getElement("filePickerUpBtn");
    const forwardBtn = getElement("filePickerForwardBtn");
    const buttonState = navigationButtonState(filePicker);
    if (upBtn) upBtn.hidden = !buttonState.canGoUp;
    if (forwardBtn) forwardBtn.hidden = !buttonState.canGoForward;
  }

  function findRow(path = "", deps = {}) {
    const getElement = typeof deps.getElement === "function" ? deps.getElement : () => null;
    const list = getElement("filePickerList");
    if (!list || !path) return null;
    const target = normalizeFor(deps, path);
    for (const row of list.querySelectorAll(".file-picker-row")) {
      if (normalizeFor(deps, row.dataset.path || "") === target) return row;
    }
    return null;
  }

  function restoreScrollAfterRender(deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : {};
    const filePicker = state.filePicker && typeof state.filePicker === "object" ? state.filePicker : {};
    const anchor = filePicker.scrollAnchorPath;
    if (!anchor) return;
    const schedule = typeof deps.requestAnimationFrame === "function"
      ? deps.requestAnimationFrame
      : (callback) => window.requestAnimationFrame(callback);
    schedule(() => {
      const row = findRow(anchor, deps);
      if (row) row.scrollIntoView({ block: "center", inline: "nearest" });
      const latestFilePicker = state.filePicker && typeof state.filePicker === "object" ? state.filePicker : null;
      if (latestFilePicker) latestFilePicker.scrollAnchorPath = "";
    });
  }

  function forwardNavigationState(filePicker = {}) {
    const forwardStack = Array.isArray(filePicker?.forwardStack) ? filePicker.forwardStack.slice() : [];
    const nextPath = forwardStack.shift() || "";
    if (!nextPath) {
      return {
        nextPath: "",
        forwardStack,
        navStack: Array.isArray(filePicker?.navStack) ? filePicker.navStack.slice() : [],
        selectedPath: filePicker?.selectedPath || "",
      };
    }
    const navStack = Array.isArray(filePicker?.navStack) ? filePicker.navStack.slice() : [];
    if (filePicker?.path) navStack.push(nextPath);
    return {
      nextPath,
      forwardStack,
      navStack,
      selectedPath: nextPath,
    };
  }

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function filePickerState(deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : {};
    if (!state.filePicker || typeof state.filePicker !== "object") state.filePicker = {};
    if (!Array.isArray(state.filePicker.forwardStack)) state.filePicker.forwardStack = [];
    if (!Array.isArray(state.filePicker.navStack)) state.filePicker.navStack = [];
    return state.filePicker;
  }

  async function navigateForward(deps = {}) {
    const filePicker = filePickerState(deps);
    const forwardState = forwardNavigationState(filePicker);
    filePicker.forwardStack = forwardState.forwardStack;
    if (!forwardState.nextPath) {
      fn(deps, "updateFilePickerNavigationButtons", () => {})();
      return;
    }
    filePicker.navStack = forwardState.navStack;
    filePicker.selectedPath = forwardState.selectedPath;
    await fn(deps, "loadFilePicker", async () => {})(forwardState.nextPath);
  }

  async function navigateUp(deps = {}) {
    const filePicker = filePickerState(deps);
    if (!filePicker.parent) return;
    fn(deps, "rememberFilePickerForwardPath", () => {})(filePicker.path);
    const anchor = filePicker.navStack.pop();
    if (anchor) {
      filePicker.scrollAnchorPath = anchor;
      filePicker.selectedPath = anchor;
    }
    await fn(deps, "loadFilePicker", async () => {})(filePicker.parent);
  }

  async function openPath(path = "", deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : {};
    state.filePicker = resetNavigationState(state.filePicker);
    await fn(deps, "loadFilePicker", async () => {})(path);
  }

  async function activateRow(path = "", isDir = false, deps = {}) {
    const filePicker = filePickerState(deps);
    filePicker.selectedPath = path;
    if (isDir) {
      filePicker.forwardStack = [];
      filePicker.navStack.push(path);
      await fn(deps, "loadFilePicker", async () => {})(path);
      return;
    }
    await fn(deps, "previewFileInPicker", async () => {})(path);
  }

  async function previewPath(path = "", deps = {}) {
    const filePicker = filePickerState(deps);
    filePicker.selectedPath = path;
    await fn(deps, "previewFileInPicker", async () => {})(path);
  }

  function markPathInputChanged(deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : {};
    const filePicker = state.filePicker || {};
    filePicker.requestId = (filePicker.requestId || 0) + 1;
  }

  window.FilePickerNavigation = {
    activateRow,
    findRow,
    forwardNavigationState,
    markPathInputChanged,
    navigateForward,
    navigateUp,
    navigationButtonState,
    openPath,
    previewPath,
    rememberForwardPath,
    resetNavigationState,
    restoreScrollAfterRender,
    updateNavigationButtons,
  };
})();
