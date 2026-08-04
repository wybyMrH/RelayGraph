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

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function transferState(deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : {};
    if (!state.transfer || typeof state.transfer !== "object") state.transfer = {};
    if (!Array.isArray(state.transfer.sourceForwardStack)) state.transfer.sourceForwardStack = [];
    if (!Array.isArray(state.transfer.targetForwardStack)) state.transfer.targetForwardStack = [];
    return state.transfer;
  }

  async function navigateSourceParent(deps = {}) {
    const transfer = transferState(deps);
    const parentDirectoryPath = fn(deps, "parentDirectoryPath", () => "");
    const sourceValue = fn(deps, "transferSourceValue", () => "");
    const parent = parentDirectoryPath(transfer.source?.path || sourceValue());
    if (!parent) return;
    await fn(deps, "loadTransferSourceTree", async () => {})(parent, { rememberForward: true });
  }

  async function navigateSourceForward(deps = {}) {
    const transfer = transferState(deps);
    const forwardState = forwardNavigationState(transfer.sourceForwardStack);
    transfer.sourceForwardStack = forwardState.forwardStack;
    if (!forwardState.nextPath) {
      fn(deps, "updateTransferTreeClearButtons", () => {})();
      return;
    }
    await fn(deps, "loadTransferSourceTree", async () => {})(forwardState.nextPath, { keepForward: true });
  }

  async function navigateTargetParent(deps = {}) {
    const transfer = transferState(deps);
    const parentDirectoryPath = fn(deps, "parentDirectoryPath", () => "");
    const targetValue = fn(deps, "transferTargetValue", () => "");
    const parent = parentDirectoryPath(transfer.target?.path || targetValue());
    if (!parent) return;
    await fn(deps, "loadTransferTargetTree", async () => {})(parent, { rememberForward: true });
  }

  async function navigateTargetForward(deps = {}) {
    const transfer = transferState(deps);
    const forwardState = forwardNavigationState(transfer.targetForwardStack);
    transfer.targetForwardStack = forwardState.forwardStack;
    if (!forwardState.nextPath) {
      fn(deps, "updateTransferTreeClearButtons", () => {})();
      return;
    }
    await fn(deps, "loadTransferTargetTree", async () => {})(forwardState.nextPath, { keepForward: true });
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
    navigateSourceForward,
    navigateSourceParent,
    navigateTargetForward,
    navigateTargetParent,
    treeButtonState,
  };
})();
