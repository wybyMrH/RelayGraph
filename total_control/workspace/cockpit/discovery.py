"""Cockpit — discovery helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .helpers import append_unique_text
from ..automation.evidence import workspace_evidence_group
from ..execution import workspace_config_values, workspace_node_config_by_kind

def workspace_path_like_values(workspace: dict[str, Any]) -> list[str]:
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    raw_values: list[Any] = []
    for key in ("references", "context_blocks"):
        values = inputs.get(key)
        if isinstance(values, list):
            raw_values.extend(values)
    raw_values.extend(workspace.get("references") if isinstance(workspace.get("references"), list) else [])
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = str(raw or "").strip()
        if not text or text.startswith(("http://", "https://")):
            continue
        for token in text.replace(",", "\n").splitlines():
            value = token.strip()
            if not value:
                continue
            if value.startswith(("~", "/", "./", "../")) or ":\\" in value:
                if value not in seen:
                    seen.add(value)
                    candidates.append(value)
    return candidates

def workspace_project_path_score(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    markers = {
        ".git": 3,
        "README.md": 2,
        "README.rst": 2,
        "pyproject.toml": 3,
        "requirements.txt": 3,
        "environment.yml": 3,
        "conda.yml": 3,
        "setup.py": 3,
        "train.py": 2,
        "main.py": 2,
        "tests": 1,
    }
    score = 0
    for marker, weight in markers.items():
        if (path / marker).exists():
            score += weight
    return score

def workspace_default_name_seed(workspace: dict[str, Any]) -> str:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    repo_name = repo_name_from_url(str(source.get("repo_url") or ""))
    if repo_name:
        return repo_name
    for value in (workspace.get("name"), workspace.get("brief"), workspace.get("template_name"), workspace.get("id")):
        text = str(value or "").strip()
        if text:
            return text
    return "workspace"

def infer_workspace_dir_from_inputs(workspace: dict[str, Any]) -> str:
    existing = str(workspace.get("workspace_dir") or "").strip()
    if existing:
        return existing
    best_path = ""
    best_score = 0
    for value in workspace_path_like_values(workspace):
        path = Path(value).expanduser()
        score = workspace_project_path_score(path)
        if score > best_score:
            best_score = score
            best_path = str(path)
    if best_path:
        return best_path
    return str((DATA_DIR / "workspaces" / safe_id(workspace_default_name_seed(workspace))).resolve())

def infer_workspace_data_roots(workspace: dict[str, Any], workspace_dir: str = "") -> list[str]:
    roots: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        text = str(value or "").strip()
        if not text or text in seen:
            return
        seen.add(text)
        roots.append(text)

    workspace_path = Path(workspace_dir).expanduser() if workspace_dir else None
    for value in workspace_path_like_values(workspace):
        path = Path(value).expanduser()
        if workspace_path and str(path) == str(workspace_path):
            continue
        if path.exists() and path.is_dir():
            add(str(path))
    if workspace_path:
        for local_name in ("data", "datasets"):
            candidate = workspace_path / local_name
            if candidate.exists():
                add(str(candidate))
    for default_root in ("/mnt/e/datasets", "/mnt/f/datasets", "/data", "data", "datasets"):
        path = Path(default_root).expanduser()
        if default_root.startswith("/") and not path.exists():
            continue
        add(default_root)
    return roots

def workspace_dataset_value_kind(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lower = text.lower()
    if lower.startswith(("http://", "https://", "doi:", "arxiv:", "hf://", "kaggle:")):
        return "source"
    if text.startswith(("~", "/", "./", "../")) or ":\\" in text:
        return "path"
    if any(token in lower for token in ("dataset", "数据集", "benchmark", "imagenet", "coco", "kaggle", "huggingface")):
        return "query"
    return "query"

def derive_workspace_dataset_discovery_plan(
    workspace: dict[str, Any],
    execution: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    path_config = workspace_node_config_by_kind(workspace, "path.resolve")
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    dataset_node_id = next(
        (
            str(node.get("id") or "").strip()
            for node in nodes
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == "dataset.find"
        ),
        "",
    )

    queries: list[str] = []
    local_roots: list[str] = []
    source_refs: list[str] = []
    hints: list[str] = []
    expected_layout = str(dataset_config.get("expected_layout") or "").strip()

    for value in workspace_config_values(dataset_config.get("query")):
        append_unique_text(queries, value)
    for value in workspace_config_values(dataset_config.get("dataset_hints")):
        kind = workspace_dataset_value_kind(value)
        append_unique_text(hints, value)
        if kind == "path":
            append_unique_text(local_roots, value)
        elif kind == "source":
            append_unique_text(source_refs, value)
        else:
            append_unique_text(queries, value)
    for value in workspace_config_values(path_config.get("data_roots")) + workspace_config_values(dataset_config.get("data_roots")):
        append_unique_text(local_roots, value)

    repo_url = str(source.get("repo_url") or "").strip()
    paper_url = str(source.get("paper_url") or "").strip()
    if repo_url:
        append_unique_text(source_refs, repo_url)
        repo_name = repo_name_from_url(repo_url)
        if repo_name:
            append_unique_text(queries, f"{repo_name} dataset")
    if paper_url:
        append_unique_text(source_refs, paper_url)
        append_unique_text(queries, paper_url)

    for value in parse_line_list(inputs.get("paper_urls", [])):
        append_unique_text(source_refs, value)
        append_unique_text(queries, value)
    for value in parse_line_list(inputs.get("repo_urls", [])):
        append_unique_text(source_refs, value)
        repo_name = repo_name_from_url(value)
        append_unique_text(queries, f"{repo_name or value} dataset")
    for value in parse_line_list(inputs.get("references", [])) + parse_line_list(workspace.get("references", [])):
        kind = workspace_dataset_value_kind(value)
        append_unique_text(hints, value)
        if kind == "path":
            append_unique_text(local_roots, value)
        elif kind == "source":
            append_unique_text(source_refs, value)
        else:
            append_unique_text(queries, value)
    for value in parse_line_list(inputs.get("context_blocks", [])):
        lowered = value.lower()
        if any(token in lowered for token in ("dataset", "数据", "benchmark", "kaggle", "huggingface", "imagenet", "coco")):
            append_unique_text(queries, value)
    for value in (
        inputs.get("goal_text"),
        source.get("idea_text"),
        workspace.get("brief"),
        workspace.get("name"),
    ):
        text = str(value or "").strip()
        if text and (not queries or any(token in text.lower() for token in ("dataset", "数据", "benchmark", "复现", "baseline"))):
            append_unique_text(queries, text)

    inferred_roots = infer_workspace_data_roots(workspace, str(workspace.get("workspace_dir") or "").strip())
    for value in inferred_roots:
        append_unique_text(local_roots, value)

    evidence_group = workspace_evidence_group(evidence or [], "dataset")
    evidence_items = evidence_group.get("items") if isinstance(evidence_group.get("items"), list) else []
    found_datasets = [
        str(item.get("value") or "").strip()
        for item in evidence_items
        if isinstance(item, dict)
        and str(item.get("label") or "") in {"候选数据集", "数据集线索"}
        and str(item.get("value") or "").strip()
    ]
    for value in found_datasets:
        append_unique_text(hints, value)

    if not dataset_node_id:
        status = "blocked"
    elif found_datasets:
        status = "ready"
    elif queries or local_roots or source_refs or hints:
        status = "ready"
    else:
        status = "warning"

    actions: list[dict[str, Any]] = []
    if local_roots:
        actions.append(
            {
                "id": "scan_local_roots",
                "label": "扫描本地数据根",
                "status": "ready",
                "detail": f"扫描 {len(local_roots)} 个候选根目录，匹配查询词和目录名。",
            }
        )
    if queries or source_refs:
        actions.append(
            {
                "id": "derive_queries",
                "label": "派生数据集查询",
                "status": "ready" if queries else "warning",
                "detail": f"{len(queries)} 个查询词 · {len(source_refs)} 个资料入口。",
            }
        )
    actions.append(
        {
            "id": "verify_layout",
            "label": "验证数据结构",
            "status": "ready" if found_datasets or expected_layout else "warning",
            "detail": expected_layout or "确认 train/val、images/annotations、metadata 或项目 README 要求。",
        }
    )

    if not dataset_node_id:
        next_action = {
            "action": "switch-workspace-manage",
            "title": "补 dataset.find 节点",
            "detail": "当前链路缺少数据集发现节点，无法形成数据证据。",
            "node_id": "",
        }
    elif found_datasets:
        next_action = {
            "action": "apply-workspace-automation",
            "title": "回填数据集证据",
            "detail": "把发现的数据集路径或线索写回 dataset.find / path.resolve。",
            "node_id": dataset_node_id,
        }
    elif local_roots or queries:
        next_action = {
            "action": "run-workspace-discovery",
            "title": "运行数据集发现",
            "detail": "提交安全发现链，扫描本地数据根并输出 dataset_profile。",
            "node_id": dataset_node_id,
        }
    else:
        next_action = {
            "action": "select-execution-node",
            "title": "补数据集线索",
            "detail": "填写数据集名、下载页、本地路径或论文资料后再发现。",
            "node_id": dataset_node_id,
        }

    return {
        "status": status,
        "summary": f"{len(queries)} 个查询 · {len(local_roots)} 个本地根 · {len(source_refs)} 个资料入口 · {safe_int(evidence_group.get('count'), 0)} 条证据",
        "node_kind": "dataset.find",
        "node_id": dataset_node_id,
        "queries": queries[:12],
        "local_roots": local_roots[:12],
        "source_refs": source_refs[:12],
        "hints": hints[:12],
        "expected_layout": expected_layout,
        "found_datasets": found_datasets[:12],
        "root_verification": workspace_dataset_root_verification(
            local_roots,
            found_datasets,
            hints,
            workspace_dir=str(workspace.get("workspace_dir") or "").strip(),
        ),
        "evidence_count": safe_int(evidence_group.get("count"), 0),
        "actions": actions,
        "next_action": next_action,
    }

def workspace_dataset_root_verification(
    local_roots: list[str],
    found_datasets: list[str],
    hints: list[str],
    *,
    workspace_dir: str = "",
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    workspace_path = Path(workspace_dir).expanduser() if workspace_dir else None

    def resolve_root(value: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute() and workspace_path:
            return workspace_path / path
        return path

    for raw in local_roots:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        path = resolve_root(value)
        if path.exists() and path.is_dir():
            items.append({"path": value, "status": "verified"})
        else:
            items.append({"path": value, "status": "missing"})
    for raw in [*found_datasets, *hints]:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        path = resolve_root(value)
        if path.exists() and path.is_dir():
            items.append({"path": value, "status": "found"})
        else:
            items.append({"path": value, "status": "hint"})
    return items[:24]

def workspace_dataset_discovery_bundle_command(plan: dict[str, Any]) -> str:
    queries = plan.get("queries") if isinstance(plan.get("queries"), list) else []
    local_roots = plan.get("local_roots") if isinstance(plan.get("local_roots"), list) else []
    source_refs = plan.get("source_refs") if isinstance(plan.get("source_refs"), list) else []
    expected_layout = str(plan.get("expected_layout") or "").strip()
    if not queries and not local_roots and not source_refs and not expected_layout:
        return ""
    return f"""python3 - <<'PY'
from pathlib import Path

queries = {json.dumps(queries[:12], ensure_ascii=False)}
local_roots = {json.dumps(local_roots[:12], ensure_ascii=False)}
source_refs = {json.dumps(source_refs[:12], ensure_ascii=False)}
expected_layout = {json.dumps(expected_layout, ensure_ascii=False)}

for query in queries:
    print("dataset_plan_query:", query)
for source in source_refs:
    print("dataset_source:", source)
if expected_layout:
    print("expected_layout:", expected_layout)
terms = [part.lower() for query in queries for part in query.replace("/", " ").replace("_", " ").replace("-", " ").split() if len(part) >= 3]
for raw in local_roots:
    path = Path(raw).expanduser()
    print(f"candidate_root: {{path}} exists={{path.exists()}}")
    if not path.exists() or not path.is_dir():
        continue
    matches = []
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        name = child.name.lower()
        if not terms or any(term in name for term in terms):
            matches.append(child)
        if len(matches) >= 12:
            break
    for child in matches:
        kind = "dir" if child.is_dir() else "file"
        print(f"  match: {{child.name}} ({{kind}})")
PY"""
