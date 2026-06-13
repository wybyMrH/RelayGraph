"""Cockpit — commands helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403

def infer_workspace_setup_command(workspace_dir: str) -> str:
    root = Path(workspace_dir).expanduser()
    if not workspace_dir or not root.exists():
        return ""
    for name in ("environment.yml", "conda.yml", "conda.yaml"):
        if (root / name).exists():
            return f"conda env update -f {name}"
    if (root / "requirements.txt").exists():
        return "pip install -r requirements.txt"
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return "pip install -e ."
    return ""

def infer_workspace_run_command(workspace_dir: str) -> str:
    root = Path(workspace_dir).expanduser()
    if not workspace_dir or not root.exists():
        return ""
    if (root / "pytest.ini").exists() or (root / "tests").exists():
        return "python -m pytest -q"
    if (root / "train.py").exists():
        return "python train.py --help"
    if (root / "main.py").exists():
        return "python main.py --help"
    if (root / "app.py").exists():
        return "python app.py"
    return ""

def infer_workspace_best_gpu(statuses: list[dict[str, Any]]) -> dict[str, Any]:
    best: dict[str, Any] = {}
    best_free = -1
    for status in statuses:
        if not isinstance(status, dict) or not status.get("online"):
            continue
        server_id = str(status.get("id") or "").strip()
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else []):
            if not isinstance(gpu, dict):
                continue
            free = safe_int(gpu.get("memory_free_mib"), 0)
            if str(gpu.get("state") or "") == "idle":
                free += 1_000_000
            if free <= best_free:
                continue
            best_free = free
            best = {
                "server_id": server_id,
                "gpu_index": str(gpu.get("index") if gpu.get("index") is not None else "auto"),
                "memory_free_mib": safe_int(gpu.get("memory_free_mib"), 0),
                "state": str(gpu.get("state") or ""),
            }
    return best
