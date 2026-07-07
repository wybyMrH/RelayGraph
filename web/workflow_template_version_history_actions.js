(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function currentTemplateForCopy(deps = {}) {
    const draft = fn(deps, "draftTemplate", () => null)();
    if (draft && typeof draft === "object" && Object.keys(draft).length) return draft;
    return fn(deps, "selectedTemplate", () => null)();
  }

  async function copyHistory(deps = {}) {
    const template = currentTemplateForCopy(deps);
    const payload = fn(deps, "auditPayload", () => ({ history_count: 0 }))(template || {});
    const setMessage = fn(deps, "setMessage", () => {});
    if (!payload.history_count) {
      setMessage("当前模板还没有可复制的版本历史。", true);
      return;
    }
    await fn(deps, "copyText", async () => {})(JSON.stringify(payload, null, 2));
    setMessage("模板版本历史 JSON 已复制。");
  }

  window.WorkflowTemplateVersionHistoryActions = {
    copyHistory,
  };
})();
