(function () {
  "use strict";

  const DEFAULT_CONFIG = {
    zoomMin: 0.45,
    zoomMax: 1.85,
    zoomStep: 0.08,
  };

  let panState = null;

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function configFor(callbacks = {}) {
    return {
      ...DEFAULT_CONFIG,
      ...(callbacks.config && typeof callbacks.config === "object" ? callbacks.config : {}),
    };
  }

  function boardFor(callbacks = {}, root = null) {
    return root || fn(callbacks, "board", () => null)();
  }

  function requestFrame(callbacks = {}, callback) {
    const request = fn(callbacks, "requestAnimationFrame", (handler) => window.requestAnimationFrame(handler));
    return request(callback);
  }

  function zoomLevel(callbacks = {}) {
    const cfg = configFor(callbacks);
    const zoom = Number(fn(callbacks, "getZoom", () => 1)() || 1);
    if (!Number.isFinite(zoom)) return 1;
    return Math.max(cfg.zoomMin, Math.min(cfg.zoomMax, zoom));
  }

  function panPosition(callbacks = {}) {
    const pan = fn(callbacks, "getPan", () => ({ x: 0, y: 0 }))() || {};
    return {
      x: Number(pan.x || 0) || 0,
      y: Number(pan.y || 0) || 0,
    };
  }

  function setPan(callbacks = {}, x = 0, y = 0) {
    fn(callbacks, "setPan", () => {})({
      x: Number(x || 0) || 0,
      y: Number(y || 0) || 0,
    });
  }

  function setZoom(callbacks = {}, nextZoom = 1, options = {}) {
    const cfg = configFor(callbacks);
    const numeric = Number(nextZoom || 1);
    const zoom = Number.isFinite(numeric)
      ? Math.max(cfg.zoomMin, Math.min(cfg.zoomMax, numeric))
      : 1;
    fn(callbacks, "setZoomValue", () => {})(zoom);
    if (options.persist !== false) fn(callbacks, "persistZoom", () => {})(String(zoom));
    applyTransform(callbacks, boardFor(callbacks));
  }

  function applyTransform(callbacks = {}, root = null) {
    const canvas = boardFor(callbacks, root)?.querySelector(".workspace-execution-canvas");
    if (!canvas) return;
    const zoom = zoomLevel(callbacks);
    const pan = panPosition(callbacks);
    const panLayer = canvas.querySelector(".workspace-flow-pan-layer");
    const label = canvas.querySelector("[data-flow-zoom-label]");
    if (panLayer) {
      panLayer.style.transform = `translate(${pan.x}px, ${pan.y}px)`;
      panLayer.dataset.panX = String(pan.x);
      panLayer.dataset.panY = String(pan.y);
    }
    const zoomLayer = canvas.querySelector(".workspace-flow-zoom-layer");
    if (zoomLayer) {
      zoomLayer.style.zoom = String(zoom);
      zoomLayer.dataset.zoom = String(zoom);
    }
    if (label) label.textContent = `${Math.round(zoom * 100)}%`;
  }

  function center(callbacks = {}, root = null) {
    const board = boardFor(callbacks, root);
    const viewport = board?.querySelector(".workspace-execution-flow-viewport");
    const track = board?.querySelector(".workspace-flow-track");
    if (!viewport || !track) return;
    requestFrame(callbacks, () => {
      const zoom = zoomLevel(callbacks);
      const scaledWidth = track.offsetWidth * zoom;
      const scaledHeight = track.offsetHeight * zoom;
      setPan(
        callbacks,
        Math.round((viewport.clientWidth - scaledWidth) / 2),
        Math.round((viewport.clientHeight - scaledHeight) / 2),
      );
      applyTransform(callbacks, board);
    });
  }

  function reset(callbacks = {}, options = {}) {
    fn(callbacks, "setZoomValue", () => {})(1);
    setPan(callbacks, 0, 0);
    if (options.persist !== false) fn(callbacks, "persistZoom", () => {})("1");
    applyTransform(callbacks, boardFor(callbacks));
    if (options.center !== false) center(callbacks, boardFor(callbacks));
  }

  function handleWheel(event, callbacks = {}) {
    const viewport = event.target.closest(".workspace-execution-flow-viewport");
    if (!viewport || !viewport.closest("#workspaceExecutionBoard")) return;
    const cfg = configFor(callbacks);
    const nextZoom = zoomLevel(callbacks) + (event.deltaY > 0 ? -cfg.zoomStep : cfg.zoomStep);
    setZoom(callbacks, nextZoom);
    event.preventDefault();
    event.stopPropagation();
  }

  function handlePointerDown(event, callbacks = {}) {
    const viewport = event.target.closest(".workspace-execution-flow-viewport");
    if (!viewport || !viewport.closest("#workspaceExecutionBoard")) return;
    if (event.button !== 0) return;
    if (event.target.closest("[data-action]")) return;
    const pan = panPosition(callbacks);
    panState = {
      viewport,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originPanX: pan.x,
      originPanY: pan.y,
      moved: false,
    };
    viewport.classList.add("panning");
    viewport.setPointerCapture?.(event.pointerId);
  }

  function handlePointerMove(event, callbacks = {}) {
    const pan = panState;
    if (!pan || pan.pointerId !== event.pointerId) return;
    const dx = event.clientX - pan.startClientX;
    const dy = event.clientY - pan.startClientY;
    if (!pan.moved && Math.hypot(dx, dy) < 4) return;
    pan.moved = true;
    setPan(callbacks, pan.originPanX + dx, pan.originPanY + dy);
    applyTransform(callbacks, boardFor(callbacks));
  }

  function handlePointerUp(event) {
    const pan = panState;
    if (!pan || pan.pointerId !== event.pointerId) return;
    pan.viewport?.classList.remove("panning");
    pan.viewport?.releasePointerCapture?.(event.pointerId);
    panState = null;
  }

  function bind(callbacks = {}, root = null) {
    const board = boardFor(callbacks, root);
    if (!board || board.dataset.flowCanvasBound === "1") return;
    board.dataset.flowCanvasBound = "1";
    board.addEventListener("wheel", (event) => handleWheel(event, callbacks), { passive: false, capture: true });
    board.addEventListener("pointerdown", (event) => handlePointerDown(event, callbacks));
    window.addEventListener("pointermove", (event) => handlePointerMove(event, callbacks));
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
  }

  window.WorkspaceFlowCanvasControls = {
    applyTransform,
    bind,
    center,
    reset,
    setZoom,
    zoomLevel,
  };
})();
