"""Execution — log_parser helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .paths import compact_workspace_command, workspace_path_probe

def workspace_log_path_artifact(label: str, path_text: str, exists_text: str, source: str) -> dict[str, Any]:
    exists = str(exists_text or "").strip().lower() == "true"
    return {
        "label": label,
        "path": str(path_text or "").strip(),
        "resolved_path": str(path_text or "").strip(),
        "source": source,
        "status": "found" if exists else "expected",
        "exists": exists,
    }

def workspace_manifest_setup_suggestion(manifests: list[str]) -> str:
    names = {Path(str(item or "").strip()).name.lower() for item in manifests if str(item or "").strip()}
    if names.intersection({"environment.yml", "conda.yml", "conda.yaml"}):
        return "conda env update -f environment.yml"
    if "requirements.txt" in names:
        return "pip install -r requirements.txt"
    if "pyproject.toml" in names or "setup.py" in names:
        return "pip install -e ."
    return ""

def workspace_run_command_suggestion_from_entries(entries: list[str] | set[str] | tuple[str, ...]) -> str:
    names = {Path(str(item or "").strip().rstrip("/")).name.lower() for item in entries if str(item or "").strip()}
    if "pytest.ini" in names or "tests" in names:
        return "python -m pytest -q"
    if "train.py" in names:
        return "python train.py --help"
    if "main.py" in names:
        return "python main.py --help"
    if "app.py" in names:
        return "python app.py"
    return ""

def workspace_repo_inspect_top_level_artifacts(workspace_dir: str, top_level_text: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for raw_entry in str(top_level_text or "").split(","):
        entry = raw_entry.strip()
        if not entry or not entry.endswith("/"):
            continue
        name = entry.rstrip("/").strip()
        if not name:
            continue
        normalized = name.lower()
        path_text = str(Path(workspace_dir) / name) if workspace_dir else name
        if normalized in WORKSPACE_DATA_DIR_NAMES or "dataset" in normalized:
            artifacts.append(workspace_log_path_artifact("候选数据根", path_text, "True", "log"))
        elif normalized in WORKSPACE_OUTPUT_DIR_NAMES:
            artifacts.append(workspace_log_path_artifact("输出目录", path_text, "True", "log"))
            if normalized in {"result", "results"}:
                artifacts.append(workspace_log_path_artifact("指标路径", path_text, "True", "log"))
        elif normalized in WORKSPACE_ARTIFACT_DIR_NAMES:
            artifacts.append(workspace_log_path_artifact("产物路径", path_text, "True", "log"))
    return artifacts

def workspace_dedupe_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        path_text = str(item.get("resolved_path") or item.get("path") or "").strip()
        source = str(item.get("source") or "").strip()
        key = (label, path_text, source)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result

def parse_workspace_artifacts_from_log(kind: str, log_text: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    workspace_dir = ""
    current_candidate_root = ""
    for raw_line in str(log_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("workspace_dir:"):
            workspace_dir = line.split(":", 1)[1].strip()
            if workspace_dir:
                artifacts.append(workspace_log_path_artifact("工作目录", workspace_dir, "True", "log"))
            continue
        for prefix, label in (
            ("data_root:", "数据根目录"),
            ("output_root:", "输出目录"),
            ("candidate_root:", "候选数据根"),
            ("artifact:", "产物路径"),
            ("metric:", "指标路径"),
        ):
            if not line.startswith(prefix):
                continue
            payload = line.split(":", 1)[1].strip()
            path_text, exists_text = payload, ""
            if " exists=" in payload:
                path_text, exists_text = payload.rsplit(" exists=", 1)
            artifacts.append(workspace_log_path_artifact(label, path_text.strip(), exists_text, "log"))
            if prefix == "candidate_root:" and str(exists_text).strip().lower() == "true":
                current_candidate_root = path_text.strip()
            break
        else:
            if line.startswith(("dataset_query:", "dataset_plan_query:")):
                value = line.split(":", 1)[1].strip()
                if value:
                    artifacts.append(
                        {
                            "label": "检索词",
                            "path": value,
                            "source": "log",
                            "status": "planned",
                        }
                    )
            elif line.startswith("dataset_source:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    artifacts.append(
                        {
                            "label": "数据来源线索",
                            "path": value,
                            "source": "log",
                            "status": "planned",
                        }
                    )
            elif line.startswith("expected_layout:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    artifacts.append(
                        {
                            "label": "数据结构要求",
                            "path": value,
                            "source": "log",
                            "status": "planned",
                        }
                    )
            elif line.startswith("match:") and current_candidate_root:
                name = line.split(":", 1)[1].strip().split(" (", 1)[0].strip()
                if name:
                    artifacts.append(
                        {
                            "label": "候选数据集",
                            "path": str(Path(current_candidate_root) / name),
                            "resolved_path": str(Path(current_candidate_root) / name),
                            "source": "log",
                            "status": "found",
                            "exists": True,
                        }
                    )
            elif line.startswith("found:"):
                name = line.split(":", 1)[1].strip()
                if name:
                    normalized = Path(name).name.lower()
                    path_text = str(Path(workspace_dir) / name) if workspace_dir else name
                    if normalized in WORKSPACE_ENV_MANIFEST_NAMES:
                        artifacts.append(workspace_log_path_artifact("环境清单", path_text, "True", "log"))
                    elif normalized.startswith("readme"):
                        artifacts.append(workspace_log_path_artifact("项目文档", path_text, "True", "log"))
            elif line.startswith("top_level:"):
                artifacts.extend(workspace_repo_inspect_top_level_artifacts(workspace_dir, line.split(":", 1)[1].strip()))
            elif line.startswith("found_manifest:"):
                name = line.split(":", 1)[1].strip()
                if name:
                    artifacts.append(workspace_path_probe(name, root=workspace_dir, label="环境清单", source="log"))
    return workspace_dedupe_artifacts(artifacts)

def parse_workspace_resources_from_log(kind: str, log_text: str) -> dict[str, Any]:
    resources: dict[str, Any] = {}
    manifests: list[str] = []
    gpu_snapshot: list[dict[str, Any]] = []
    repo_entries: list[str] = []
    dataset_queries: list[str] = []
    dataset_sources: list[str] = []
    expected_layout = ""
    for raw_line in str(log_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("suggest_setup:"):
            resources["setup_suggestion"] = line.split(":", 1)[1].strip()
        elif line.startswith("suggest_run:"):
            resources["run_suggestion"] = line.split(":", 1)[1].strip()
        elif line.startswith("found_manifest:"):
            value = line.split(":", 1)[1].strip()
            if value and value not in manifests:
                manifests.append(value)
        elif line.startswith("found:"):
            value = line.split(":", 1)[1].strip()
            if Path(value).name.lower() in WORKSPACE_ENV_MANIFEST_NAMES and value not in manifests:
                manifests.append(value)
            if value:
                repo_entries.append(value)
        elif line.startswith("top_level:"):
            repo_entries.extend(
                [item.strip().rstrip("/") for item in line.split(":", 1)[1].split(",") if item.strip()]
            )
        elif line.startswith("[gpu.allocate]"):
            resources["gpu_policy_summary"] = line
        elif line.startswith("CUDA_VISIBLE_DEVICES=") or line.startswith("CUDA_VISIBLE_DEVICES:"):
            resources["cuda_visible_devices"] = line.split("=", 1)[1].strip() if "=" in line else line.split(":", 1)[1].strip()
        elif kind == "gpu.allocate" and "," in line:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 4 and parts[0].isdigit():
                gpu_snapshot.append(
                    {
                        "index": parts[0],
                        "name": parts[1],
                        "memory_free": parts[2],
                        "utilization": parts[3],
                    }
                )
        elif kind == "dataset.find" and line.startswith(("dataset_query:", "dataset_plan_query:")):
            value = line.split(":", 1)[1].strip()
            if value and value not in dataset_queries:
                dataset_queries.append(value)
        elif kind == "dataset.find" and line.startswith("dataset_source:"):
            value = line.split(":", 1)[1].strip()
            if value and value not in dataset_sources:
                dataset_sources.append(value)
        elif kind == "dataset.find" and line.startswith("expected_layout:"):
            expected_layout = line.split(":", 1)[1].strip()
    if manifests:
        resources["found_manifests"] = manifests
    if manifests and not resources.get("setup_suggestion"):
        setup_suggestion = workspace_manifest_setup_suggestion(manifests)
        if setup_suggestion:
            resources["setup_suggestion"] = setup_suggestion
    if kind == "repo.inspect" and not resources.get("run_suggestion"):
        run_suggestion = workspace_run_command_suggestion_from_entries(repo_entries)
        if run_suggestion:
            resources["run_suggestion"] = run_suggestion
    if dataset_queries:
        resources["dataset_queries"] = dataset_queries[:12]
    if dataset_sources:
        resources["dataset_sources"] = dataset_sources[:12]
    if expected_layout:
        resources["expected_layout"] = expected_layout
    if gpu_snapshot:
        resources["gpu_snapshot"] = gpu_snapshot[:16]
    return resources

def normalize_workspace_metric_key(value: str) -> str:
    key = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "acc": "accuracy",
        "map": "mAP",
        "rougel": "rougeL",
        "rouge_l": "rougeL",
        "ppl": "perplexity",
        "top_1": "top1",
        "top_5": "top5",
    }
    return aliases.get(key, key)

def parse_workspace_metrics_from_log(kind: str, log_text: str) -> list[dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for raw_line in str(log_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for match in WORKSPACE_METRIC_PATTERN.finditer(line):
            key = normalize_workspace_metric_key(match.group("key"))
            value = match.group("value")
            metrics[key] = {
                "key": key,
                "label": key,
                "value": value,
                "raw": compact_workspace_command(line, limit=180),
                "source": "log",
                "node_kind": kind,
                "status": "found",
            }
    return list(metrics.values())[:24]
