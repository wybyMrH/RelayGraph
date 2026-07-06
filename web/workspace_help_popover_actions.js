(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function workspaceHelpTarget(event) {
    return eventTarget(event)?.closest("[data-workspace-help]") || null;
  }

  function containsRelatedTarget(target, event) {
    return Boolean(event?.relatedTarget && target?.contains?.(event.relatedTarget));
  }

  function call(callbacks, name, ...args) {
    fn(callbacks, name, () => {})(...args);
  }

  function handlePointerOver(event, callbacks = {}) {
    const target = workspaceHelpTarget(event);
    if (!target || containsRelatedTarget(target, event)) return;
    call(callbacks, "showWorkspaceHelp", target, event);
  }

  function handlePointerOut(event, callbacks = {}) {
    const target = workspaceHelpTarget(event);
    if (!target || containsRelatedTarget(target, event)) return;
    call(callbacks, "hideWorkspaceHelp", target, event);
  }

  function handleFocusIn(event, callbacks = {}) {
    const target = workspaceHelpTarget(event);
    if (target) call(callbacks, "showWorkspaceHelp", target, event);
  }

  function handleFocusOut(event, callbacks = {}) {
    const target = workspaceHelpTarget(event);
    if (!target || containsRelatedTarget(target, event)) return;
    call(callbacks, "hideWorkspaceHelp", target, event);
  }

  function bind(callbacks = {}) {
    document.addEventListener("pointerover", (event) => {
      handlePointerOver(event, callbacks);
    });
    document.addEventListener("pointerout", (event) => {
      handlePointerOut(event, callbacks);
    });
    document.addEventListener("focusin", (event) => {
      handleFocusIn(event, callbacks);
    });
    document.addEventListener("focusout", (event) => {
      handleFocusOut(event, callbacks);
    });
    window.addEventListener("resize", (event) => {
      call(callbacks, "positionWorkspaceHelp", event);
    });
    window.addEventListener("scroll", (event) => {
      call(callbacks, "positionWorkspaceHelp", event);
    }, true);
  }

  window.WorkspaceHelpPopoverActions = {
    bind,
    containsRelatedTarget,
    handleFocusIn,
    handleFocusOut,
    handlePointerOut,
    handlePointerOver,
    workspaceHelpTarget,
  };
})();
