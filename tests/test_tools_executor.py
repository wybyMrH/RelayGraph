import json
import tempfile
import unittest
from pathlib import Path

from total_control.orchestration.workspace_mutations import apply_artifact_write
from total_control.tools.registry import create_workspace_tool_executor


class WorkspaceToolExecutorTests(unittest.TestCase):
    def test_dir_scan_lists_files_under_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# demo", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "sample.txt").write_text("hello", encoding="utf-8")
            workspace = {"id": "ws-scan", "workspace_dir": str(root), "nodes": []}
            executor = create_workspace_tool_executor(workspace)
            payload = json.loads(executor("dir.scan", {"max_depth": 2}))
            self.assertEqual(payload["status"], "scanned")
            names = {item["name"] for item in payload.get("entries") or []}
            self.assertIn("README.md", names)
            self.assertIn("sample.txt", names)

    def test_artifact_read_returns_runtime_and_context_outputs(self) -> None:
        workspace = {
            "id": "ws-read",
            "workspace_dir": "/tmp/unused",
            "nodes": [
                {
                    "id": "node-inspect",
                    "kind": "repo.inspect",
                    "handler": {"output_key": "repo_profile"},
                    "runtime": {"artifacts": []},
                }
            ],
            "automation": {"execution_context": {"outputs": {}}},
        }
        apply_artifact_write(
            workspace,
            node_kind="repo.inspect",
            label="repo profile",
            path="artifacts/repo_profile.json",
            content='{"entry":"train.py"}',
            output_key="repo_profile",
        )
        executor = create_workspace_tool_executor(workspace)
        payload = json.loads(executor("artifact.read", {"output_key": "repo_profile"}))
        self.assertEqual(payload["status"], "read")
        self.assertGreaterEqual(payload.get("artifact_count") or 0, 1)
        self.assertTrue(any(item.get("output_key") == "repo_profile" for item in payload.get("artifacts") or []))

    def test_dataset_find_scans_workspace_for_data_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data" / "imagenet"
            data_dir.mkdir(parents=True)
            (data_dir / "labels.txt").write_text("label", encoding="utf-8")
            (root / "README.md").write_text("# Demo\nDataset lives under data/imagenet\n", encoding="utf-8")
            workspace = {
                "id": "ws-dataset",
                "workspace_dir": str(root),
                "inputs": {"goal_text": "find dataset", "references": []},
                "nodes": [{"id": "node-dataset", "kind": "dataset.find", "config": {}}],
            }
            executor = create_workspace_tool_executor(workspace)
            payload = json.loads(executor("dataset.find", {"workspace_dir": str(root)}))
            self.assertEqual(payload["status"], "found")
            self.assertTrue(any("data" in str(item).lower() for item in payload.get("data_roots") or []))
            self.assertTrue(any("dataset" in str(item).lower() for item in payload.get("dataset_hints") or []))

    def test_artifact_read_file_content_within_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "notes.txt"
            target.write_text("artifact body", encoding="utf-8")
            workspace = {"id": "ws-file", "workspace_dir": str(root), "nodes": []}
            executor = create_workspace_tool_executor(workspace)
            payload = json.loads(executor("artifact.read", {"path": "notes.txt"}))
            self.assertEqual(payload["status"], "read")
            self.assertIn("artifact body", str((payload.get("file") or {}).get("content") or ""))


if __name__ == "__main__":
    unittest.main()
