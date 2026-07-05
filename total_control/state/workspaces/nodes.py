"""Workspace state — nodes operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class NodesMixin:
    def workspace_node_job_payload(
        self,
        workspace: dict[str, Any],
        node: dict[str, Any],
        *,
        previous_job_id: str = "",
        automation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            raise ValueError("node kind is not executable yet")
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
        workspace_source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
        workspace_recipe = workspace.get("recipes") if isinstance(workspace.get("recipes"), list) and workspace.get("recipes") else []
        recipe = workspace_recipe[0] if workspace_recipe and isinstance(workspace_recipe[0], dict) else {}

        command = ""
        name_suffix = str(node.get("title") or kind).strip() or kind
        workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
        if kind == "run.command":
            command = str(config.get("run_command") or "").strip()
        elif kind == "env.prepare":
            command = str(config.get("setup_command") or recipe.get("setup_command") or "").strip()
        elif kind == "eval.report":
            command = str(config.get("report_command") or recipe.get("report_command") or "").strip()
        elif kind == "repo.clone":
            repo_url = str(config.get("repo_url") or workspace_source.get("repo_url") or "").strip()
            repo_ref = str(config.get("repo_ref") or workspace_source.get("repo_ref") or "").strip()
            if repo_url and workspace_dir:
                parent_dir = os.path.dirname(workspace_dir.rstrip("/")) or "."
                clone_name = os.path.basename(workspace_dir.rstrip("/")) or workspace_dir.rstrip("/")
                clone_parts = ["git", "clone"]
                if repo_ref:
                    clone_parts.extend(["--branch", shlex.quote(repo_ref)])
                clone_parts.extend([shlex.quote(repo_url), shlex.quote(clone_name)])
                command = f"mkdir -p {shlex.quote(parent_dir)} && cd {shlex.quote(parent_dir)} && " + " ".join(clone_parts)
            else:
                command = (
                    "echo "
                    + shlex.quote("[repo.clone] repo_url or workspace_dir missing; waiting for upstream research output")
                )
        elif kind == "path.resolve":
            data_roots = str(config.get("data_roots") or "").strip()
            output_roots = str(config.get("output_roots") or "runs\noutputs\ncheckpoints\nlogs").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

workspace_dir = {json.dumps(workspace_dir)}
data_roots = {json.dumps(data_roots)}
output_roots = {json.dumps(output_roots)}

root = Path(workspace_dir or ".").expanduser()
print("workspace_dir:", root.resolve())
print("workspace_exists:", root.exists())

for label, raw in [("data_root", data_roots), ("output_root", output_roots)]:
    values = [item.strip() for item in raw.replace(",", "\\n").splitlines() if item.strip()]
    if not values:
        print(f"{{label}}: none")
        continue
    for value in values[:20]:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        print(f"{{label}}: {{path.resolve()}} exists={{path.exists()}}")
PY"""
        elif kind == "dataset.find":
            query = str(config.get("query") or workspace_source.get("paper_url") or workspace_source.get("repo_url") or workspace.get("brief") or "").strip()
            dataset_hints = str(config.get("dataset_hints") or "").strip()
            data_roots = str(config.get("data_roots") or "").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

query = {json.dumps(query)}
dataset_hints = {json.dumps(dataset_hints)}
data_roots = {json.dumps(data_roots)}

terms = [part.lower() for part in query.replace("/", " ").replace("_", " ").replace("-", " ").split() if len(part) >= 3]
roots = [item.strip() for item in (data_roots + "\\n" + dataset_hints).replace(",", "\\n").splitlines() if item.strip()]
roots.extend(["/mnt/e/datasets", "/mnt/f/datasets", "/data", "data", "datasets"])
seen = set()
print("dataset_query:", query or "未填写")
for raw in roots:
    path = Path(raw).expanduser()
    key = str(path)
    if key in seen:
        continue
    seen.add(key)
    if not path.exists():
        print(f"candidate_root: {{path}} exists=False")
        continue
    print(f"candidate_root: {{path.resolve()}} exists=True")
    matches = []
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        text = child.name.lower()
        if not terms or any(term in text for term in terms):
            matches.append(child)
        if len(matches) >= 12:
            break
    for child in matches:
        kind = "dir" if child.is_dir() else "file"
        print(f"  match: {{child.name}} ({{kind}})")
