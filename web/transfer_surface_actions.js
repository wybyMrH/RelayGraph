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

  function bool(value) {
    return value === true || value === "1";
  }

  function rowInfo(row, button) {
    const path = button?.dataset.path || row?.dataset.path || "";
    const isDir = bool(button?.dataset.dir) || bool(row?.dataset.dir);
    return { path, isDir };
  }

  function call(callbacks, name, ...args) {
    return fn(callbacks, name, () => {})(...args);
  }

  function callAsync(callbacks, name, ...args) {
    void fn(callbacks, name, async () => {})(...args);
  }

  function handleFavoriteClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const openBtn = target?.closest("[data-action='open-transfer-favorite']");
    if (openBtn?.dataset.path) {
      callAsync(callbacks, "openFavorite", openBtn.dataset.mode || "source", openBtn.dataset.path);
      return;
    }
    const removeBtn = target?.closest("[data-action='remove-transfer-favorite']");
    if (removeBtn?.dataset.path) {
      call(callbacks, "removeFavorite", removeBtn.dataset.mode || "source", removeBtn.dataset.path);
    }
  }

  function handleIgnoreClick(event, callbacks = {}) {
    const button = eventTarget(event)?.closest(".chip-remove");
    if (button) call(callbacks, "removeIgnore", button.dataset.ignore || "");
  }

  function handleSelectedSourceClick(event, callbacks = {}) {
    const target = eventTarget(event);
    if (target?.closest("[data-action='clear-transfer-sources']")) {
      call(callbacks, "clearSources");
      return;
    }
    const previewButton = target?.closest("[data-action='preview-selected-source']");
    if (previewButton?.dataset.sourceKey) {
      callAsync(callbacks, "previewSelectedSource", previewButton.dataset.sourceKey);
      return;
    }
    const removeButton = target?.closest("[data-source-key]");
    if (removeButton) call(callbacks, "removeSelectedSource", removeButton.dataset.sourceKey || "");
  }

  function handleTransferTreeClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    const row = target?.closest(".file-tree-row");
    if (!row) return;
    const rowPath = row.dataset.path || "";
    const rowIsDir = bool(row.dataset.dir);
    if (!button) {
      if (target.closest(".file-name")) callAsync(callbacks, "openTransferTreeName", rowPath, rowIsDir);
      return;
    }
    const { path, isDir } = rowInfo(row, button);
    if (button.dataset.action === "toggle-transfer-node") {
      callAsync(callbacks, "toggleTransferNode", path, isDir);
    } else if (button.dataset.action === "preview-transfer-node") {
      callAsync(callbacks, "previewTransferNode", path);
    } else if (button.dataset.action === "add-transfer-source") {
      call(callbacks, "addTransferSource", path, isDir);
    } else if (button.dataset.action === "remove-transfer-source") {
      call(callbacks, "removeTransferSourceFromTree", button.dataset.sourceKey || "", path, isDir);
    } else if (button.dataset.action === "ignore-transfer-node") {
      call(callbacks, "addTransferIgnore", path, isDir);
    }
  }

  function handleTargetTreeClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    const row = target?.closest(".file-tree-row");
    if (!row) return;
    const rowPath = row.dataset.path || "";
    const rowIsDir = bool(row.dataset.dir);
    if (!button) {
      if (rowIsDir && target.closest(".file-name")) call(callbacks, "chooseTransferTargetDirectory", rowPath);
      return;
    }
    const { path, isDir } = rowInfo(row, button);
    if (button.dataset.action === "toggle-target-node") {
      callAsync(callbacks, "toggleTransferTargetNode", path, isDir);
    }
  }

  function handleFilePickerRootsClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const removeBtn = target?.closest("[data-action='remove-favorite-path']");
    if (removeBtn?.dataset.path) {
      call(callbacks, "removeFilePickerFavorite", removeBtn.dataset.path);
      return;
    }
    const openFavorite = target?.closest("[data-action='open-favorite-path']");
    if (openFavorite?.dataset.path) {
      callAsync(callbacks, "openFilePickerRoot", openFavorite.dataset.path);
      return;
    }
    const button = target?.closest(".root-button");
    if (button?.dataset.path) callAsync(callbacks, "openFilePickerRoot", button.dataset.path);
  }

  function handleFilePickerListClick(event, callbacks = {}) {
    const target = eventTarget(event);
    const button = target?.closest("[data-action]");
    const row = target?.closest(".file-picker-row");
    if (!row) return;
    const path = row.dataset.path || "";
    const isDir = bool(row.dataset.dir);
    if (!button) {
      if (target.closest(".file-picker-row-main")) callAsync(callbacks, "activateFilePickerRow", path, isDir);
      return;
    }
    if (button.dataset.action === "preview-picker") {
      callAsync(callbacks, "previewPicker", path);
    } else if (button.dataset.action === "choose-picker") {
      callAsync(callbacks, "choosePicker", path, isDir);
    } else if (button.dataset.action === "remove-picker-source") {
      call(callbacks, "removePickerSource", button.dataset.sourceKey || "", path, isDir);
    }
  }

  function bindConflictControls(callbacks = {}) {
    element(callbacks, "transferConflictCloseBtn")?.addEventListener("click", () => {
      call(callbacks, "cancelTransferConflict");
    });
    element(callbacks, "transferConflictOverwriteAllBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "resolveTransferConflict", "overwrite_all");
    });
    element(callbacks, "transferConflictSkipAllBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "resolveTransferConflict", "skip_all");
    });
    element(callbacks, "transferConflictPromptEachBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "resolveTransferConflict", "prompt_each");
    });
  }

  function bindTransferControls(callbacks = {}) {
    element(callbacks, "transferForm")?.addEventListener("submit", (event) => callAsync(callbacks, "submitTransfer", event));
    element(callbacks, "transferForm")?.addEventListener("click", (event) => handleFavoriteClick(event, callbacks));
    element(callbacks, "sourceFavoritePathBtn")?.addEventListener("click", () => call(callbacks, "toggleFavorite", "source"));
    element(callbacks, "targetFavoritePathBtn")?.addEventListener("click", () => call(callbacks, "toggleFavorite", "target"));
    element(callbacks, "transferSourceTreeUpBtn")?.addEventListener("click", () => callAsync(callbacks, "navigateSourceParent"));
    element(callbacks, "transferSourceTreeForwardBtn")?.addEventListener("click", () => callAsync(callbacks, "navigateSourceForward"));
    element(callbacks, "transferTargetTreeUpBtn")?.addEventListener("click", () => callAsync(callbacks, "navigateTargetParent"));
    element(callbacks, "transferTargetTreeForwardBtn")?.addEventListener("click", () => callAsync(callbacks, "navigateTargetForward"));
    element(callbacks, "sourceBrowseBtn")?.addEventListener("click", () => callAsync(callbacks, "openFilePicker", "source"));
    element(callbacks, "sourceInspectBtn")?.addEventListener("click", () => callAsync(callbacks, "inspectSource"));
    element(callbacks, "sourcePreviewBtn")?.addEventListener("click", () => callAsync(callbacks, "previewSourceInput"));
    element(callbacks, "transferSourceInput")?.addEventListener("blur", () => call(callbacks, "transferInputBlur", "source"));
    element(callbacks, "transferSourceInput")?.addEventListener("input", () => call(callbacks, "updateFavoriteButtons"));
    element(callbacks, "transferSourceServerSelect")?.addEventListener("change", (event) => call(callbacks, "sourceServerChange", eventTarget(event)?.value || ""));
    element(callbacks, "targetBrowseBtn")?.addEventListener("click", () => callAsync(callbacks, "openFilePicker", "target"));
    element(callbacks, "targetInspectBtn")?.addEventListener("click", () => callAsync(callbacks, "inspectTarget"));
    element(callbacks, "transferTargetInput")?.addEventListener("blur", () => call(callbacks, "transferInputBlur", "target"));
    element(callbacks, "transferTargetInput")?.addEventListener("input", () => call(callbacks, "updateFavoriteButtons"));
    element(callbacks, "transferTargetServerSelect")?.addEventListener("change", (event) => call(callbacks, "targetServerChange", eventTarget(event)?.value || ""));
    element(callbacks, "transferExcludeInput")?.addEventListener("change", () => call(callbacks, "syncIgnoreState"));
    element(callbacks, "ignoreChips")?.addEventListener("click", (event) => handleIgnoreClick(event, callbacks));
    element(callbacks, "selectedSourceList")?.addEventListener("click", (event) => handleSelectedSourceClick(event, callbacks));
    element(callbacks, "transferTree")?.addEventListener("click", (event) => handleTransferTreeClick(event, callbacks));
    element(callbacks, "targetTree")?.addEventListener("click", (event) => handleTargetTreeClick(event, callbacks));
    element(callbacks, "transferSourceTreeClearBtn")?.addEventListener("click", () => call(callbacks, "clearSourceTree"));
    element(callbacks, "transferTargetTreeClearBtn")?.addEventListener("click", () => call(callbacks, "clearTargetTree"));
    element(callbacks, "transferPreviewClearBtn")?.addEventListener("click", () => call(callbacks, "clearPreview"));
    element(callbacks, "transferTreeClearPreviewBtn")?.addEventListener("click", () => call(callbacks, "clearPreview"));
    element(callbacks, "transferPreviewOpenBtn")?.addEventListener("click", () => call(callbacks, "openCurrentPreview"));
    element(callbacks, "transferPreviewDownloadBtn")?.addEventListener("click", () => call(callbacks, "downloadCurrentPreview"));
  }

  function bindFilePickerControls(callbacks = {}) {
    element(callbacks, "closeFilePickerBtn")?.addEventListener("click", () => call(callbacks, "closeFilePicker"));
    element(callbacks, "filePickerModal")?.addEventListener("click", (event) => {
      if (event.target?.id === "filePickerModal") call(callbacks, "closeFilePicker");
    });
    element(callbacks, "filePickerOpenBtn")?.addEventListener("click", () => {
      callAsync(callbacks, "openFilePickerPath", element(callbacks, "filePickerPathInput")?.value || "");
    });
    element(callbacks, "filePickerFavoriteBtn")?.addEventListener("click", () => call(callbacks, "toggleFilePickerFavorite"));
    element(callbacks, "filePickerPathInput")?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      callAsync(callbacks, "openFilePickerPath", eventTarget(event)?.value || "");
    });
    element(callbacks, "filePickerPathInput")?.addEventListener("input", () => call(callbacks, "filePickerPathInputChanged"));
    element(callbacks, "filePickerUpBtn")?.addEventListener("click", () => callAsync(callbacks, "filePickerUp"));
    element(callbacks, "filePickerForwardBtn")?.addEventListener("click", () => callAsync(callbacks, "filePickerForward"));
    element(callbacks, "filePickerChooseDirBtn")?.addEventListener("click", () => callAsync(callbacks, "chooseCurrentFilePickerDirectory"));
    element(callbacks, "filePreviewOpenBtn")?.addEventListener("click", () => call(callbacks, "openCurrentPreview"));
    element(callbacks, "filePreviewDownloadBtn")?.addEventListener("click", () => call(callbacks, "downloadCurrentPreview"));
    element(callbacks, "filePickerRoots")?.addEventListener("click", (event) => handleFilePickerRootsClick(event, callbacks));
    element(callbacks, "filePickerList")?.addEventListener("click", (event) => handleFilePickerListClick(event, callbacks));
  }

  function bind(callbacks = {}) {
    bindConflictControls(callbacks);
    bindTransferControls(callbacks);
    bindFilePickerControls(callbacks);
  }

  window.TransferSurfaceActions = {
    bind,
    bindConflictControls,
    bindFilePickerControls,
    bindTransferControls,
    handleFavoriteClick,
    handleFilePickerListClick,
    handleFilePickerRootsClick,
    handleIgnoreClick,
    handleSelectedSourceClick,
    handleTargetTreeClick,
    handleTransferTreeClick,
  };
})();
