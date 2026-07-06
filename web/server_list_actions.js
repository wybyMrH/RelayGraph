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

  function handleServerListClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const refreshButton = target?.closest("[data-action='refresh-server']");
    if (refreshButton?.dataset.id) {
      call(callbacks, "refreshServer", refreshButton.dataset.id, event, refreshButton);
      return;
    }
    const pinButton = target?.closest("[data-action='pin-server']");
    if (pinButton?.dataset.id) {
      call(callbacks, "pinServer", pinButton.dataset.id, event, pinButton);
      return;
    }
    const item = target?.closest(".server-item[data-id]");
    if (item?.dataset.id) call(callbacks, "selectServer", item.dataset.id, event, item);
  }

  function bind(callbacks = {}) {
    element(callbacks, "serverSortSelect")?.addEventListener("change", (event) => {
      call(callbacks, "setServerSort", event?.target?.value || "default", event);
    });
    element(callbacks, "serverList")?.addEventListener("click", (event) => {
      handleServerListClick(event, callbacks);
    });
  }

  window.ServerListActions = {
    bind,
    handleServerListClick,
  };
})();
