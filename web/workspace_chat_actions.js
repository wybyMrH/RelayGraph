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
    fn(callbacks, name, () => {})(...args);
  }

  function callAsync(callbacks, name, ...args) {
    void fn(callbacks, name, async () => {})(...args);
  }

  function bindChatInput(callbacks = {}) {
    element(callbacks, "workspaceChatInput")?.addEventListener("keydown", (event) => {
      if (!(event.ctrlKey || event.metaKey) || event.key !== "Enter") return;
      event.preventDefault();
      callAsync(callbacks, "submitWorkspaceChat");
    });
  }

  function bindChatList(callbacks = {}) {
    element(callbacks, "workspaceChatList")?.addEventListener("click", (event) => {
      const button = eventTarget(event)?.closest("[data-action]");
      if (button) call(callbacks, "handleAutomationAction", button);
    });
  }

  function bind(callbacks = {}) {
    element(callbacks, "workspaceChatSendBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "submitWorkspaceChat");
    });
    bindChatList(callbacks);
    bindChatInput(callbacks);
    element(callbacks, "workspaceChatAgentSelect")?.addEventListener("change", (event) => {
      call(callbacks, "setWorkspaceChatAgentId", eventTarget(event)?.value || "");
    });
    element(callbacks, "workspaceUseChatAgentSelect")?.addEventListener("change", (event) => {
      call(callbacks, "setWorkspaceUseChatAgentId", String(eventTarget(event)?.value || "").trim());
    });
  }

  window.WorkspaceChatActions = {
    bind,
    bindChatInput,
    bindChatList,
    eventTarget,
  };
})();