PY"""
        elif kind == "env.infer":
            manifest_paths = str(config.get("manifest_paths") or "requirements.txt, pyproject.toml, environment.yml, setup.py").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

workspace_dir = {json.dumps(workspace_dir)}
manifest_paths = {json.dumps(manifest_paths)}
root = Path(workspace_dir or ".").expanduser()
print("workspace_dir:", root.resolve())

found = []
for raw in manifest_paths.replace(",", "\\n").splitlines():
    value = raw.strip()
    if not value:
        continue
    path = root / value
    if path.exists():
        found.append(value)
        print("found_manifest:", value)

if "environment.yml" in found or "conda.yml" in found or "conda.yaml" in found:
    print("suggest_setup: conda env update -f environment.yml")
elif "requirements.txt" in found:
    print("suggest_setup: pip install -r requirements.txt")
elif "pyproject.toml" in found:
    print("suggest_setup: pip install -e .")
else:
    print("suggest_setup: inspect README and build custom setup command")
PY"""
        elif kind == "gpu.allocate":
            gpu_policy = str(config.get("gpu_policy") or "auto").strip()
            min_free_memory_gib = str(config.get("min_free_memory_gib") or "").strip()
            gpu_message = f"[gpu.allocate] policy={gpu_policy} min_free_memory_gib={min_free_memory_gib or '-'}"
            command = (
                "echo "
                + shlex.quote(gpu_message)
                + "; echo \"CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}\"; "
                + "nvidia-smi --query-gpu=index,name,memory.free,utilization.gpu --format=csv,noheader 2>/dev/null || true"
            )
        elif kind == "repo.inspect":
            command = """python3 - <<'PY'
from pathlib import Path

root = Path(".").resolve()
print(f"workspace_dir: {root}")

interesting = [
    "README.md",
    "README.rst",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "environment.yml",
    "conda.yml",
    "conda.yaml",
]
for name in interesting:
    path = root / name
    if path.exists():
        print(f"found: {name}")

top_level = []
for item in sorted(root.iterdir(), key=lambda p: p.name.lower()):
    if item.name.startswith("."):
        continue
    if item.name in {"__pycache__", "node_modules", "dist", "build"}:
        continue
    suffix = "/" if item.is_dir() else ""
    top_level.append(f"{item.name}{suffix}")
    if len(top_level) >= 30:
        break
print("top_level:", ", ".join(top_level))

entry_names = {item.rstrip("/") for item in top_level}
if "pytest.ini" in entry_names or "tests" in entry_names:
    print("suggest_run: python -m pytest -q")
elif "train.py" in entry_names:
    print("suggest_run: python train.py --help")
elif "main.py" in entry_names:
    print("suggest_run: python main.py --help")
elif "app.py" in entry_names:
    print("suggest_run: python app.py")
PY"""
        elif kind == "artifact.collect":
            artifact_paths = str(config.get("artifact_paths") or "runs\noutputs\ncheckpoints\nlogs").strip()
            metric_paths = str(config.get("metric_paths") or "").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

workspace_dir = {json.dumps(workspace_dir)}
artifact_paths = {json.dumps(artifact_paths)}
metric_paths = {json.dumps(metric_paths)}
root = Path(workspace_dir or ".").expanduser()
print("workspace_dir:", root.resolve())

for label, raw in [("artifact", artifact_paths), ("metric", metric_paths)]:
    values = [item.strip() for item in raw.replace(",", "\\n").splitlines() if item.strip()]
    if not values:
        print(f"{{label}}: none")
        continue
    for value in values[:30]:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        print(f"{{label}}: {{path.resolve()}} exists={{path.exists()}}")
