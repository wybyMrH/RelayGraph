(function () {
  "use strict";

  function fallbackShellQuote(value) {
    const text = String(value ?? "");
    return `'${text.replaceAll("'", "'\\''")}'`;
  }

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function buildTransferCommandParts(form, sourceItems, target, excludes, transferOptions = {}, deps = {}) {
    const shellQuote = fn(deps, "shellQuote", fallbackShellQuote);
    const rsyncTransferSourceValue = fn(deps, "rsyncTransferSourceValue", (item = {}) => item.value || "");
    const baseParts = ["rsync", "-avPh", "--info=progress2"];
    if (form.checksum?.checked) {
      baseParts.push("--checksum");
    } else if (form.size_only?.checked) {
      baseParts.push("--size-only");
    }
    if (form.resume_partial?.checked) baseParts.push("--partial", "--append-verify");
    if (transferOptions.ignore_existing) baseParts.push("--ignore-existing");
    excludes.forEach((item) => {
      baseParts.push("--exclude", shellQuote(item));
    });
    const filteredItems = sourceItems.filter((item) => !transferOptions.skip_sources?.includes(item.path));
    const sources = filteredItems.map((item) => rsyncTransferSourceValue(item)).filter(Boolean);
    const commandForSource = (source) => [...baseParts, shellQuote(source), shellQuote(target)].join(" ");
    const command = sources.length === 1
      ? commandForSource(sources[0])
      : sources.length ? ["set -e", ...sources.map((source) => commandForSource(source))].join("\n") : "";
    return { command, sources, filteredItems };
  }

  window.TransferCommandBuilder = {
    buildTransferCommandParts,
  };
})();
