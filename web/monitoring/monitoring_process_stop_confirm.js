(function () {
  "use strict";

  function processStopOwnerUnknown(reason = "") {
    const value = String(reason || "").trim();
    return value === "owner_unknown" || value === "owner_check_failed";
  }

  function processStopConfirmCopy(details = {}) {
    const ownerUnknown = processStopOwnerUnknown(details.reason);
    return {
      title: ownerUnknown ? "确认关闭归属未知进程" : "确认关闭非当前用户进程",
      subtitle: ownerUnknown
        ? "系统无法确认这个进程是否属于当前登录用户，确认后才会发送停止信号。"
        : "这个进程不属于当前登录用户，确认后才会发送停止信号。",
    };
  }

  function processStopConfirmRows(details = {}) {
    return [
      ["服务器", details.serverName || "-"],
      ["PID", details.pid || "-"],
      ["进程用户", details.owner || "未知用户"],
      ["当前用户", details.currentUser || "当前用户未知"],
      ...(details.ownerUid || details.currentUid ? [["进程 UID", details.ownerUid || "-"], ["当前 UID", details.currentUid || "-"]] : []),
    ];
  }

  function processStopConfirmDetails({ server = null, process = null, pid = "", context = {} } = {}) {
    return {
      serverName: server?.name || server?.id || "-",
      pid,
      owner: context.owner || process?.user || "未知用户",
      ownerUid: context.owner_uid || process?.uid || "",
      currentUser: context.current_user || server?.current_user || server?.host_resources?.current_user || "当前用户未知",
      currentUid: context.current_uid || server?.current_uid || server?.host_resources?.current_uid || "",
      command: String(context.command || process?.command || process?.process_name || "").trim(),
      reason: String(context.reason || "").trim(),
    };
  }

  window.MonitoringProcessStopConfirm = {
    processStopConfirmCopy,
    processStopConfirmDetails,
    processStopConfirmRows,
    processStopOwnerUnknown,
  };
})();
