(function () {
  "use strict";

  function normalizeFor(options = {}, value = "") {
    const normalize = typeof options.normalizePathForCompare === "function"
      ? options.normalizePathForCompare
      : (item) => String(item || "").trim().replace(/\/+$/, "").toLowerCase();
    return normalize(value);
  }

  function rememberForwardStack(forwardStack = [], previousPath = "", targetPath = "", options = {}) {
    const previous = String(previousPath || "").trim();
    if (!previous) return Array.isArray(forwardStack) ? forwardStack.slice() : [];
    if (normalizeFor(options, previous) === normalizeFor(options, targetPath)) {
      return Array.isArray(forwardStack) ? forwardStack.slice() : [];
    }
    const limit = Math.max(1, Number(options.limit || 8));
    const normalized = normalizeFor(options, previous);
    return [
      previous,
      ...(Array.isArray(forwardStack) ? forwardStack : [])
        .filter((item) => normalizeFor(options, item) !== normalized),
    ].slice(0, limit);
  }

  function forwardNavigationState(forwardStack = []) {
    const stack = Array.isArray(forwardStack) ? forwardStack.slice() : [];
    const nextPath = stack.shift() || "";
    return { nextPath, forwardStack: stack };
  }

  function treeButtonState(transfer = {}, options = {}) {
    const parentDirectoryPath = typeof options.parentDirectoryPath === "function"
      ? options.parentDirectoryPath
      : () => "";
    return {
      sourceClear: Boolean(transfer.source),
      targetClear: Boolean(transfer.target),
      sourceUp: Boolean(parentDirectoryPath(transfer.source?.path || "")),
      targetUp: Boolean(parentDirectoryPath(transfer.target?.path || "")),
      sourceForward: Boolean(Array.isArray(transfer.sourceForwardStack) && transfer.sourceForwardStack.length),
      targetForward: Boolean(Array.isArray(transfer.targetForwardStack) && transfer.targetForwardStack.length),
    };
  }

  window.TransferTreeNavigation = {
    forwardNavigationState,
    rememberForwardStack,
    treeButtonState,
  };
})();
