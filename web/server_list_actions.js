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

  function serverItemFromEvent(event, list) {
    const item = eventTarget(event)?.closest(".server-item[data-id]");
    if (!item?.dataset.id) return null;
    if (list && typeof list.contains === "function" && !list.contains(item)) return null;
    return item;
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

  function handleServerListPointerOver(event, callbacks = {}, list = null) {
    const item = serverItemFromEvent(event, list);
    if (item) call(callbacks, "showServerResource", item.dataset.id, item, event);
  }

  function handleServerListPointerOut(event, callbacks = {}, list = null) {
    const item = serverItemFromEvent(event, list);
    if (item) call(callbacks, "hideServerResource", item.dataset.id, item, event);
  }

  function handleServerListFocusIn(event, callbacks = {}, list = null) {
    const item = serverItemFromEvent(event, list);
    if (item) call(callbacks, "showServerResource", item.dataset.id, item, event);
  }

  function handleServerListFocusOut(event, callbacks = {}, list = null) {
    const item = eventTarget(event)?.closest(".server-item[data-id]") || null;
    if (item && list && typeof list.contains === "function" && !list.contains(item)) return;
    call(callbacks, "hideServerResource", item?.dataset?.id || "", item, event);
  }

  function dragPosition(event, item) {
    const rect = item?.getBoundingClientRect?.();
    if (!rect) return "after";
    return event.clientY < rect.top + rect.height / 2 ? "before" : "after";
  }

  function handleServerListDragStart(event, callbacks = {}, list = null) {
    const item = serverItemFromEvent(event, list);
    call(callbacks, "startServerDrag", item?.dataset?.id || "", event, item);
  }

  function handleServerListDragOver(event, callbacks = {}, list = null) {
    const item = serverItemFromEvent(event, list);
    if (item) call(callbacks, "overServerDrag", item.dataset.id, dragPosition(event, item), event, item);
  }

  function handleServerListDrop(event, callbacks = {}, list = null) {
    const item = serverItemFromEvent(event, list);
    if (item) call(callbacks, "dropServerDrag", item.dataset.id, event, item);
  }

  function handleServerListDragEnd(event, callbacks = {}) {
    call(callbacks, "endServerDrag", event);
  }

  function bindOfflineServerGroup(callbacks = {}) {
    element(callbacks, "offlineServerGroup")?.addEventListener("toggle", (event) => {
      call(callbacks, "setOfflineServersOpen", event?.currentTarget?.open, event);
    });
  }

  function bind(callbacks = {}) {
    const list = element(callbacks, "serverList");
    element(callbacks, "serverSortSelect")?.addEventListener("change", (event) => {
      call(callbacks, "setServerSort", event?.target?.value || "default", event);
    });
    list?.addEventListener("click", (event) => {
      handleServerListClick(event, callbacks);
    });
    list?.addEventListener("pointerover", (event) => {
      handleServerListPointerOver(event, callbacks, list);
    });
    list?.addEventListener("pointerout", (event) => {
      handleServerListPointerOut(event, callbacks, list);
    });
    list?.addEventListener("focusin", (event) => {
      handleServerListFocusIn(event, callbacks, list);
    });
    list?.addEventListener("focusout", (event) => {
      handleServerListFocusOut(event, callbacks, list);
    });
    list?.addEventListener("scroll", (event) => {
      call(callbacks, "positionServerResource", event);
    }, { passive: true });
    list?.addEventListener("dragstart", (event) => {
      handleServerListDragStart(event, callbacks, list);
    });
    list?.addEventListener("dragover", (event) => {
      handleServerListDragOver(event, callbacks, list);
    });
    list?.addEventListener("drop", (event) => {
      handleServerListDrop(event, callbacks, list);
    });
    list?.addEventListener("dragend", (event) => {
      handleServerListDragEnd(event, callbacks);
    });
  }

  window.ServerListActions = {
    bind,
    bindOfflineServerGroup,
    dragPosition,
    handleServerListDragEnd,
    handleServerListDragOver,
    handleServerListDragStart,
    handleServerListDrop,
    handleServerListClick,
    handleServerListFocusIn,
    handleServerListFocusOut,
    handleServerListPointerOut,
    handleServerListPointerOver,
    serverItemFromEvent,
  };
})();
