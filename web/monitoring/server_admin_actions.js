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

  function aliasValueFor(list, id) {
    const input = Array.from(list?.querySelectorAll?.(".alias-input[data-id]") || [])
      .find((item) => item.dataset.id === id);
    return input?.value || "";
  }

  function handleAdminServerListClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const save = target?.closest(".alias-save[data-id]");
    const list = element(callbacks, "adminServerList");
    if (save?.dataset.id) {
      callAsync(callbacks, "saveAlias", save.dataset.id, aliasValueFor(list, save.dataset.id));
      return;
    }
    const remove = target?.closest(".alias-remove[data-id]");
    if (remove?.dataset.id) {
      callAsync(callbacks, "removeServer", remove.dataset.id);
      return;
    }
    const check = target?.closest(".server-check[data-id]");
    if (check?.dataset.id) {
      callAsync(callbacks, "checkServer", check.dataset.id);
      return;
    }
    const edit = target?.closest(".server-edit[data-id]");
    if (edit?.dataset.id) {
      call(callbacks, "editServer", edit.dataset.id);
    }
  }

  function handleHiddenListClick(event, callbacks = {}) {
    const restore = eventTarget(event)?.closest(".restore-btn[data-alias]");
    if (restore?.dataset.alias) callAsync(callbacks, "restoreDiscovery", restore.dataset.alias);
  }

  function bindModalControls(callbacks = {}) {
    element(callbacks, "manageServersBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "openServerModal");
    });
    element(callbacks, "closeModalBtn")?.addEventListener("click", () => {
      call(callbacks, "closeServerModal");
    });
    element(callbacks, "serverModal")?.addEventListener("click", (event) => {
      if (event.target?.id === "serverModal") call(callbacks, "closeServerModal");
    });
    element(callbacks, "addServerForm")?.addEventListener("submit", (event) => {
      callAsync(callbacks, "addServer", event);
    });
    element(callbacks, "addServerForm")?.querySelector?.(".cancel-edit-btn")?.addEventListener("click", () => {
      call(callbacks, "cancelEdit");
    });
  }

  function bindRuntimeStorageControls(callbacks = {}) {
    element(callbacks, "runtimeStorageSaveBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "saveRuntimeStorageSettings");
    });
    element(callbacks, "runtimeStorageCleanupBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "cleanupRuntimeStorage", false);
    });
    element(callbacks, "runtimeStoragePurgeBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "cleanupRuntimeStorage", true);
    });
    element(callbacks, "runtimeStateCleanupBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "cleanupRuntimeState");
    });
    element(callbacks, "runtimeStorageResetBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "resetRuntimeStorageSettings");
    });
  }

  function bindAdminLists(callbacks = {}) {
    element(callbacks, "adminServerList")?.addEventListener("click", (event) => {
      handleAdminServerListClick(event, callbacks);
    });
    element(callbacks, "hiddenList")?.addEventListener("click", (event) => {
      handleHiddenListClick(event, callbacks);
    });
  }

  function bind(callbacks = {}) {
    bindModalControls(callbacks);
    bindRuntimeStorageControls(callbacks);
    bindAdminLists(callbacks);
  }

  window.ServerAdminActions = {
    bind,
    bindAdminLists,
    bindModalControls,
    bindRuntimeStorageControls,
    handleAdminServerListClick,
    handleHiddenListClick,
  };
})();
