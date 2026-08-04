(function () {
  "use strict";

  function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeFor(deps, value) {
    return (typeof deps.escapeHtml === "function" ? deps.escapeHtml : fallbackEscapeHtml)(value);
  }

  function pathBaseNameFor(deps, path) {
    if (typeof deps.pathBaseName === "function") return deps.pathBaseName(path);
    return String(path || "").replace(/\/+$/, "").split("/").pop() || String(path || "");
  }

  function formatPreviewTextFor(deps, path, text) {
    if (typeof deps.formatPreviewText === "function") return deps.formatPreviewText(path, text);
    return String(text ?? "");
  }

  function filePreviewKindLabel(kind) {
    const labels = {
      text: "文本快览",
      image: "图片快览",
      pdf: "PDF 快览",
      audio: "音频快览",
      video: "视频快览",
      binary: "文件快览",
    };
    return labels[String(kind || "")] || "文件快览";
  }

  function previewSummaryMarkup(preview = {}, deps = {}) {
    const path = preview.localPath || preview.path;
    return `
    <div class="file-preview-summary">
      <strong>${preview.cached ? "已缓存到本机" : "当前本机文件"}</strong>
      <p class="file-preview-path" title="${escapeFor(deps, path)}">${escapeFor(deps, path)}</p>
    </div>
  `;
  }

  function buildFilePreviewDisplay(preview = {}, context = {}, deps = {}) {
    const emptyMessage = context.emptyMessage || "选择文件查看预览。";
    if (preview.loading) {
      return {
        title: "文件快览",
        meta: "正在下载到本机缓存",
        html: '<div class="file-preview-note">正在下载并准备预览内容...</div>',
        canOpen: false,
        canDownload: false,
      };
    }
    if (preview.error) {
      return {
        title: "文件快览",
        meta: "不可预览",
        html: `<div class="file-preview-note">${escapeFor(deps, preview.error)}</div>`,
        canOpen: false,
        canDownload: false,
      };
    }
    if (!preview.path) {
      return {
        title: "文件快览",
        meta: "选择文件后预览",
        html: `<div class="file-preview-note">${escapeFor(deps, emptyMessage)}</div>`,
        canOpen: false,
        canDownload: false,
      };
    }
    const kind = preview.kind || "binary";
    const title = pathBaseNameFor(deps, preview.path);
    const meta = [
      context.serverName || (preview.serverId ? preview.serverId : "本机"),
      filePreviewKindLabel(kind),
      preview.sizeText || "",
      kind === "text" ? (preview.encoding || "utf-8") : "",
      preview.truncated ? "已截断" : "",
    ].filter(Boolean).join(" · ");
    const summary = previewSummaryMarkup(preview, deps);
    const fileName = pathBaseNameFor(deps, preview.path);
    if (kind === "text") {
      const previewText = formatPreviewTextFor(deps, preview.path, preview.text || "文件为空。");
      const lowerName = pathBaseNameFor(deps, preview.path || "").toLowerCase();
      const htmlKind = lowerName.endsWith(".html") || lowerName.endsWith(".htm");
      if (htmlKind && preview.previewUrl) {
        return {
          title,
          meta,
          html: `${summary}<div class="file-preview-embed"><iframe sandbox="" src="${escapeFor(deps, preview.previewUrl)}" title="${escapeFor(deps, fileName)}"></iframe></div>`,
          canOpen: true,
          canDownload: Boolean(preview.downloadUrl),
        };
      }
      return {
        title,
        meta,
        html: `${summary}<pre class="file-preview-text">${escapeFor(deps, previewText)}</pre>`,
        canOpen: Boolean(preview.previewUrl),
        canDownload: Boolean(preview.downloadUrl),
      };
    }
    if (kind === "image" && preview.previewUrl) {
      return {
        title,
        meta,
        html: `${summary}<div class="file-preview-embed"><img src="${escapeFor(deps, preview.previewUrl)}" alt="${escapeFor(deps, fileName)}" loading="lazy" /></div>`,
        canOpen: true,
        canDownload: Boolean(preview.downloadUrl),
      };
    }
    if (kind === "pdf" && preview.previewUrl) {
      return {
        title,
        meta,
        html: `${summary}<div class="file-preview-embed"><iframe src="${escapeFor(deps, preview.previewUrl)}" title="${escapeFor(deps, fileName)}"></iframe></div>`,
        canOpen: true,
        canDownload: Boolean(preview.downloadUrl),
      };
    }
    if (kind === "audio" && preview.previewUrl) {
      return {
        title,
        meta,
        html: `${summary}<div class="file-preview-embed"><audio controls preload="metadata" src="${escapeFor(deps, preview.previewUrl)}"></audio></div>`,
        canOpen: true,
        canDownload: Boolean(preview.downloadUrl),
      };
    }
    if (kind === "video" && preview.previewUrl) {
      return {
        title,
        meta,
        html: `${summary}<div class="file-preview-embed"><video controls preload="metadata" src="${escapeFor(deps, preview.previewUrl)}"></video></div>`,
        canOpen: true,
        canDownload: Boolean(preview.downloadUrl),
      };
    }
    return {
      title,
      meta,
      html: `${summary}<div class="file-preview-note">这个文件类型暂不做内嵌展示，已经可以直接打开或下载本机缓存文件。</div>`,
      canOpen: Boolean(preview.previewUrl),
      canDownload: Boolean(preview.downloadUrl),
    };
  }

  window.FilePreviewMarkup = {
    buildFilePreviewDisplay,
    filePreviewKindLabel,
  };
})();
