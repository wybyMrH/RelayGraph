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

  window.FilePickerNavigation = {
    forwardNavigationState,
    navigationButtonState,
    rememberForwardPath,
    resetNavigationState,
  };
})();