PY"""
        if not command:
            raise ValueError("node has no executable command yet")

        gpu_policy = str(config.get("gpu_policy") or "auto").strip().lower()
        server_id = str(config.get("server_id") or "auto").strip() or "auto"
        is_gpu_job = kind in {"run.command", "gpu.allocate"}
        wait_for_idle = kind in {"run.command", "gpu.allocate"} or kind in {"repo.clone", "env.prepare", "eval.report"}
        gpu_index: int | str = "auto"
        if kind in {"repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "env.prepare", "artifact.collect", "eval.report"}:
            gpu_index = "none"
        elif gpu_policy in {"cpu", "none", "no_gpu"}:
            gpu_index = "none"
        else:
            configured_gpu_index = str(config.get("gpu_index") or "").strip()
            if configured_gpu_index and configured_gpu_index != "auto":
                gpu_index = configured_gpu_index
        job_cwd = workspace_dir
        if kind == "repo.clone":
            job_cwd = ""
        elif kind in WORKSPACE_NO_CWD_NODE_KINDS:
            job_cwd = ""
        if automation is None:
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            statuses_snapshot = copy.deepcopy(getattr(self, "statuses", []))
            runtime_workspace = apply_workspace_job_runtime(workspace, jobs_snapshot)
            execution = derive_workspace_execution_state(runtime_workspace, jobs_snapshot)
            automation = derive_workspace_automation_state(runtime_workspace, execution, statuses_snapshot)
        execution_bundle_metadata = workspace_execution_bundle_job_metadata(automation, node)
        scheduler_binding = workspace_scheduler_binding_metadata(automation, config)
        env_name = str(config.get("env_name") or workspace_env.get("name") or "").strip()
        runtime_binding = workspace_execution_package_runtime_binding(
            automation,
            node,
            config,
            fallback={
                "server_id": server_id,
                "gpu_index": str(gpu_index),
                "gpu_policy": gpu_policy,
                "cwd": job_cwd,
                "env_name": env_name,
                "wait_for_idle": wait_for_idle,
                "execution_mode": "gpu" if is_gpu_job else "cpu",
            },
        )
        target_bound = str(runtime_binding.get("source") or "") == "execution_package.target"
        if kind == "run.command" or target_bound:
            if target_bound or kind == "run.command":
                server_id = str(runtime_binding.get("server_id") or server_id).strip() or "auto"
            if is_gpu_job:
                gpu_policy = str(runtime_binding.get("gpu_policy") or gpu_policy).strip().lower() or "auto"
                gpu_index = str(runtime_binding.get("gpu_index") or gpu_index).strip() or "auto"
            else:
                runtime_binding["gpu_policy"] = gpu_policy
                runtime_binding["gpu_index"] = str(gpu_index)
            if target_bound and kind not in WORKSPACE_NO_CWD_NODE_KINDS and kind != "repo.clone":
                job_cwd = str(runtime_binding.get("cwd") or job_cwd).strip()
            elif kind == "run.command":
                job_cwd = str(runtime_binding.get("cwd") or job_cwd).strip()
            if target_bound and kind in {"repo.inspect", "env.prepare", "run.command", "eval.report"}:
                env_name = str(runtime_binding.get("env_name") or env_name).strip()
            elif kind == "run.command":
                env_name = str(runtime_binding.get("env_name") or env_name).strip()
            wait_for_idle = bool(runtime_binding.get("wait_for_idle", wait_for_idle))
        else:
            runtime_binding = {
                "node_kind": kind,
                "source": "node.config",
                "server_id": server_id,
                "gpu_index": str(gpu_index),
                "gpu_policy": gpu_policy,
                "cwd": job_cwd,
                "env_name": env_name,
                "wait_for_idle": wait_for_idle,
            }
        if server_id != "auto" and not self.server_by_id(server_id):
            raise ValueError(f"unknown server: {server_id}")
        runtime_execution_mode = (
            "gpu"
            if is_gpu_job and str(gpu_index).strip().lower() not in {"none", "cpu", "no_gpu"}
            else "cpu"
        )
        runtime_binding["execution_mode"] = runtime_execution_mode
        runtime_binding.setdefault("scheduler_status", str(scheduler_binding.get("status") or "").strip())
        runtime_binding.setdefault("scheduler_summary", str(scheduler_binding.get("summary") or "").strip())
        payload: dict[str, Any] = {
            "name": f"{workspace.get('name') or workspace.get('id') or 'workspace'} · {name_suffix}",
            "server_id": server_id,
            "gpu_index": gpu_index,
            "wait_for_idle": wait_for_idle,
            "command": command,
            "command_display": command,
            "cwd": job_cwd,
            "env_name": env_name,
            "target_job_ids": [str(previous_job_id)] if previous_job_id else [],
            "metadata": {
                "workspace_id": str(workspace.get("id") or "").strip(),
                "node_id": str(node.get("id") or "").strip(),
                "node_kind": kind,
                "node_title": name_suffix,
                "execution_mode": runtime_execution_mode,
                "resource_plan": workspace_node_resources(workspace, node, None),
                "artifact_plan": workspace_node_artifacts(workspace, node, None),
                "workflow_contract_node": workspace_node_workflow_contract_metadata(workspace, node),
                "execution_bundle": execution_bundle_metadata,
                "scheduler_binding": scheduler_binding,
                "runtime_binding": runtime_binding,
            },
            "kind": "command",
        }
        if kind == "run.command":
            runtime_min_free_mib = safe_int(runtime_binding.get("min_free_mib"), 0)
            if runtime_min_free_mib > 0:
                payload["min_free_mib"] = runtime_min_free_mib
        if previous_job_id:
            payload["metadata"]["workflow_prev_job_id"] = previous_job_id
        return payload


    def run_workspace_node(self, workspace_id: str, node_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        node_id = str(node_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        prefer_raw = str(
            requested_payload.get("prefer")
            or requested_payload.get("executor_mode")
            or "auto"
        ).strip().lower()
        prefer = prefer_raw if prefer_raw in {"auto", "job", "agent", "skip"} else "auto"
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            statuses_snapshot = copy.deepcopy(getattr(self, "statuses", []))
            node = next(
                (
                    item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
                    if isinstance(item, dict) and str(item.get("id") or "").strip() == node_id
                ),
                None,
            )
            if not node:
                raise ValueError("node not found")
            workspace = copy.deepcopy(workspace)
            node = copy.deepcopy(node)
        runtime_workspace = apply_workspace_job_runtime(workspace, jobs_snapshot)
        execution = derive_workspace_execution_state(runtime_workspace, jobs_snapshot)
        automation = derive_workspace_automation_state(runtime_workspace, execution, statuses_snapshot)
        executor_mode = resolve_node_executor_mode(node, prefer)
        node_title = str(node.get("title") or node.get("kind") or "节点").strip()

        if executor_mode == "agent":
            agent_summary = f"Agent 节点 · {node_title}"
            run = self.register_workspace_execution_run(
                workspace_id,
                kind="node",
                trigger="user",
                summary=agent_summary,
                steps=[],
            )
            run_id = str(run.get("id") or "").strip()
            step_result = self.execute_workspace_agent_node(
                workspace_id,
                node,
                run_context=ExecutionRunContext(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    kind="node",
                    trigger="user",
                ),
            )
            run = self.update_workspace_execution_run_steps(
                workspace_id,
                run_id,
                steps=[workspace_run_step_from_agent(node, step_result, 0)],
                summary=agent_summary,
            )
            if step_result.status in {"completed", "warning"}:
                with self.lock:
                    refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
                    payload_workspace = self.workspace_public_payload(refreshed_workspace)
                return {
                    "executor": "agent",
                    "step": step_result.as_dict(),
                    "run": run,
                    "run_id": run_id,
                    "workspace": payload_workspace,
                }
            if (
                step_result.reason == "input_mapping_blocked"
                or prefer != "auto"
                or str(node.get("kind") or "").strip() not in WORKSPACE_EXECUTABLE_NODE_KINDS
            ):
                with self.lock:
                    refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
                    payload_workspace = self.workspace_public_payload(refreshed_workspace)
                return {
                    "executor": "agent",
                    "step": step_result.as_dict(),
                    "run": run,
                    "run_id": run_id,
                    "workspace": payload_workspace,
                }

        if workspace_nodes_require_execution_package([node]):
            package_checks = workspace_execution_package_blocking_checks(automation, full_workflow=True)
            if package_checks:
                with self.lock:
                    payload_workspace = self.workspace_public_payload(self.workspace_by_id(workspace_id) or workspace)
                raise WorkspaceWorkflowReadinessError(
                    workspace_readiness_message(package_checks),
                    blocked_checks=package_checks,
                    workspace=payload_workspace,
                )

        job_payload = self.workspace_node_job_payload(workspace, node, automation=automation)
        runtime_checks = workspace_execution_package_runtime_binding_checks(automation, node, job_payload)
        if runtime_checks:
            with self.lock:
                payload_workspace = self.workspace_public_payload(self.workspace_by_id(workspace_id) or workspace)
            raise WorkspaceWorkflowReadinessError(
                workspace_readiness_message(runtime_checks),
                blocked_checks=runtime_checks,
                workspace=payload_workspace,
            )
        job = self.create_job(job_payload, publish_events=False)
        run = self.register_workspace_execution_run(
            workspace_id,
            kind="node",
            trigger="user",
            summary=f"单节点运行 · {node_title}",
            jobs=[job],
        )
        with self.lock:
            refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
            payload_workspace = self.workspace_public_payload(refreshed_workspace)
        return {
            "executor": "job",
            "job": job,
            "run": run,
            "run_id": run["id"],
            "workspace": payload_workspace,
        }
