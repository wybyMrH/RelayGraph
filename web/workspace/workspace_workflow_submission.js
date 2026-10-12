(function () {
  "use strict";

  const PREFIX = "relaygraph.workflow-submission.v1:";

  function validArguments(value) {
    return value && typeof value === "object" && !Array.isArray(value)
      && typeof value.auto_apply === "boolean" && typeof value.apply_evidence === "boolean"
      && Object.keys(value).every((key) => ["auto_apply", "apply_evidence", "until_node_id"].includes(key))
      && (value.until_node_id === undefined || (typeof value.until_node_id === "string" && value.until_node_id.length > 0));
  }

  function sameArguments(left, right) {
    return left.auto_apply === right.auto_apply && left.apply_evidence === right.apply_evidence
      && left.until_node_id === right.until_node_id;
  }

  async function submit(workspaceId, args, deps) {
    if (!workspaceId || !validArguments(args)) throw new Error("工作流提交参数无效，尚未发出请求。");
    if (typeof deps.fetchJson !== "function" || typeof deps.makeClientId !== "function") {
      throw new Error("工作流提交组件未加载完整，请刷新页面。");
    }
    const key = PREFIX + encodeURIComponent(workspaceId);
    let storage;
    let pending;
    try {
      storage = deps.storage();
      const raw = storage.getItem(key);
      if (raw) {
        pending = JSON.parse(raw);
        if (pending?.version !== 1 || pending.workspace_id !== workspaceId
            || typeof pending.request_id !== "string" || !/^[A-Za-z0-9_.:-]{1,128}$/.test(pending.request_id)
            || !validArguments(pending.args)) {
          throw new Error("invalid saved submission");
        }
      }
    } catch {
      throw new Error("无法读取浏览器提交记录。请检查此站点的存储权限或记录；尚未发出新请求，原记录保留。");
    }
    if (pending && !sameArguments(pending.args, args)) {
      const scope = pending.args.until_node_id ? `运行到节点 ${pending.args.until_node_id}` : "运行工作流";
      throw new Error(`上次“${scope}”的提交结果尚未确认，请先重试该操作，再开始其他范围的运行。`);
    }
    if (!pending) {
      pending = { version: 1, workspace_id: workspaceId, request_id: deps.makeClientId("workflow"), args: { ...args } };
      if (typeof pending.request_id !== "string" || !/^[A-Za-z0-9_.:-]{1,128}$/.test(pending.request_id)) {
        throw new Error("无法生成有效的提交标识。");
      }
      try {
        const encoded = JSON.stringify(pending);
        storage.setItem(key, encoded);
        if (storage.getItem(key) !== encoded) throw new Error("submission not persisted");
      } catch {
        throw new Error("浏览器无法保存提交记录，请启用此站点的存储后重试。尚未发出请求。");
      }
    }
    let payload;
    try {
      payload = await deps.fetchJson(`/api/workspaces/${encodeURIComponent(workspaceId)}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...pending.args, request_id: pending.request_id }),
      });
      if (typeof payload?.run_id !== "string" || !payload.run_id || payload.run?.id !== payload.run_id) {
        throw new Error("服务响应缺少有效的运行记录。");
      }
    } catch (error) {
      // Only this existing readiness response proves the plan was never registered.
      const rejectedBeforeRun = error.status === 409 && Array.isArray(error.payload?.blocked_checks);
      if (rejectedBeforeRun) {
        try { storage.removeItem(key); } catch { /* Keeping the same request key is safe. */ }
      } else {
        error.workflowSubmissionPending = true;
      }
      throw error;
    }
    try {
      storage.removeItem(key);
      if (storage.getItem(key) !== null) throw new Error("submission not cleared");
    } catch {
      const error = new Error(`运行 ${payload.run_id} 已确认，但浏览器无法清除提交记录。恢复存储权限后重试，会返回同一运行。`);
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  window.WorkspaceWorkflowSubmission = { submit };
})();
