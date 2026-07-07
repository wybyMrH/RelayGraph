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

  window.FilePickerNavigation = {
    forwardNavigationState,
    navigateForward,
    navigateUp,
    navigationButtonState,
    openPath,
    rememberForwardPath,
    resetNavigationState,
  };
})();
