(function () {
  "use strict";

  function hasNotes(step = {}) {
    return [step.detail, step.error, step.recorded_error].some((value) => String(value ?? "").trim());
  }

  function markup(step = {}, deps = {}, options = {}) {
    const escape = deps.escapeHtml;
    const detail = String(step.detail ?? "").trim();
    const error = String(step.error ?? "").trim();
    const recordedError = String(step.recorded_error ?? "").trim();
    if (!detail && !error && !recordedError) return "";
    const description = detail === "agent node executed" ? "Agent 已执行这一步。" : detail;
    let explanation = "";
    if (step.status === "blocked" && error === "Agent invocation outcome unknown; automatic replay refused") {
      explanation = "这次 Agent 调用的结果未能确认，流程已暂停。系统不会自动再次调用模型；请先核对本次运行记录。";
    } else if (step.status === "failed" && error.startsWith("LLM error: Invalid JSON content response:")) {
      explanation = "模型回复格式无效，本次 Agent 执行失败。请核对模型接口的响应格式。";
    }
    const originKey = JSON.stringify([
      "step-origin", options.surface || "list", options.runId || "",
      step.step_id || step.node_id || step.index, step.attempt_id || "",
    ]);
    return `<div class="workspace-run-step-notes">
      ${detail && detail !== error ? `<p class="workspace-run-step-description">说明：${escape(description)}</p>` : ""}
      ${explanation ? `<p class="workspace-run-step-description">${escape(explanation)}</p>` : ""}
      ${error ? `<p class="workspace-execution-run-step-error">错误：${escape(error)}</p>` : ""}
      ${recordedError ? `<details class="workspace-run-step-origin" data-reader-detail="${escape(originKey)}"${options.openDetails?.has(originKey) ? " open" : ""}>
        <summary>历史记录来源</summary>
        <p>原记录将这段文字放在错误字段中；此处保留原文供核对，当前结果请看步骤状态和错误说明。</p>
        <p class="workspace-run-step-original-text">${escape(recordedError)}</p>
      </details>` : ""}
    </div>`;
  }

  window.WorkspaceRunStepNotes = { hasNotes, markup };
})();
