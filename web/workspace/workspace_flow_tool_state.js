(function () {
  "use strict";

  function workspaceFlowNodeToolStatuses(node = {}, tools = [], preview = false) {
    const nodeStatus = String(node?.status || (preview ? "preview" : "pending"));
    if (nodeStatus === "done") return tools.map(() => "done");
    if (["failed", "stopped", "blocked"].includes(nodeStatus)) {
      return tools.map((_, index) => (index === 0 ? "failed" : "pending"));
    }
    if (!["running", "starting", "queued"].includes(nodeStatus)) {
      return tools.map(() => (preview ? "preview" : "pending"));
    }
    const activeIndex = Math.min(tools.length - 1, Math.max(0, tools.findIndex((_, index) => index === 0)));
    return tools.map((_, index) => {
      if (index < activeIndex) return "done";
      if (index === activeIndex) return "running";
      return "pending";
    });
  }

  function workspaceFlowToolStatusLabel(status = "pending") {
    const map = {
      done: "完成",
      running: "进行中",
      failed: "失败",
      blocked: "阻塞",
      preview: "预览",
      pending: "等待",
    };
    return map[String(status || "pending")] || "等待";
  }

  function workspaceFlowToolHealthStatus(tool = {}, runtimeStatus = "pending") {
    if (tool?.enabled === false) return "fault";
    const status = String(runtimeStatus || "pending");
    if (["failed", "blocked"].includes(status)) return "fault";
    if (["running", "starting"].includes(status)) return "running";
    if (status === "done") return "done";
    if (status === "preview") return "preview";
    return "available";
  }

  function workspaceFlowToolHealthLabel(health = "available") {
    const map = {
      available: "可用",
      running: "运行中",
      fault: "故障",
      done: "完成",
      preview: "预览",
      pending: "等待",
    };
    return map[String(health || "available")] || "可用";
  }

  function workspaceFlowToolSelectionKey(nodeId = "", toolId = "") {
    const node = String(nodeId || "").trim();
    const tool = String(toolId || "").trim();
    return node && tool ? `${node}::${tool}` : "";
  }

  function parseWorkspaceFlowToolSelectionKey(key = "") {
    const text = String(key || "").trim();
    if (!text.includes("::")) return { nodeId: "", toolId: "" };
    const [nodeId, toolId] = text.split("::");
    return { nodeId: nodeId || "", toolId: toolId || "" };
  }

  window.WorkspaceFlowToolState = {
    parseWorkspaceFlowToolSelectionKey,
    workspaceFlowNodeToolStatuses,
    workspaceFlowToolHealthLabel,
    workspaceFlowToolHealthStatus,
    workspaceFlowToolSelectionKey,
    workspaceFlowToolStatusLabel,
  };
})();
