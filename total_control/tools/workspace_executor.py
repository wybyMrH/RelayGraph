from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..orchestration.workspace_mutations import apply_artifact_write, apply_workflow_edit
from .registry import TOOL_SIDE_EFFECTS, ToolSideEffect, tool_side_effect


def _split_values(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_items = [str(item or "") for item in value]
    else:
        raw_items = str(value or "").replace(",", "\n").splitlines()
    seen: set[str] = set()
    values: list[str] = []
    for raw in raw_items:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        values.append(item)
    return values


def _safe_workspace_path(workspace_dir: str, path: str) -> Path | None:
    root_text = str(workspace_dir or "").strip()
    target_text = str(path or "").strip()
    if not root_text or not target_text:
        return None
    root = Path(root_text).expanduser().resolve()
    target = Path(target_text).expanduser()
    if not target.is_absolute():
        target = (root / target_text.lstrip("/")).resolve()
    else:
        target = target.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target if target.exists() else None


def _preview_value(value: Any, *, limit: int = 120) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        text = " ".join(value.split())
        return text[:limit] + ("…" if len(text) > limit else "")
    if isinstance(value, list):
        if not value:
            return "[]"
        items = [_preview_value(item, limit=40) for item in value[:4]]
        suffix = f" +{len(value) - 4}" if len(value) > 4 else ""
        return f"[{', '.join(items)}{suffix}]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = []
        for index, (key, item) in enumerate(value.items()):
            if index >= 4:
                parts.append("…")
                break
            parts.append(f"{key}: {_preview_value(item, limit=32)}")
        return "{" + ", ".join(parts) + "}"
    return _preview_value(str(value), limit=limit)


def _scan_directory(
    root_path: Path,
    *,
    max_depth: int = 2,
    max_entries: int = 180,
    include_files: bool = True,
    include_dirs: bool = True,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    root = root_path.resolve()
    if not root.is_dir():
        return entries
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        depth = len(current.relative_to(root).parts)
        if depth > max_depth:
            dirnames[:] = []
            continue
        dirnames.sort()
        filenames.sort()
        if include_dirs:
            for name in dirnames:
                if len(entries) >= max_entries:
                    return entries
                path = current / name
                try:
                    rel = str(path.relative_to(root))
                except ValueError:
                    rel = str(path)
                entries.append({"name": name, "path": rel, "type": "dir", "depth": depth + 1})
        if include_files:
            for name in filenames:
                if len(entries) >= max_entries:
                    return entries
                path = current / name
                try:
                    rel = str(path.relative_to(root))
                except ValueError:
                    rel = str(path)
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                entries.append({"name": name, "path": rel, "type": "file", "depth": depth + 1, "size": size})
    return entries


@dataclass
class WorkspaceToolContext:
    workspace: dict[str, Any]
    statuses: list[dict[str, Any]] = field(default_factory=list)
    jobs: list[dict[str, Any]] = field(default_factory=list)

    def node_config(self, kind: str) -> dict[str, Any]:
        for node in self.workspace.get("nodes") if isinstance(self.workspace.get("nodes"), list) else []:
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == kind:
                config = node.get("config") if isinstance(node.get("config"), dict) else {}
                return config
        return {}

    def source_payload(self) -> dict[str, Any]:
        source = self.workspace.get("source") if isinstance(self.workspace.get("source"), dict) else {}
        inputs = self.workspace.get("inputs") if isinstance(self.workspace.get("inputs"), dict) else {}
        return {
            "goal_text": str(inputs.get("goal_text") or self.workspace.get("brief") or source.get("idea_text") or "").strip(),
            "repo_urls": _split_values(inputs.get("repo_urls") or source.get("repo_url")),
            "paper_urls": _split_values(inputs.get("paper_urls") or source.get("paper_url")),
            "references": _split_values(inputs.get("references")),
            "context_blocks": _split_values(inputs.get("context_blocks")),
            "workspace_dir": str(self.workspace.get("workspace_dir") or "").strip(),
        }

    def configured_run_command(self) -> str:
        return str(self.node_config("run.command").get("run_command") or "").strip()

    def workflow_nodes(self) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for index, node in enumerate(self.workspace.get("nodes") if isinstance(self.workspace.get("nodes"), list) else []):
            if not isinstance(node, dict):
                continue
            config = node.get("config") if isinstance(node.get("config"), dict) else {}
            handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
            nodes.append(
                {
                    "order": index + 1,
                    "id": str(node.get("id") or "").strip(),
                    "kind": str(node.get("kind") or "").strip(),
                    "title": str(node.get("title") or node.get("kind") or "").strip(),
                    "agent_id": str(handler.get("agent_id") or "").strip(),
                    "input_mapping": node.get("input_mapping") if isinstance(node.get("input_mapping"), dict) else {},
                    "output_key": str(node.get("output_key") or "").strip(),
                    "configured_fields": sorted(key for key, value in config.items() if str(value or "").strip())[:8],
                }
            )
        return nodes

    def gpu_candidates(self, min_free_mib: int = 0, server_id: str = "") -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for status in self.statuses:
            sid = str(status.get("id") or "").strip()
            if server_id and sid != server_id:
                continue
            if status.get("online") is False:
                continue
            for gpu in status.get("gpus") if isinstance(status.get("gpus"), list) else []:
                if not isinstance(gpu, dict):
                    continue
                free_mib = int(float(gpu.get("memory_free_mib") or 0))
                util = int(float(gpu.get("gpu_util") or 100))
                state = str(gpu.get("state") or "").strip() or ("idle" if util <= 10 else "busy")
                candidates.append(
                    {
                        "server_id": sid,
                        "server_name": str(status.get("name") or sid).strip(),
                        "gpu_index": gpu.get("index"),
                        "name": str(gpu.get("name") or "").strip(),
                        "memory_free_mib": free_mib,
                        "memory_total_mib": int(float(gpu.get("memory_total_mib") or 0)),
                        "gpu_util": util,
                        "state": state,
                        "eligible": state == "idle" and free_mib >= min_free_mib,
                        "collected_at": str(status.get("collected_at") or "").strip(),
                    }
                )
        candidates.sort(key=lambda item: (bool(item["eligible"]), item["memory_free_mib"], -item["gpu_util"]), reverse=True)
        return candidates

    def automation_selected_gpu(self) -> dict[str, Any]:
        automation = self.workspace.get("automation") if isinstance(self.workspace.get("automation"), dict) else {}
        resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
        scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
        selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
        return selected

    def execution_package_payload(self) -> dict[str, Any]:
        automation = self.workspace.get("automation") if isinstance(self.workspace.get("automation"), dict) else {}
        manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
        bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
        package_manifest = bundle.get("package_manifest") if isinstance(bundle.get("package_manifest"), dict) else {}
        resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
        scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
        selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
        backfill = automation.get("evidence_backfill") if isinstance(automation.get("evidence_backfill"), dict) else {}
        backfill_items = backfill.get("items") if isinstance(backfill.get("items"), list) else []
        readiness = automation.get("execution_readiness") if isinstance(automation.get("execution_readiness"), dict) else {}
        command_script = bundle.get("command_script") if isinstance(bundle.get("command_script"), dict) else {}
        return {
            "status": str(bundle.get("status") or manifest.get("status") or "draft").strip(),
            "ready_to_execute": bool(bundle.get("ready_to_execute")),
            "next_action": bundle.get("next_action") if isinstance(bundle.get("next_action"), dict) else {},
            "target": bundle.get("target") if isinstance(bundle.get("target"), dict) else {},
            "commands": package_manifest.get("commands") if isinstance(package_manifest.get("commands"), dict) else {},
            "paths": package_manifest.get("paths") if isinstance(package_manifest.get("paths"), dict) else {},
            "dataset_discovery": package_manifest.get("dataset_discovery") if isinstance(package_manifest.get("dataset_discovery"), dict) else {},
            "scheduler": {
                "status": str(scheduler.get("status") or "").strip(),
                "mode": str(scheduler.get("mode") or "").strip(),
                "policy": str(scheduler.get("policy") or "").strip(),
                "summary": str(scheduler.get("summary") or "").strip(),
                "selected": selected,
                "candidate_count": int(scheduler.get("candidate_count") or 0),
                "ready_count": int(scheduler.get("ready_count") or 0),
            },
            "missing": bundle.get("missing") if isinstance(bundle.get("missing"), list) else [],
            "backfill": {
                "status": str(backfill.get("status") or "").strip(),
                "summary": str(backfill.get("summary") or "").strip(),
                "ready_count": int(backfill.get("ready_count") or 0),
                "items": [
                    {
                        "node_kind": str(item.get("node_kind") or "").strip(),
                        "field": str(item.get("field") or "").strip(),
                        "label": str(item.get("label") or "").strip(),
                        "value": str(item.get("value") or "").strip(),
                        "status": str(item.get("status") or "").strip(),
                    }
                    for item in backfill_items[:12]
                    if isinstance(item, dict)
                ],
            },
            "readiness": {
                "status": str(readiness.get("status") or "").strip(),
                "summary": str(readiness.get("summary") or "").strip(),
                "gate": readiness.get("gate") if isinstance(readiness.get("gate"), dict) else {},
            },
            "script": {
                "shell": str(command_script.get("shell") or "bash").strip(),
                "status": str(command_script.get("status") or "").strip(),
                "ready": bool(command_script.get("ready")),
                "summary": str(command_script.get("summary") or "").strip(),
                "text": str(command_script.get("text") or "")[:4000],
            },
        }

    def workspace_artifacts(self) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for node in self.workspace.get("nodes") if isinstance(self.workspace.get("nodes"), list) else []:
            if not isinstance(node, dict):
                continue
            runtime = node.get("runtime") if isinstance(node.get("runtime"), dict) else {}
            node_artifacts = runtime.get("artifacts") if isinstance(runtime.get("artifacts"), list) else []
            if not node_artifacts and isinstance(node.get("artifacts"), list):
                node_artifacts = node.get("artifacts")
            for artifact in node_artifacts:
                if not isinstance(artifact, dict):
                    continue
                artifacts.append(
                    {
                        **artifact,
                        "node_id": str(node.get("id") or "").strip(),
                        "node_kind": str(node.get("kind") or "").strip(),
                        "source": "node.runtime",
                    }
                )
        automation = self.workspace.get("automation") if isinstance(self.workspace.get("automation"), dict) else {}
        context = automation.get("execution_context") if isinstance(automation.get("execution_context"), dict) else {}
        outputs = context.get("outputs") if isinstance(context.get("outputs"), dict) else {}
        for key, value in outputs.items():
            if not isinstance(value, dict):
                continue
            artifacts.append(
                {
                    "label": str(value.get("label") or key).strip(),
                    "path": str(value.get("path") or "").strip(),
                    "summary": str(value.get("summary") or "").strip(),
                    "output_key": str(key).strip(),
                    "node_id": str(value.get("node_id") or "").strip(),
                    "node_kind": str(value.get("node_kind") or "").strip(),
                    "source": "context.outputs",
                }
            )
        return artifacts

    def job_workspace_id(self, job: dict[str, Any]) -> str:
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        return str(metadata.get("workspace_id") or job.get("workspace_id") or "").strip()

    def execute_dataset_find(self, arguments: dict[str, Any]) -> dict[str, Any]:
        source = self.source_payload()
        config = self.node_config("dataset.find")
        workspace_dir = str(
            arguments.get("workspace_dir")
            or source.get("workspace_dir")
            or config.get("workspace_dir")
            or ""
        ).strip()
        query = str(arguments.get("query") or config.get("query") or source.get("goal_text") or "").strip()
        roots = _split_values(arguments.get("data_roots") or config.get("data_roots"))
        hints = _split_values(arguments.get("dataset_hints") or config.get("dataset_hints"))
        for value in source["references"]:
            text = str(value or "").strip()
            if not text:
                continue
            if text.startswith("/") or text.startswith("./") or "data" in text.lower():
                if text not in roots:
                    roots.append(text)
            elif text not in hints:
                hints.append(text)

        data_like_names = {
            "data",
            "dataset",
            "datasets",
            "assets",
            "resources",
            "input",
            "inputs",
            "raw",
            "storage",
        }
        scanned_roots: list[str] = []
        discovered_dirs: list[dict[str, Any]] = []
        readme_hints: list[str] = []
        scan_targets: list[str] = []
        if workspace_dir:
            scan_targets.append(workspace_dir)
        scan_targets.extend(roots)
        seen_roots: set[str] = set()
        for root_text in scan_targets:
            text = str(root_text or "").strip()
            if not text or text in seen_roots:
                continue
            seen_roots.add(text)
            root_path = Path(text).expanduser()
            if not root_path.is_absolute() and workspace_dir:
                resolved = _safe_workspace_path(workspace_dir, text)
                root_path = resolved or (Path(workspace_dir).expanduser() / text.lstrip("/"))
            root_path = root_path.resolve()
            if not root_path.exists() or not root_path.is_dir():
                continue
            scanned_roots.append(str(root_path))
            entries = _scan_directory(root_path, max_depth=2, max_entries=120, include_dirs=True, include_files=False)
            for entry in entries:
                name = str(entry.get("name") or "").strip().lower()
                rel = str(entry.get("path") or "").strip()
                if not rel:
                    continue
                if name in data_like_names or "data" in name or "dataset" in name:
                    discovered_dirs.append(
                        {
                            "name": entry.get("name"),
                            "path": rel,
                            "root": str(root_path),
                            "depth": entry.get("depth"),
                        }
                    )
                    candidate = rel if rel.startswith("/") else str((root_path / rel).resolve())
                    if candidate not in roots:
                        roots.append(candidate)

        if workspace_dir:
            for readme_name in ("README.md", "README.rst", "readme.md", "README"):
                readme_path = _safe_workspace_path(workspace_dir, readme_name)
                if not readme_path or not readme_path.is_file():
                    continue
                try:
                    text = readme_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for line in text.splitlines():
                    normalized = line.strip()
                    if not normalized:
                        continue
                    lower = normalized.lower()
                    if any(token in lower for token in ("dataset", "data/", "download", "数据", "数据集")):
                        if normalized not in readme_hints:
                            readme_hints.append(normalized[:200])
                break

        merged_hints = hints + readme_hints
        status = "found" if roots or merged_hints else "draft"
        return {
            "status": status,
            "query": query,
            "data_roots": roots[:16],
            "dataset_hints": merged_hints[:16],
            "scanned_roots": scanned_roots[:8],
            "discovered_dirs": discovered_dirs[:24],
            "message": (
                f"发现 {len(roots)} 个数据根目录、{len(merged_hints)} 条线索。"
                if status == "found"
                else "等待 workspace_dir、数据根目录或参考线索。"
            ),
        }

    def execute_dir_scan(self, arguments: dict[str, Any]) -> dict[str, Any]:
        source = self.source_payload()
        config = self.node_config("dataset.find")
        workspace_dir = str(arguments.get("workspace_dir") or source.get("workspace_dir") or config.get("workspace_dir") or "").strip()
        scan_root = str(arguments.get("path") or arguments.get("root") or workspace_dir or "").strip()
        if not scan_root:
            return {"status": "draft", "message": "等待 workspace_dir 或 path。", "entries": []}
        root_path = Path(scan_root).expanduser()
        if not root_path.is_absolute() and workspace_dir:
            resolved = _safe_workspace_path(workspace_dir, scan_root)
            root_path = resolved or (Path(workspace_dir).expanduser() / scan_root.lstrip("/"))
        root_path = root_path.resolve()
        if not root_path.exists():
            return {"status": "missing", "root": str(root_path), "message": "目录不存在。", "entries": []}
        if not root_path.is_dir():
            return {"status": "blocked", "root": str(root_path), "message": "目标不是目录。", "entries": []}
        max_depth = max(0, min(int(float(arguments.get("max_depth") or 2)), 4))
        max_entries = max(20, min(int(float(arguments.get("max_entries") or 180)), 400))
        entries = _scan_directory(root_path, max_depth=max_depth, max_entries=max_entries)
        return {
            "status": "scanned",
            "root": str(root_path),
            "entry_count": len(entries),
            "truncated": len(entries) >= max_entries,
            "max_depth": max_depth,
            "entries": entries,
        }

    def execute_artifact_read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        artifacts = self.workspace_artifacts()
        output_key = str(arguments.get("output_key") or arguments.get("key") or "").strip()
        label = str(arguments.get("label") or "").strip().lower()
        node_kind = str(arguments.get("node_kind") or "").strip()
        if output_key:
            artifacts = [item for item in artifacts if str(item.get("output_key") or item.get("path") or "").strip() == output_key]
        if label:
            artifacts = [item for item in artifacts if label in str(item.get("label") or "").strip().lower()]
        if node_kind:
            artifacts = [item for item in artifacts if str(item.get("node_kind") or "").strip() == node_kind]

        read_path = str(arguments.get("path") or arguments.get("content_path") or "").strip()
        file_payload: dict[str, Any] | None = None
        if read_path:
            source = self.source_payload()
            resolved = _safe_workspace_path(source.get("workspace_dir") or "", read_path)
            if resolved and resolved.is_file():
                try:
                    text = resolved.read_text(encoding="utf-8", errors="replace")
                    file_payload = {
                        "path": read_path,
                        "size": resolved.stat().st_size,
                        "content": text[:8000],
                        "truncated": len(text) > 8000,
                    }
                except OSError as exc:
                    file_payload = {"path": read_path, "error": str(exc)}

        return {
            "status": "read" if artifacts or file_payload else "draft",
            "artifact_count": len(artifacts),
            "artifacts": artifacts[:20],
            "file": file_payload,
        }

    def execute(self, tool_id: str, arguments: dict[str, Any]) -> str:
        arguments = arguments if isinstance(arguments, dict) else {}
        workspace_snapshot = self.workspace

        if tool_id == "workflow.plan":
            nodes = self.workflow_nodes()
            return json.dumps(
                {
                    "status": "planned" if nodes else "draft",
                    "workspace_id": str(workspace_snapshot.get("id") or "").strip(),
                    "workspace_name": str(workspace_snapshot.get("name") or "").strip(),
                    "node_count": len(nodes),
                    "nodes": nodes,
                    "run_command": self.configured_run_command(),
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "web.search":
            source = self.source_payload()
            query = str(arguments.get("query") or source.get("goal_text") or "").strip()
            results = [
                {"type": "repo", "url": url, "source": "workspace.input"}
                for url in source["repo_urls"]
            ] + [
                {"type": "paper", "url": url, "source": "workspace.input"}
                for url in source["paper_urls"]
            ]
            return json.dumps(
                {
                    "status": "seeded" if results else "draft",
                    "query": query,
                    "results": results,
                    "note": "当前工具返回工作台已有搜索种子；真正联网搜索应由受控搜索工具接管。",
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "repo.clone":
            source = self.source_payload()
            repo_url = str(arguments.get("repo_url") or (source["repo_urls"][0] if source["repo_urls"] else "")).strip()
            workspace_dir = str(arguments.get("workspace_dir") or source.get("workspace_dir") or "").strip()
            return json.dumps(
                {
                    "status": "ready" if repo_url and workspace_dir else "draft",
                    "repo_url": repo_url,
                    "workspace_dir": workspace_dir,
                    "dry_run": True,
                    "message": "已生成克隆计划，等待工作流节点提交实际任务。" if repo_url else "等待 repo_url。",
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "gpu.inspect":
            min_free_mib = int(float(arguments.get("min_free_mib") or 0))
            candidates = self.gpu_candidates(min_free_mib=min_free_mib, server_id=str(arguments.get("server_id") or "").strip())
            return json.dumps(
                {
                    "status": "inspected" if self.statuses else "draft",
                    "server_count": len(self.statuses),
                    "gpu_count": len(candidates),
                    "idle_count": len([item for item in candidates if item["eligible"]]),
                    "candidates": candidates[:12],
                    "selected": candidates[0] if candidates else self.automation_selected_gpu(),
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "gpu.allocate":
            min_free_mib = int(float(arguments.get("min_free_mib") or 0))
            if not min_free_mib:
                min_free_gib = float(arguments.get("min_free_memory_gib") or self.node_config("gpu.allocate").get("min_free_memory_gib") or 0)
                min_free_mib = int(min_free_gib * 1024)
            config = self.node_config("gpu.allocate")
            server_id = str(arguments.get("server_id") or config.get("server_id") or "").strip()
            candidates = self.gpu_candidates(min_free_mib=min_free_mib, server_id=server_id)
            selected = next((item for item in candidates if item["eligible"]), None)
            if not selected and not candidates:
                scheduler_selected = self.automation_selected_gpu()
                selected = scheduler_selected if scheduler_selected else None
            return json.dumps(
                {
                    "status": "allocated" if selected else "blocked",
                    "selected": selected,
                    "candidate_count": len(candidates),
                    "min_free_mib": min_free_mib,
                    "dry_run": True,
                    "message": "已选出候选 GPU，等待 run.command 使用。" if selected else "没有满足条件的 GPU 候选。",
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "dataset.find":
            return json.dumps(self.execute_dataset_find(arguments), ensure_ascii=False, indent=2)

        if tool_id == "repo.search":
            config = self.node_config("dataset.find")
            source = self.source_payload()
            query = str(arguments.get("query") or config.get("query") or source.get("goal_text") or "").strip()
            roots = _split_values(arguments.get("data_roots") or config.get("data_roots"))
            hints = _split_values(arguments.get("dataset_hints") or config.get("dataset_hints"))
            for value in source["references"]:
                if value not in roots and (value.startswith("/") or value.startswith("./") or "data" in value.lower()):
                    roots.append(value)
                elif value not in hints:
                    hints.append(value)
            return json.dumps(
                {
                    "status": "ready" if roots or hints or query else "draft",
                    "query": query,
                    "data_roots": roots,
                    "dataset_hints": hints,
                    "message": "数据线索已收集，可回填 dataset.find。" if roots or hints else "等待数据集名称、路径或参考链接。",
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "dir.scan":
            return json.dumps(self.execute_dir_scan(arguments), ensure_ascii=False, indent=2)

        if tool_id in {"env.inspect", "env.infer"}:
            env = workspace_snapshot.get("env") if isinstance(workspace_snapshot.get("env"), dict) else {}
            infer_config = self.node_config("env.infer")
            prepare_config = self.node_config("env.prepare")
            manifests = _split_values(arguments.get("manifest_paths") or infer_config.get("manifest_paths"))
            setup_command = str(arguments.get("setup_command") or prepare_config.get("setup_command") or "").strip()
            return json.dumps(
                {
                    "status": "ready" if manifests or setup_command else "draft",
                    "env_name": str(env.get("name") or infer_config.get("env_name") or prepare_config.get("env_name") or "").strip(),
                    "env_manager": str(env.get("manager") or prepare_config.get("env_manager") or "conda").strip(),
                    "python_version": str(env.get("python") or infer_config.get("python_version") or "").strip(),
                    "manifest_paths": manifests,
                    "setup_command": setup_command,
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "job.run":
            run_config = self.node_config("run.command")
            command = str(arguments.get("command") or run_config.get("run_command") or "").strip()
            return json.dumps(
                {
                    "status": "ready" if command else "draft",
                    "dry_run": True,
                    "command": command,
                    "server_id": str(arguments.get("server_id") or run_config.get("server_id") or "").strip(),
                    "gpu_index": str(arguments.get("gpu_index") or run_config.get("gpu_index") or "").strip(),
                    "message": "已生成任务提交包；由工作流运行按钮真正入队。" if command else "等待 run.command。",
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "execution.package":
            package = self.execution_package_payload()
            return json.dumps(
                {
                    "status": "ready" if package["ready_to_execute"] else package["status"] or "draft",
                    "workspace_id": str(workspace_snapshot.get("id") or "").strip(),
                    "workspace_name": str(workspace_snapshot.get("name") or "").strip(),
                    "package": package,
                    "message": "执行包已就绪，可按工作流提交。" if package["ready_to_execute"] else "执行包仍有缺口，请查看 missing/backfill/readiness。",
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "log.read":
            workspace_id = str(workspace_snapshot.get("id") or "").strip()
            related_jobs = [job for job in self.jobs if self.job_workspace_id(job) == workspace_id]
            related_jobs.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
            latest = related_jobs[0] if related_jobs else {}
            return json.dumps(
                {
                    "status": "found" if latest else "draft",
                    "job_id": str(latest.get("id") or "").strip(),
                    "job_status": str(latest.get("status") or "").strip(),
                    "log_path": str(latest.get("log_path") or "").strip(),
                    "message": "找到最近任务日志入口。" if latest else "当前工作台还没有关联任务日志。",
                },
                ensure_ascii=False,
                indent=2,
            )

        if tool_id == "artifact.read":
            return json.dumps(self.execute_artifact_read(arguments), ensure_ascii=False, indent=2)

        if tool_id == "artifact.write":
            try:
                result = apply_artifact_write(
                    workspace_snapshot,
                    node_id=str(arguments.get("node_id") or "").strip(),
                    node_kind=str(arguments.get("node_kind") or "").strip(),
                    label=str(arguments.get("label") or arguments.get("title") or "").strip(),
                    path=str(arguments.get("path") or arguments.get("content_path") or "").strip(),
                    content=str(arguments.get("content") or arguments.get("text") or "").strip(),
                    output_key=str(arguments.get("output_key") or "").strip(),
                    artifact_type=str(arguments.get("type") or arguments.get("artifact_type") or "note").strip(),
                )
                return json.dumps({"status": "written", **result}, ensure_ascii=False, indent=2)
            except ValueError as exc:
                return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

        if tool_id == "workflow.edit":
            patch = arguments.get("config")
            if not isinstance(patch, dict):
                patch = arguments.get("patch") if isinstance(arguments.get("patch"), dict) else {}
            try:
                result = apply_workflow_edit(
                    workspace_snapshot,
                    node_id=str(arguments.get("node_id") or "").strip(),
                    node_kind=str(arguments.get("node_kind") or "").strip(),
                    config_patch=patch,
                )
                return json.dumps({"status": "updated", **result}, ensure_ascii=False, indent=2)
            except ValueError as exc:
                return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

        if tool_id == "report.write":
            try:
                result = apply_artifact_write(
                    workspace_snapshot,
                    node_id=str(arguments.get("node_id") or "").strip(),
                    node_kind=str(arguments.get("node_kind") or "eval.report").strip(),
                    label=str(arguments.get("label") or arguments.get("title") or "report").strip(),
                    path=str(arguments.get("path") or arguments.get("report_path") or "").strip(),
                    content=str(arguments.get("content") or arguments.get("text") or arguments.get("report") or "").strip(),
                    output_key=str(arguments.get("output_key") or "eval_report").strip(),
                    artifact_type="report",
                )
                return json.dumps({"status": "written", **result}, ensure_ascii=False, indent=2)
            except ValueError as exc:
                return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

        if tool_id == "chat.write":
            message = arguments.get("message", "")
            return json.dumps({"status": "written", "message": message}, ensure_ascii=False, indent=2)

        side_effect = tool_side_effect(tool_id)
        meta = TOOL_SIDE_EFFECTS.get(str(tool_id or "").strip(), {})
        implemented = bool(meta.get("implemented"))
        if side_effect != ToolSideEffect.READ and not implemented:
            return json.dumps(
                {
                    "status": "simulated",
                    "tool": tool_id,
                    "side_effect": side_effect.value,
                    "arguments": arguments,
                    "message": f"Tool '{tool_id}' is not implemented yet; returning simulated payload.",
                },
                ensure_ascii=False,
                indent=2,
            )
        return json.dumps(
            {
                "status": "simulated",
                "tool": tool_id,
                "arguments": arguments,
                "message": f"Tool '{tool_id}' executed (simulated)",
            },
            ensure_ascii=False,
            indent=2,
        )


def create_workspace_tool_executor(
    workspace: dict[str, Any],
    server_config: Any = None,
    *,
    statuses: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> Callable[[str, dict[str, Any]], str]:
    """Create a tool executor bound to a workspace snapshot."""
    _ = server_config
    context = WorkspaceToolContext(
        workspace=workspace if isinstance(workspace, dict) else {},
        statuses=[item for item in (statuses or []) if isinstance(item, dict)],
        jobs=[item for item in (jobs or []) if isinstance(item, dict)],
    )

    def executor(tool_id: str, arguments: dict[str, Any]) -> str:
        return context.execute(tool_id, arguments)

    return executor


def summarize_mapped_inputs(mapped_inputs: dict[str, Any] | None, *, limit: int = 6) -> list[dict[str, str]]:
    if not isinstance(mapped_inputs, dict):
        return []
    items: list[dict[str, str]] = []
    for key, value in mapped_inputs.items():
        name = str(key or "").strip()
        if not name:
            continue
        present = value is not None and value != "" and value != [] and value != {}
        items.append(
            {
                "name": name,
                "preview": _preview_value(value),
                "present": "true" if present else "false",
            }
        )
        if len(items) >= limit:
            break
    return items
