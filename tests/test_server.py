from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import total_control.server as server_module
from total_control.agent_executor import create_workspace_tool_executor
from total_control.server import (
    AppConfig,
    ServerConfig,
    TotalControlState,
    browse_local_files,
    cleanup_preview_cache,
    collect_server,
    build_transfer_command,
    check_transfer_conflicts,
    normalize_rsync_directory_source,
    transfer_item_destination_path,
    download_remote_file_to_local,
    gpu_activity_state,
    load_config,
    parse_loadavg,
    parse_meminfo,
    parse_proc_net_dev,
    parse_remote_marked_json,
    preview_kind_for_path,
    read_local_text_file,
    run_server_checks,
    stop_server_process,
)


def make_registry_state() -> TotalControlState:
    state = object.__new__(TotalControlState)
    state.lock = threading.RLock()
    state.config = AppConfig()
    state.servers = [ServerConfig(id="local", name="Local", mode="local")]
    state.statuses = []
    state.jobs = []
    state.workspaces = []
    state.next_queue_rank = 1
    state.provider_profiles = []
    state.tool_definitions = server_module.workspace_default_tools()
    state.agent_definitions = server_module.workspace_default_agents()
    state.workflow_templates = server_module.build_default_workflow_templates(
        state.agent_definitions,
        state.tool_definitions,
    )
    state.save_jobs = lambda: None
    state.save_workspaces = lambda: None
    state.save_agent_definitions = lambda: None
    state.save_tool_definitions = lambda: None
    state.save_workflow_templates = lambda: None
    state.save_provider_profiles = lambda: None
    return state


class TotalControlServerTests(unittest.TestCase):
    def test_status_payload_uses_last_refresh_and_poll_interval(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.config = AppConfig(poll_interval_seconds=7)
        state.config_path = Path("/tmp/test-config.toml")
        state.servers = [ServerConfig(id="local", name="Local")]
        state.last_refresh = time.time() - 1.5
        state.last_refreshed_at = "2026-05-21T10:00:00"
        state.statuses = [{"id": "local", "online": True}]
        state.jobs = [{"id": "job-1"}]
        state.workspaces = []

        payload = TotalControlState.status_payload(state)

        self.assertEqual(payload["config"]["poll_interval_seconds"], 7)
        self.assertEqual(payload["refreshed_at"], "2026-05-21T10:00:00")
        self.assertGreaterEqual(payload["status_age_seconds"], 1.0)

    def test_refresh_server_status_updates_only_target_snapshot(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.config = AppConfig()
        state.servers = [
            ServerConfig(id="local", name="Local", mode="local"),
            ServerConfig(id="gpu-box", name="GPU Box", mode="ssh"),
        ]
        state.statuses = [
            {"id": "local", "online": True, "gpus": [{"index": 0, "state": "busy"}]},
            {"id": "gpu-box", "online": False, "gpus": []},
        ]
        state.last_refresh = 0.0
        state.last_refreshed_at = ""
        state.reload_config = lambda: None
        refreshed = {
            "id": "gpu-box",
            "online": True,
            "gpus": [{"index": 1, "state": "idle", "memory_free_mib": 24576}],
            "processes": [],
        }

        with patch.object(server_module, "collect_server", return_value=refreshed) as collect:
            result = TotalControlState.refresh_server_status(state, "gpu-box")

        self.assertEqual(result, refreshed)
        collect.assert_called_once_with(state.servers[1], state.config)
        self.assertEqual([item["id"] for item in state.statuses], ["local", "gpu-box"])
        self.assertEqual(state.statuses[0]["gpus"][0]["state"], "busy")
        self.assertEqual(state.statuses[1]["gpus"][0]["state"], "idle")
        self.assertTrue(state.last_refreshed_at)
        self.assertGreater(state.last_refresh, 0)

    def test_load_config_merges_user_servers_and_discovery_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            ssh_config = root / "ssh-config"
            ssh_config.write_text(
                "\n".join(
                    [
                        "Host gpu-box",
                        "  HostName 10.0.0.8",
                        "  User alice",
                        "",
                        "Host repo-box",
                        "  HostName 10.0.0.9",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            servers_toml = root / "servers.toml"
            servers_toml.write_text(
                f"""
[app]
poll_interval_seconds = 5
remote_timeout_seconds = 6
idle_min_free_mib = 1024
idle_max_gpu_util = 10

[server_aliases]
"local" = "本机"

[[servers]]
id = "local"
name = "Local"
mode = "local"
enabled = true

[ssh_discovery]
enabled = true
config_path = "{ssh_config}"
include = ["*"]
exclude = []
""".strip(),
                encoding="utf-8",
            )
            (root / "user_servers.toml").write_text(
                """
[server_aliases]
"gpu-box" = "计算节点"
""".strip(),
                encoding="utf-8",
            )

            config = load_config(servers_toml)
            server_ids = {server.id for server in config.servers}

            self.assertIn("local", server_ids)
            self.assertIn("gpu-box", server_ids)
            self.assertIn("repo-box", server_ids)
            gpu_box = next(server for server in config.servers if server.id == "gpu-box")
            self.assertEqual(gpu_box.name, "计算节点")
            self.assertEqual(gpu_box.host_name, "10.0.0.8")

    def test_browse_local_files_marks_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for index in range(12):
                (root / f"file_{index:02d}.txt").write_text("x", encoding="utf-8")

            payload = browse_local_files(str(root), max_entries=10)

            self.assertEqual(payload["path"], str(root))
            self.assertEqual(len(payload["entries"]), 10)
            self.assertTrue(payload["truncated"])

    def test_build_transfer_command_blocks_remote_to_remote(self) -> None:
        with self.assertRaisesRegex(ValueError, "暂不支持远程服务器到远程服务器传输"):
            build_transfer_command(
                {
                    "sources": [{"value": "alice@10.0.0.1:/data/src/"}],
                    "target": "bob@10.0.0.2:/data/dst/",
                    "options": {},
                },
                [],
            )

    def test_build_transfer_command_normalizes_remote_target(self) -> None:
        server = ServerConfig(
            id="gpu-box",
            name="GPU Box",
            mode="ssh",
            ssh_alias="gpu-box",
            host_name="10.0.0.8",
            user="alice",
        )

        _actual, display = build_transfer_command(
            {
                "sources": [{"value": "/tmp/train.log"}],
                "target": "alice@10.0.0.8:/srv/logs/",
                "options": {"size_only": True, "resume_partial": True},
            },
            [server],
        )

        self.assertIn("rsync", display)
        self.assertIn("StrictHostKeyChecking=accept-new", display)
        self.assertIn("/tmp/train.log", display)
        self.assertIn("alice@10.0.0.8:/srv/logs/", display)

    def test_normalize_rsync_directory_source_strips_trailing_slash(self) -> None:
        self.assertEqual(normalize_rsync_directory_source("/tmp/project/", True), "/tmp/project")
        self.assertEqual(normalize_rsync_directory_source("/tmp/file.txt", False), "/tmp/file.txt")

    def test_transfer_item_destination_path_preserves_directory_name(self) -> None:
        self.assertEqual(
            transfer_item_destination_path("/tmp/myfolder", True, "/srv/backup/"),
            "/srv/backup/myfolder",
        )
        self.assertEqual(
            transfer_item_destination_path("/tmp/train.log", False, "/srv/backup/"),
            "/srv/backup/train.log",
        )

    def test_build_transfer_command_preserves_directory_name(self) -> None:
        _actual, display = build_transfer_command(
            {
                "sources": [{"value": "/tmp/myfolder/", "path": "/tmp/myfolder", "is_dir": True}],
                "target": "/srv/backup/",
                "options": {},
            },
            [],
        )
        self.assertIn("/tmp/myfolder /srv/backup/", display)
        self.assertNotIn("/tmp/myfolder/ /srv/backup/", display)

    def test_check_transfer_conflicts_detects_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "backup"
            target.mkdir()
            existing = target / "note.txt"
            existing.write_text("old", encoding="utf-8")
            payload = check_transfer_conflicts(
                {
                    "sources": [{"path": str(root / "note.txt"), "value": str(root / "note.txt"), "is_dir": False}],
                    "target": f"{target}/",
                },
                [],
            )
            self.assertTrue(payload["checked"])
            self.assertEqual(len(payload["conflicts"]), 1)
            self.assertEqual(payload["conflicts"][0]["name"], "note.txt")

    def test_run_server_checks_distinguishes_ssh_from_dependency_failures(self) -> None:
        server = ServerConfig(id="gpu-box", name="GPU Box", mode="ssh", host_name="10.0.0.8")

        def fake_remote_runner(_server: ServerConfig, script: str, _timeout: int) -> subprocess.CompletedProcess[str]:
            if "ssh ok" in script:
                return subprocess.CompletedProcess(["ssh"], 0, "ssh ok\n", "")
            if "python3 --version" in script:
                return subprocess.CompletedProcess(["ssh"], 0, "Python 3.11.9\n", "")
            if "nvidia-smi --query-gpu" in script:
                return subprocess.CompletedProcess(["ssh"], 0, "0,uuid,RTX 4090,24576,0,0,30,50.0,350.0\n", "")
            if "tmux -V" in script:
                return subprocess.CompletedProcess(["ssh"], 1, "", "tmux: command not found\n")
            if "rsync --version" in script:
                return subprocess.CompletedProcess(["ssh"], 0, "rsync  version 3.2.7\n", "")
            raise AssertionError(f"unexpected script: {script}")

        result = run_server_checks(server, 5, remote_runner=fake_remote_runner)
        checks = {item["key"]: item for item in result["checks"]}

        self.assertTrue(checks["ssh"]["ok"])
        self.assertTrue(checks["python3"]["ok"])
        self.assertTrue(checks["nvidia-smi"]["ok"])
        self.assertFalse(checks["tmux"]["ok"])
        self.assertIn("command not found", checks["tmux"]["detail"])

    def test_gpu_activity_state_uses_utilization_only(self) -> None:
        self.assertEqual(gpu_activity_state(30, 10), "busy")
        self.assertEqual(gpu_activity_state(0, 10), "idle")
        self.assertEqual(gpu_activity_state(10, 10), "idle")

    def test_gpu_activity_state_marks_vram_usage_as_busy(self) -> None:
        self.assertEqual(
            gpu_activity_state(
                0,
                10,
                memory_used_mib=14900,
                memory_total_mib=24000,
            ),
            "busy",
        )

    def test_gpu_activity_state_marks_processes_as_busy(self) -> None:
        self.assertEqual(gpu_activity_state(0, 10, has_processes=True), "busy")

    def test_workspace_tool_executor_reads_workspace_gpu_env_and_jobs(self) -> None:
        workspace = {
            "id": "ws-1",
            "name": "Reproduce Demo",
            "workspace_dir": "/srv/repro/demo",
            "source": {"repo_url": "https://example.com/repo.git"},
            "inputs": {
                "goal_text": "复现 demo baseline",
                "references": ["/data/imagenet", "ImageNet-1k"],
            },
            "env": {"name": "rg-demo", "manager": "conda", "python": "3.10"},
            "automation": {
                "reproduction_manifest": {
                    "execution_bundle": {
                        "status": "ready",
                        "ready_to_execute": True,
                        "next_action": {"action": "run-selected-workspace", "label": "提交执行包"},
                        "target": {
                            "workspace_dir": "/srv/repro/demo",
                            "server_id": "gpu-box",
                            "gpu_index": "1",
                            "gpu_policy": "auto",
                            "env_name": "rg-demo",
                        },
                        "missing": [],
                        "command_script": {
                            "shell": "bash",
                            "status": "ready",
                            "ready": True,
                            "summary": "6 个步骤 · 0 阻塞",
                            "text": "cd /srv/repro/demo\npython train.py --data /data/imagenet\n",
                        },
                        "package_manifest": {
                            "commands": {"run_command": "python train.py --data /data/imagenet"},
                            "paths": {
                                "workspace_dir": "/srv/repro/demo",
                                "data_roots": ["/data/imagenet"],
                                "artifact_paths": ["runs"],
                            },
                            "dataset_discovery": {"status": "ready", "local_roots": ["/data/imagenet"]},
                        },
                    }
                },
                "resource_orchestration": {
                    "scheduler": {
                        "status": "ready",
                        "mode": "gpu",
                        "policy": "auto",
                        "summary": "1/2 个候选可用",
                        "selected": {"server_id": "gpu-box", "gpu_index": "1", "memory_free_mib": 18000},
                        "candidate_count": 2,
                        "ready_count": 1,
                    }
                },
                "evidence_backfill": {
                    "status": "ready",
                    "summary": "1 项可回填",
                    "ready_count": 1,
                    "items": [
                        {
                            "node_kind": "artifact.collect",
                            "field": "artifact_paths",
                            "label": "发现产物路径",
                            "value": "runs",
                            "status": "ready",
                        }
                    ],
                },
                "execution_readiness": {
                    "status": "ready",
                    "summary": "执行包可提交",
                    "gate": {"status": "ready"},
                },
            },
            "nodes": [
                {
                    "id": "dataset",
                    "kind": "dataset.find",
                    "title": "找数据",
                    "config": {"query": "ImageNet", "data_roots": "/data/imagenet"},
                },
                {
                    "id": "env",
                    "kind": "env.infer",
                    "title": "推断环境",
                    "config": {"manifest_paths": "requirements.txt, pyproject.toml"},
                },
                {
                    "id": "prepare",
                    "kind": "env.prepare",
                    "title": "准备环境",
                    "config": {"setup_command": "pip install -r requirements.txt"},
                },
                {
                    "id": "gpu",
                    "kind": "gpu.allocate",
                    "title": "分配 GPU",
                    "config": {"server_id": "gpu-box", "min_free_memory_gib": "8"},
                },
                {
                    "id": "run",
                    "kind": "run.command",
                    "title": "运行",
                    "config": {"run_command": "python train.py --data /data/imagenet", "gpu_index": "auto"},
                },
            ],
        }
        statuses = [
            {
                "id": "gpu-box",
                "name": "GPU Box",
                "online": True,
                "collected_at": "2026-06-08T20:00:00",
                "gpus": [
                    {"index": 0, "name": "RTX", "memory_free_mib": 24000, "memory_total_mib": 24576, "gpu_util": 98, "state": "busy"},
                    {"index": 1, "name": "RTX", "memory_free_mib": 18000, "memory_total_mib": 24576, "gpu_util": 0, "state": "idle"},
                ],
            }
        ]
        jobs = [
            {
                "id": "job-1",
                "status": "done",
                "metadata": {"workspace_id": "ws-1"},
                "log_path": "/tmp/job-1.log",
                "updated_at": "2026-06-08T20:10:00",
            }
        ]

        executor = create_workspace_tool_executor(workspace, statuses=statuses, jobs=jobs)

        plan = json.loads(executor("workflow.plan", {}))
        self.assertEqual(plan["node_count"], 5)
        self.assertEqual(plan["run_command"], "python train.py --data /data/imagenet")

        dataset = json.loads(executor("dataset.find", {}))
        self.assertEqual(dataset["status"], "ready")
        self.assertIn("/data/imagenet", dataset["data_roots"])
        self.assertIn("ImageNet-1k", dataset["dataset_hints"])

        env = json.loads(executor("env.infer", {}))
        self.assertEqual(env["env_name"], "rg-demo")
        self.assertIn("requirements.txt", env["manifest_paths"])
        self.assertEqual(env["setup_command"], "pip install -r requirements.txt")

        allocation = json.loads(executor("gpu.allocate", {}))
        self.assertEqual(allocation["status"], "allocated")
        self.assertEqual(allocation["selected"]["server_id"], "gpu-box")
        self.assertEqual(allocation["selected"]["gpu_index"], 1)

        run = json.loads(executor("job.run", {}))
        self.assertTrue(run["dry_run"])
        self.assertEqual(run["command"], "python train.py --data /data/imagenet")

        package = json.loads(executor("execution.package", {}))
        self.assertEqual(package["status"], "ready")
        self.assertTrue(package["package"]["ready_to_execute"])
        self.assertEqual(package["package"]["target"]["server_id"], "gpu-box")
        self.assertEqual(package["package"]["scheduler"]["selected"]["gpu_index"], "1")
        self.assertEqual(package["package"]["commands"]["run_command"], "python train.py --data /data/imagenet")
        self.assertEqual(package["package"]["backfill"]["items"][0]["field"], "artifact_paths")
        self.assertIn("python train.py", package["package"]["script"]["text"])

        log = json.loads(executor("log.read", {}))
        self.assertEqual(log["status"], "found")
        self.assertEqual(log["job_id"], "job-1")

    def test_host_resource_parsers_report_memory_load_and_network(self) -> None:
        memory = parse_meminfo(
            "\n".join(
                [
                    "MemTotal:       1024000 kB",
                    "MemAvailable:    256000 kB",
                    "SwapTotal:       512000 kB",
                    "SwapFree:        128000 kB",
                ]
            )
        )
        load = parse_loadavg("1.50 0.75 0.25 3/200 9912", cpu_count=4)
        network = parse_proc_net_dev(
            "\n".join(
                [
                    "Inter-|   Receive                                                |  Transmit",
                    " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed",
                    "    lo: 100 1 0 0 0 0 0 0 100 1 0 0 0 0 0 0",
                    "  eth0: 2048 8 0 0 0 0 0 0 4096 9 0 0 0 0 0 0",
                ]
            )
        )

        self.assertEqual(memory["memory"]["total_bytes"], 1024000 * 1024)
        self.assertEqual(memory["memory"]["used_bytes"], 768000 * 1024)
        self.assertEqual(memory["memory"]["used_percent"], 75.0)
        self.assertEqual(memory["swap"]["used_percent"], 75.0)
        self.assertEqual(load["load1"], 1.5)
        self.assertEqual(load["load_percent"], 37.5)
        self.assertEqual(load["running_processes"], 3)
        self.assertEqual(network["rx_bytes"], 2048)
        self.assertEqual(network["tx_bytes"], 4096)
        self.assertEqual(network["interfaces"][0]["name"], "eth0")

    def test_collect_server_attaches_host_resources_to_gpu_snapshot(self) -> None:
        server = ServerConfig(id="local", name="Local", mode="local")
        config = AppConfig(remote_timeout_seconds=3)
        gpu_result = subprocess.CompletedProcess(
            ["nvidia-smi"],
            0,
            "0, GPU-local, RTX Test, 24576, 1024, 5, 42, 55, 450\n",
            "",
        )
        proc_result = subprocess.CompletedProcess(["nvidia-smi"], 0, "", "")
        host_resources = {
            "ok": True,
            "cpu": {"util_percent": 12.5},
            "memory": {"used_percent": 33.0},
            "disks": [],
            "network": {"interfaces": []},
        }

        with patch.object(server_module, "run_command", side_effect=[gpu_result, proc_result]):
            with patch.object(server_module, "collect_host_resources", return_value=host_resources) as host_probe:
                payload = collect_server(server, config)

        host_probe.assert_called_once()
        self.assertTrue(payload["online"])
        self.assertTrue(payload["host_resources"]["ok"])
        self.assertEqual(payload["host_resources"]["cpu"]["util_percent"], 12.5)

    def test_collect_all_reuses_recent_connection_failure(self) -> None:
        server = ServerConfig(id="offline-box", name="Offline", mode="ssh", host_name="10.0.0.9")
        previous = {
            "id": "offline-box",
            "online": False,
            "reachable": False,
            "error_kind": "connection",
            "error": "timeout",
            "collected_at": server_module.now_iso(),
            "gpus": [],
            "processes": [],
        }

        with patch.object(server_module, "collect_server") as collect:
            statuses = server_module.collect_all([server], AppConfig(), previous_statuses=[previous])

        collect.assert_not_called()
        self.assertEqual(statuses[0]["id"], "offline-box")
        self.assertTrue(statuses[0]["refresh_skipped"])
        self.assertEqual(statuses[0]["refresh_skip_reason"], "connection_backoff")

    def test_collect_server_timeout_uses_ssh_probe_for_reachability(self) -> None:
        server = ServerConfig(id="slow-box", name="Slow", mode="ssh", host_name="10.0.0.8")
        config = AppConfig(remote_timeout_seconds=3)

        with patch.object(server_module, "ssh_command", side_effect=subprocess.TimeoutExpired("ssh", 3)):
            with patch.object(server_module, "probe_ssh_reachable", return_value=True) as probe:
                payload = collect_server(server, config)

        probe.assert_called_once()
        self.assertFalse(payload["online"])
        self.assertTrue(payload["reachable"])
        self.assertEqual(payload["error_kind"], "gpu_probe")

    def test_collect_server_marks_remote_gpu_probe_failure_as_reachable(self) -> None:
        server = ServerConfig(id="dual-3060", name="双卡3060", mode="ssh", host_name="172.30.4.172")
        config = AppConfig(remote_timeout_seconds=3)
        result = subprocess.CompletedProcess(
            ["ssh"],
            255,
            "",
            "Failed to initialize NVML: Driver/library version mismatch\n",
        )

        with patch.object(server_module, "ssh_command", return_value=result):
            payload = collect_server(server, config)

        self.assertFalse(payload["online"])
        self.assertTrue(payload["reachable"])
        self.assertFalse(payload["monitor_ok"])
        self.assertEqual(payload["error_kind"], "gpu_probe")
        self.assertIn("Driver/library version mismatch", payload["error"])

    def test_collect_server_marks_transport_failure_as_offline(self) -> None:
        server = ServerConfig(id="offline-box", name="Offline", mode="ssh", host_name="10.0.0.9")
        config = AppConfig(remote_timeout_seconds=3)
        result = subprocess.CompletedProcess(
            ["ssh"],
            255,
            "",
            "ssh: connect to host 10.0.0.9 port 22: Connection refused\n",
        )

        with patch.object(server_module, "ssh_command", return_value=result):
            payload = collect_server(server, config)

        self.assertFalse(payload["online"])
        self.assertFalse(payload["reachable"])
        self.assertFalse(payload["monitor_ok"])
        self.assertEqual(payload["error_kind"], "connection")

    def test_read_local_text_file_marks_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "train.log"
            path.write_text("0123456789abcdef", encoding="utf-8")

            payload = read_local_text_file(str(path), limit_bytes=10)

            self.assertEqual(payload["path"], str(path))
            self.assertEqual(payload["encoding"], "utf-8")
            self.assertTrue(payload["truncated"])
            self.assertEqual(payload["text"], "0123456789")

    def test_read_local_text_file_rejects_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "blob.bin"
            path.write_bytes(b"\x00\x01\x02binary")

            with self.assertRaisesRegex(ValueError, "二进制"):
                read_local_text_file(str(path), limit_bytes=32)

    def test_preview_kind_treats_html_and_svg_as_text(self) -> None:
        self.assertEqual(preview_kind_for_path("/tmp/report.html", "text/html"), "text")
        self.assertEqual(preview_kind_for_path("/tmp/diagram.svg", "image/svg+xml"), "text")
        self.assertEqual(preview_kind_for_path("/tmp/chart.png", "image/png"), "image")

    def test_preview_kind_treats_dotfiles_and_makefile_as_text(self) -> None:
        self.assertEqual(preview_kind_for_path("/repo/.gitignore"), "text")
        self.assertEqual(preview_kind_for_path("/repo/.env"), "text")
        self.assertEqual(preview_kind_for_path("/repo/Makefile"), "text")
        self.assertEqual(preview_kind_for_path("/repo/Dockerfile"), "text")

    def test_cleanup_preview_cache_only_removes_project_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "preview-cache"
            other = Path(tmp_dir) / "other-temp"
            root.mkdir()
            other.mkdir()
            old_dir = root / "old"
            new_dir = root / "new"
            old_dir.mkdir()
            new_dir.mkdir()
            (old_dir / "file.bin").write_bytes(b"x" * 1024)
            (new_dir / "file.bin").write_bytes(b"y" * 2048)
            (other / "keep.txt").write_text("stay", encoding="utf-8")
            old_ts = time.time() - 48 * 3600
            os.utime(old_dir, (old_ts, old_ts))
            with patch.object(server_module, "FILE_PREVIEW_CACHE_DIR", root):
                result = cleanup_preview_cache(max_age_hours=24, max_size_mib=0)
            self.assertEqual(result["removed_count"], 1)
            self.assertFalse(old_dir.exists())
            self.assertTrue(new_dir.exists())
            self.assertTrue((other / "keep.txt").exists())

    def test_download_remote_file_to_local_uses_rsync(self) -> None:
        server = ServerConfig(
            id="gpu-box",
            name="GPU Box",
            mode="ssh",
            host_name="10.0.0.8",
            user="alice",
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            destination = Path(tmp_dir) / "cache"

            def fake_run_command(command: list[str], _timeout: int) -> subprocess.CompletedProcess[str]:
                self.assertEqual(command[0], "rsync")
                self.assertIn("--protect-args", command)
                self.assertEqual(command[-2], "alice@10.0.0.8:/srv/train.log")
                self.assertIn("StrictHostKeyChecking=accept-new", command[command.index("-e") + 1])
                target_dir = Path(str(command[-1]).rstrip("/"))
                target_dir.mkdir(parents=True, exist_ok=True)
                (target_dir / "train.log").write_text("downloaded", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "ok\n", "")

            with patch.object(server_module, "run_command", side_effect=fake_run_command):
                local_path = download_remote_file_to_local(server, "/srv/train.log", destination)

            self.assertEqual(local_path, (destination / "train.log").resolve())

    def test_fetch_file_preview_registers_local_file(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.config = AppConfig(remote_timeout_seconds=3)
        state.servers = [ServerConfig(id="local", name="Local", mode="local")]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "train.log"
            path.write_text("0123456789abcdef", encoding="utf-8")

            payload = TotalControlState.fetch_file_preview(state, "local", str(path), limit_bytes=10)

            self.assertEqual(payload["preview_kind"], "text")
            self.assertEqual(payload["text"], "0123456789")
            self.assertTrue(payload["truncated"])
            self.assertFalse(payload["cached"])
            self.assertTrue(payload["preview_url"].startswith("/api/files/cache/"))
            entry = TotalControlState.file_preview_entry(state, payload["cache_id"])
            self.assertEqual(entry["local_path"], str(path.resolve()))

    def test_fetch_file_preview_downloads_remote_binary_to_cache(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.config = AppConfig(remote_timeout_seconds=3)
        state.servers = [
            ServerConfig(id="gpu-box", name="GPU Box", mode="ssh", host_name="10.0.0.8", user="alice"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            cached = Path(tmp_dir) / "preview.png"
            cached.write_bytes(b"PNG")

            with patch.object(server_module, "download_remote_file_to_local", return_value=cached):
                payload = TotalControlState.fetch_file_preview(state, "gpu-box", "/srv/preview.png")

            self.assertEqual(payload["preview_kind"], "image")
            self.assertTrue(payload["cached"])
            self.assertEqual(payload["local_path"], str(cached.resolve()))
            self.assertTrue(payload["download_url"].endswith("?download=1"))

    def test_parse_remote_marked_json_joins_wrapped_base64_lines(self) -> None:
        output = "\n".join(
            [
                "welcome banner",
                "__TC_FILE_BROWSE_JSON___BEGIN",
                "eyJwYXRoIjogIi9ob21lIiwgImVudHJpZXMiOiBbeyJuYW1lIjogImRldiIsICJpc19kaXIi",
                "OiB0cnVlfSwgeyJuYW1lIjogInRyYWluLmxvZyIsICJpc19kaXIiOiBmYWxzZX1dfQ==",
                "__TC_FILE_BROWSE_JSON___END",
                "motd footer",
            ]
        )

        payload = parse_remote_marked_json(output, "__TC_FILE_BROWSE_JSON__", label="目录读取结果")

        self.assertEqual(payload["path"], "/home")
        self.assertEqual(payload["entries"][0]["name"], "dev")
        self.assertFalse(payload["entries"][1]["is_dir"])

    def test_reorder_job_moves_waiting_items_only(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.jobs = [
            {"id": "job-new", "status": "queued", "queue_rank": 3, "created_at": "2026-05-22T10:02:00"},
            {"id": "job-running", "status": "running", "queue_rank": 0, "created_at": "2026-05-22T10:01:00"},
            {"id": "job-mid", "status": "queued", "queue_rank": 2, "created_at": "2026-05-22T10:01:30"},
            {"id": "job-old", "status": "blocked", "queue_rank": 1, "created_at": "2026-05-22T10:00:00"},
        ]
        state.next_queue_rank = 4
        state.save_jobs = lambda: None

        result = TotalControlState.reorder_job(state, "job-mid", "top")

        waiting = sorted(
            [job for job in state.jobs if job["status"] in {"queued", "blocked"}],
            key=lambda item: item["queue_rank"],
        )
        self.assertEqual([job["id"] for job in waiting], ["job-mid", "job-old", "job-new"])
        self.assertEqual(result["queue_position"], 1)

        with self.assertRaisesRegex(ValueError, "等待中"):
            TotalControlState.reorder_job(state, "job-running", "up")

    def test_stop_server_process_uses_term_then_kill(self) -> None:
        server = ServerConfig(id="local", name="Local", mode="local")
        seen = {}

        def fake_local_runner(script: str, timeout: int) -> subprocess.CompletedProcess[str]:
            seen["script"] = script
            seen["timeout"] = timeout
            return subprocess.CompletedProcess(["bash"], 0, "process stopped after SIGTERM\n", "")

        result = stop_server_process(server, 4321, local_runner=fake_local_runner)

        self.assertTrue(result["ok"])
        self.assertEqual(result["pid"], 4321)
        self.assertIn("signal_targets TERM", seen["script"])
        self.assertIn("signal_targets KILL", seen["script"])
        self.assertIn("tmux list-panes", seen["script"])
        self.assertIn("tmux kill-pane", seen["script"])
        self.assertIn('kill "-$sig" -- "-$pgid"', seen["script"])
        self.assertIn("ps -o stat=", seen["script"])
        self.assertGreaterEqual(seen["timeout"], 10)

    def test_stop_process_rejects_invalid_pid(self) -> None:
        state = object.__new__(TotalControlState)
        state.servers = [ServerConfig(id="local", name="Local", mode="local")]

        with self.assertRaisesRegex(ValueError, "invalid pid"):
            TotalControlState.stop_process(state, "local", "abc")

    def test_start_job_uses_wide_tmux_geometry(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.config = AppConfig()
        state.servers = [ServerConfig(id="local", name="Local", mode="local")]
        state.save_jobs = lambda: None
        job = {
            "id": "job-wide",
            "name": "Wide Job",
            "server_id": "local",
            "candidate_server_ids": [],
            "gpu_index": "none",
            "session": "tc_wide",
            "command": "python train.py --long-argument value",
            "command_display": "python train.py --long-argument value",
            "cwd": "",
            "env_name": "",
            "kind": "command",
            "metadata": {},
        }

        with patch.object(
            server_module,
            "run_command",
            return_value=subprocess.CompletedProcess(["tmux"], 0, "", ""),
        ) as run:
            TotalControlState.start_job(state, job)

        command = run.call_args.args[0]
        self.assertEqual(command[:5], ["tmux", "new-session", "-d", "-s", "tc_wide"])
        self.assertIn("-x", command)
        self.assertIn("-y", command)
        self.assertEqual(command[command.index("-x") + 1], str(server_module.TMUX_DEFAULT_COLUMNS))
        self.assertEqual(command[command.index("-y") + 1], str(server_module.TMUX_DEFAULT_ROWS))

    def test_capture_tmux_resizes_before_capture(self) -> None:
        state = object.__new__(TotalControlState)
        state.config = AppConfig()
        state.servers = [ServerConfig(id="local", name="Local", mode="local")]
        calls: list[list[str]] = []

        def fake_run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[:2] == ["tmux", "capture-pane"]:
                return subprocess.CompletedProcess(command, 0, "wide output\n", "")
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(server_module, "run_command", side_effect=fake_run):
            text = TotalControlState.capture_tmux(state, "local", "tc_wide", lines=120)

        self.assertEqual(text, "wide output\n")
        self.assertEqual(calls[0][:2], ["tmux", "resize-window"])
        self.assertEqual(calls[1][:2], ["tmux", "resize-pane"])
        self.assertEqual(calls[2][:2], ["tmux", "capture-pane"])
        self.assertEqual(calls[0][calls[0].index("-x") + 1], str(server_module.TMUX_DEFAULT_COLUMNS))
        self.assertEqual(calls[1][calls[1].index("-y") + 1], str(server_module.TMUX_DEFAULT_ROWS))
        self.assertIn("-J", calls[2])

    def test_capture_tmux_remote_resizes_before_capture(self) -> None:
        state = object.__new__(TotalControlState)
        state.config = AppConfig(remote_timeout_seconds=3)
        state.servers = [ServerConfig(id="gpu-box", name="GPU Box", mode="ssh", ssh_alias="gpu-box")]

        with patch.object(
            server_module,
            "ssh_command",
            return_value=subprocess.CompletedProcess(["ssh"], 0, "remote wide output\n", ""),
        ) as ssh:
            text = TotalControlState.capture_tmux(state, "gpu-box", "tc_remote", lines=120)

        self.assertEqual(text, "remote wide output\n")
        remote_command = ssh.call_args.args[1]
        self.assertIn("resize-window", remote_command)
        self.assertIn("resize-pane", remote_command)
        self.assertIn(f"-x {server_module.TMUX_DEFAULT_COLUMNS}", remote_command)
        self.assertIn(f"-y {server_module.TMUX_DEFAULT_ROWS}", remote_command)
        self.assertIn("capture-pane -p -J", remote_command)

    def test_create_workspace_builds_starter_graph(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.workspaces = []
        state.save_workspaces = lambda: None

        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "repo",
                "repo_url": "https://gitee.com/example/demo-workspace.git",
                "repo_ref": "main",
                "workspace_dir": "/tmp/demo-workspace",
                "env_name": "lab",
                "setup_command": "pip install -r requirements.txt",
                "run_command": "python train.py",
                "report_command": "python eval.py",
            },
        )

        self.assertEqual(workspace["name"], "demo-workspace")
        self.assertEqual(workspace["source"]["type"], "repo")
        expected_kinds = [
            "source.repo",
            "repo.clone",
            "path.resolve",
            "repo.inspect",
            "dataset.find",
            "env.infer",
            "env.prepare",
            "gpu.allocate",
            "run.command",
            "artifact.collect",
            "eval.report",
        ]
        self.assertEqual([node["kind"] for node in workspace["nodes"]], expected_kinds)
        self.assertEqual(len(workspace["links"]), len(expected_kinds) - 1)

    def test_update_workspace_preserves_id_and_nodes(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.save_workspaces = lambda: None
        state.workspaces = []
        original = TotalControlState.create_workspace(
            state,
            {
                "name": "Idea Workspace",
                "source_type": "idea",
                "idea_text": "做一个自动实验编排平台",
                "run_command": "python main.py",
            },
        )
        state.workspaces = [original]

        updated = TotalControlState.update_workspace(
            state,
            original["id"],
            {
                "name": "Idea Workspace V2",
                "env_name": "agentlab",
                "notes": "need repo search node later",
            },
        )

        self.assertEqual(updated["id"], original["id"])
        self.assertEqual(updated["name"], "Idea Workspace V2")
        self.assertEqual(updated["env"]["name"], "agentlab")
        self.assertEqual(updated["notes"], "need repo search node later")
        self.assertTrue(updated["tools"])
        self.assertEqual(updated["links"], original["links"])
        self.assertEqual(
            [node["id"] for node in updated["nodes"]],
            [node["id"] for node in original["nodes"]],
        )
        self.assertEqual(
            [node["kind"] for node in updated["nodes"]],
            [node["kind"] for node in original["nodes"]],
        )
        env_node = next(node for node in updated["nodes"] if node["kind"] == "env.prepare")
        self.assertEqual(env_node["config"]["env_name"], "agentlab")

    def test_create_workspace_accepts_custom_node_chain(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.workspaces = []
        state.save_workspaces = lambda: None

        workspace = TotalControlState.create_workspace(
            state,
            {
                "name": "Custom Chain",
                "source_type": "idea",
                "idea_text": "做一个节点化工作链",
                "nodes": [
                    {
                        "kind": "source.idea",
                        "title": "需求输入",
                        "handler": {"mode": "human", "name": "你", "handoff": "把问题背景交给分析节点"},
                        "config": {"idea_text": "做一个节点化工作链"},
                    },
                    {
                        "kind": "custom.step",
                        "title": "拆解需求",
                        "handler": {"mode": "agent", "name": "Planner"},
                        "config": {"goal": "把需求拆成节点", "output_expectation": "一条可执行链"},
                    },
                    {
                        "kind": "run.command",
                        "title": "执行验证",
                        "handler": {"mode": "system", "name": "Runner"},
                        "config": {"run_command": "python main.py"},
                    },
                ],
            },
        )

        self.assertEqual([node["kind"] for node in workspace["nodes"]], ["source.idea", "custom.step", "run.command"])
        self.assertEqual(workspace["links"][0]["from"], workspace["nodes"][0]["id"])
        self.assertEqual(workspace["links"][1]["to"], workspace["nodes"][2]["id"])
        self.assertEqual(workspace["nodes"][1]["handler"]["mode"], "agent")
        self.assertEqual(workspace["nodes"][1]["config"]["goal"], "把需求拆成节点")

    def test_update_workspace_without_nodes_keeps_custom_chain(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.workspaces = []
        state.save_workspaces = lambda: None
        original = TotalControlState.create_workspace(
            state,
            {
                "name": "Custom Chain",
                "source_type": "repo",
                "repo_url": "https://github.com/example/demo.git",
                "workspace_dir": "/tmp/demo",
                "nodes": [
                    {"kind": "source.repo", "title": "仓库输入", "config": {"repo_url": "https://github.com/example/demo.git"}},
                    {"kind": "custom.step", "title": "人工阅读", "config": {"goal": "先看 README"}},
                    {"kind": "env.prepare", "title": "准备环境", "config": {"env_name": "demo"}},
                    {"kind": "run.command", "title": "执行", "config": {"run_command": "python train.py"}},
                ],
            },
        )
        state.workspaces = [original]

        updated = TotalControlState.update_workspace(
            state,
            original["id"],
            {
                "env_name": "demo-v2",
                "run_command": "python train.py --dry-run",
            },
        )

        self.assertEqual([node["kind"] for node in updated["nodes"]], [node["kind"] for node in original["nodes"]])
        custom = updated["nodes"][1]
        self.assertEqual(custom["kind"], "custom.step")
        self.assertEqual(custom["config"]["goal"], "先看 README")
        env_node = next(node for node in updated["nodes"] if node["kind"] == "env.prepare")
        run_node = next(node for node in updated["nodes"] if node["kind"] == "run.command")
        self.assertEqual(env_node["config"]["env_name"], "demo-v2")
        self.assertEqual(run_node["config"]["run_command"], "python train.py --dry-run")

    def test_workspace_defaults_include_agents_model_and_brief(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.workspaces = []
        state.jobs = []
        state.save_workspaces = lambda: None

        workspace = TotalControlState.create_workspace(
            state,
            {
                "name": "General Workspace",
                "brief": "做一个聊天 + 工作流项目工作台",
                "references": "https://example.com/doc\n/path/to/local/note.md",
                "source_type": "idea",
            },
        )

        self.assertEqual(workspace["brief"], "做一个聊天 + 工作流项目工作台")
        self.assertEqual(workspace["references"], ["https://example.com/doc", "/path/to/local/note.md"])
        self.assertTrue(workspace["tools"])
        self.assertEqual(workspace["tools"][0]["id"], "workflow.plan")
        self.assertIn("execution.package", [tool["id"] for tool in workspace["tools"]])
        self.assertTrue(workspace["agents"])
        self.assertEqual(workspace["agents"][0]["id"], "planner")
        self.assertIn("watcher", [agent["id"] for agent in workspace["agents"]])
        self.assertIn("reporter", [agent["id"] for agent in workspace["agents"]])
        self.assertIn("chat.write", workspace["agents"][0]["tools"])
        agent_tools = {agent["id"]: set(agent.get("tools") or []) for agent in workspace["agents"]}
        for agent_id in ("planner", "runner", "evaluator", "reporter"):
            self.assertIn("execution.package", agent_tools[agent_id])
        self.assertEqual(workspace["model"]["routing_mode"], "workspace_default")
        self.assertEqual(workspace["chat"], [])
        source_node = next(node for node in workspace["nodes"] if node["kind"] == "source.idea")
        self.assertEqual(source_node["config"]["idea_text"], "做一个聊天 + 工作流项目工作台")

    def test_run_workspace_workflow_builds_dependency_chain(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.workspaces = []
        state.jobs = []
        state.next_queue_rank = 1
        state.save_workspaces = lambda: None
        state.save_jobs = lambda: None
        workspace = TotalControlState.create_workspace(
            state,
            {
                "name": "Workflow Workspace",
                "source_type": "repo",
                "repo_url": "https://github.com/example/demo.git",
                "workspace_dir": "/tmp/demo",
                "setup_command": "pip install -r requirements.txt",
                "run_command": "python train.py",
                "report_command": "python eval.py",
            },
        )
        state.workspaces = [workspace]
        state.jobs = []

        result = TotalControlState.run_workspace_workflow(state, workspace["id"])
        jobs = result["jobs"]

        expected_job_kinds = [
            "repo.clone",
            "path.resolve",
            "repo.inspect",
            "dataset.find",
            "env.infer",
            "env.prepare",
            "gpu.allocate",
            "run.command",
            "artifact.collect",
            "eval.report",
        ]
        self.assertEqual([job["metadata"]["node_kind"] for job in jobs], expected_job_kinds)
        for index, job in enumerate(jobs):
            expected_targets = [] if index == 0 else [jobs[index - 1]["id"]]
            self.assertEqual(job["target_job_ids"], expected_targets)
        run_job = next(job for job in jobs if job["metadata"]["node_kind"] == "run.command")
        run_bundle = run_job["metadata"]["execution_bundle"]
        self.assertEqual(run_bundle["step"]["id"], "run")
        self.assertEqual(run_bundle["step"]["node_kind"], "run.command")
        self.assertIn("command_script", run_bundle)
        self.assertIn("python train.py", run_bundle["command_script"]["text"])
        self.assertEqual(result["execution_package"]["job_count"], len(jobs))
        self.assertEqual(result["execution_package"]["job_ids"], [job["id"] for job in jobs])
        self.assertEqual(result["execution_package"]["package_manifest"]["schema"], "relaygraph.execution_package.v1")
        self.assertIn("python train.py", result["execution_package"]["package_manifest"]["command_script"]["text"])
        run_execution_node = next(node for node in result["workspace"]["execution"]["nodes"] if node["kind"] == "run.command")
        self.assertEqual(run_execution_node["execution_bundle"]["step"]["id"], "run")
        self.assertEqual(run_execution_node["execution_bundle"]["target"]["workspace_dir"], "/tmp/demo")

    def test_pick_server_for_cpu_job_prefers_local_when_available(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.servers = [
            ServerConfig(id="local", name="Local", mode="local"),
            ServerConfig(id="gpu-box", name="GPU Box", mode="ssh"),
        ]
        state.statuses = [
            {"id": "gpu-box", "online": True, "gpus": [{"state": "busy"}], "processes": [{"pid": "1"}]},
            {"id": "local", "online": True, "gpus": [], "processes": []},
        ]

        ok, server_id, reason = TotalControlState.pick_server_for_job(state, {"server_id": "auto", "candidate_server_ids": []})

        self.assertTrue(ok)
        self.assertEqual(server_id, "local")
        self.assertEqual(reason, "")

    def test_monitor_jobs_starts_cpu_queued_job_without_gpu_search(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.jobs = [
            {
                "id": "job-1",
                "status": "queued",
                "gpu_index": "none",
                "target_job_ids": [],
                "error": "",
            }
        ]
        state.statuses = []
        state.save_jobs = lambda: None
        called = []

        def fake_start_job(job: dict[str, Any], allow_busy: bool = False) -> None:
            called.append((job["id"], allow_busy))
            job["status"] = "running"

        def fake_find_gpu(job: dict[str, Any]):  # type: ignore[no-untyped-def]
            raise AssertionError("find_gpu should not be called for cpu jobs")

        state.start_job = fake_start_job  # type: ignore[method-assign]
        state.find_gpu = fake_find_gpu  # type: ignore[method-assign]

        TotalControlState.monitor_jobs(state)

        self.assertEqual(called, [("job-1", True)])
        self.assertEqual(state.jobs[0]["status"], "running")

    def test_append_workspace_chat_persists_messages_and_selected_agent(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.jobs = []
        state.save_workspaces = lambda: None
        state.workspaces = []
        workspace = TotalControlState.create_workspace(
            state,
            {
                "name": "Chat Workspace",
                "brief": "把用户需求整理成节点",
                "source_type": "idea",
            },
        )
        state.workspaces = [workspace]

        result = TotalControlState.append_workspace_chat(
            state,
            workspace["id"],
            {
                "text": "先帮我把这个需求拆一下",
                "agent_id": "planner",
            },
        )

        updated = result["workspace"]
        self.assertEqual(len(updated["chat"]), 2)
        self.assertEqual(updated["chat"][0]["role"], "user")
        self.assertEqual(updated["chat"][0]["agent_id"], "planner")
        self.assertEqual(updated["chat"][1]["role"], "assistant")
        self.assertIn("Planner", updated["chat"][1]["text"])
        self.assertEqual(updated["model"]["chat_agent_id"], "planner")
        self.assertEqual(len(result["messages"]), 2)

    def test_debug_workspace_agent_builds_context_and_allowed_tools(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.jobs = []
        state.save_workspaces = lambda: None
        state.workspaces = []
        workspace = TotalControlState.create_workspace(
            state,
            {
                "name": "Agent Debug Workspace",
                "brief": "从论文和仓库线索里整理出可运行的实验链",
                "source_type": "idea",
                "idea_text": "希望先搜索资料，再准备环境，最后运行评估",
                "workspace_dir": "/tmp/agent-debug",
                "references": ["https://example.com/paper", "https://gitee.com/example/repo"],
            },
        )
        state.workspaces = [workspace]

        result = TotalControlState.debug_workspace_agent(
            state,
            workspace["id"],
            "planner",
            {
                "input": "先帮我看看这个项目应该怎么拆节点",
                "node_kind": "research.search",
            },
        )

        debug = result["debug"]
        self.assertEqual(debug["workspace_id"], workspace["id"])
        self.assertEqual(debug["agent"]["id"], "planner")
        self.assertEqual(debug["context"]["source_type"], "idea")
        self.assertEqual(debug["context"]["workspace_dir"], "/tmp/agent-debug")
        self.assertEqual(debug["focus_node"]["kind"], "research.search")
        self.assertIn("项目目标", debug["prompt_preview"])
        self.assertIn("chat.write", [tool["id"] for tool in debug["allowed_tools"]])
        self.assertTrue(debug["plan"])
        self.assertTrue(any("节点" in step or "检索" in step for step in debug["plan"]))
        self.assertIn("Provider Profile", debug["next_actions"][0])

    def test_run_workspace_node_creates_bound_job_and_updates_runtime(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.config = AppConfig()
        state.servers = [ServerConfig(id="local", name="Local", mode="local")]
        state.jobs = []
        state.workspaces = []
        state.next_queue_rank = 1
        state.save_jobs = lambda: None
        state.save_workspaces = lambda: None

        workspace = TotalControlState.create_workspace(
            state,
            {
                "name": "Run Workspace",
                "source_type": "repo",
                "repo_url": "https://gitee.com/example/demo.git",
                "workspace_dir": "/tmp/demo",
                "env_name": "demo-env",
                "run_command": "python train.py --config base.yaml",
            },
        )
        state.workspaces = [workspace]
        run_node = next(node for node in workspace["nodes"] if node["kind"] == "run.command")

        result = TotalControlState.run_workspace_node(state, workspace["id"], run_node["id"])

        self.assertEqual(result["job"]["metadata"]["workspace_id"], workspace["id"])
        self.assertEqual(result["job"]["metadata"]["node_id"], run_node["id"])
        self.assertEqual(result["job"]["metadata"]["execution_bundle"]["step"]["id"], "run")
        self.assertIn("python train.py --config base.yaml", result["job"]["metadata"]["execution_bundle"]["command_script"]["text"])
        self.assertEqual(result["job"]["command"], "python train.py --config base.yaml")
        runtime_node = next(node for node in result["workspace"]["nodes"] if node["id"] == run_node["id"])
        self.assertEqual(runtime_node["runtime"]["run_count"], 1)
        self.assertEqual(runtime_node["runtime"]["last_job_id"], result["job"]["id"])
        self.assertEqual(runtime_node["runtime"]["last_job_status"], "queued")

    def test_create_workspace_from_template_supports_source_mode_matrix(self) -> None:
        scenarios = [
            {
                "mode": "repo",
                "template_source": "repo",
                "inputs": {
                    "repo_urls": ["https://github.com/example/repo.git"],
                },
            },
            {
                "mode": "paper",
                "template_source": "paper",
                "inputs": {
                    "paper_urls": ["https://arxiv.org/abs/2401.00001"],
                },
            },
            {
                "mode": "idea",
                "template_source": "idea",
                "inputs": {
                    "goal_text": "做一个自动化复现实验工作台",
                },
            },
            {
                "mode": "mixed",
                "template_source": "idea",
                "inputs": {
                    "goal_text": "结合 repo 和论文线索整理实验方案",
                    "repo_urls": ["https://github.com/example/repo.git"],
                    "paper_urls": ["https://arxiv.org/abs/2401.00001"],
                    "references": ["https://example.com/issue/42"],
                },
            },
        ]

        for scenario in scenarios:
            with self.subTest(mode=scenario["mode"]):
                state = make_registry_state()
                template = next(item for item in state.workflow_templates if item["source"]["type"] == scenario["template_source"])
                workspace = TotalControlState.create_workspace(
                    state,
                    {
                        "template_id": template["id"],
                        "inputs": scenario["inputs"],
                    },
                )

                self.assertEqual(workspace["template_id"], template["id"])
                self.assertEqual(workspace["template_snapshot"]["template_id"], template["id"])
                self.assertEqual(workspace["source"]["type"], scenario["mode"])
                self.assertEqual(workspace["inputs"]["source_mode"], scenario["mode"])
                self.assertEqual(workspace["execution"]["counts"]["pending"], len(workspace["nodes"]))
                self.assertEqual(workspace["execution"]["current_node_id"], workspace["nodes"][0]["id"])

                repo_urls = scenario["inputs"].get("repo_urls", [])
                paper_urls = scenario["inputs"].get("paper_urls", [])
                goal_text = scenario["inputs"].get("goal_text", "")
                if repo_urls:
                    self.assertEqual(workspace["source"]["repo_url"], repo_urls[0])
                if paper_urls:
                    self.assertEqual(workspace["source"]["paper_url"], paper_urls[0])
                if goal_text:
                    self.assertEqual(workspace["source"]["idea_text"], goal_text)

    def test_create_workspace_keeps_legacy_payload_when_only_references_exist(self) -> None:
        state = make_registry_state()

        workspace = TotalControlState.create_workspace(
            state,
            {
                "name": "Legacy Workspace",
                "brief": "保留旧版引用输入方式",
                "references": ["https://example.com/doc", "/tmp/local-note.md"],
                "source_type": "idea",
            },
        )

        self.assertEqual(workspace["template_id"], "")
        self.assertEqual(workspace["template_name"], "")
        self.assertEqual(workspace["template_snapshot"], {})
        self.assertEqual(workspace["references"], ["https://example.com/doc", "/tmp/local-note.md"])
        self.assertEqual(workspace["source"]["type"], "idea")
        self.assertTrue(workspace["agents"])
        self.assertTrue(workspace["tools"])

    def test_update_template_workspace_preserves_node_command_configs(self) -> None:
        state = make_registry_state()
        template = state.workflow_templates[0]
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "goal_text": "复现 demo 项目并保留节点配置",
                    "repo_urls": ["https://github.com/example/demo.git"],
                    "references": ["/datasets/imagenet-mini"],
                },
            },
        )
        state.workspaces = [workspace]

        env_node = next(node for node in workspace["nodes"] if node["kind"] == "env.prepare")
        run_node = next(node for node in workspace["nodes"] if node["kind"] == "run.command")
        dataset_node = next(node for node in workspace["nodes"] if node["kind"] == "dataset.find")
        env_node["config"]["setup_command"] = "pip install -e ."
        run_node["config"]["run_command"] = "python train.py --config configs/base.yaml"
        run_node["config"]["schedule"] = "manual"
        run_node["input_mapping"] = {"dataset_profile": "$context.outputs.dataset_profile"}
        run_node["output_key"] = "smoke_run_result"
        dataset_node["config"]["dataset_hints"] = "/datasets/imagenet-mini\n/data/shared"

        updated = TotalControlState.update_workspace(state, workspace["id"], workspace)
        updated_nodes = {node["kind"]: node for node in updated["nodes"]}

        self.assertEqual(updated["template_id"], template["id"])
        self.assertEqual(updated["template_snapshot"]["template_id"], template["id"])
        self.assertEqual(updated["inputs"]["repo_urls"], ["https://github.com/example/demo.git"])
        self.assertEqual(updated_nodes["env.prepare"]["config"]["setup_command"], "pip install -e .")
        self.assertEqual(updated_nodes["run.command"]["config"]["run_command"], "python train.py --config configs/base.yaml")
        self.assertEqual(updated_nodes["run.command"]["config"]["schedule"], "manual")
        self.assertEqual(updated_nodes["run.command"]["input_mapping"], {"dataset_profile": "$context.outputs.dataset_profile"})
        self.assertEqual(updated_nodes["run.command"]["output_key"], "smoke_run_result")
        self.assertIn("/datasets/imagenet-mini", updated_nodes["dataset.find"]["config"]["dataset_hints"])
        run_contract = next(node for node in updated["automation"]["workflow_contract"]["nodes"] if node["kind"] == "run.command")
        self.assertEqual(run_contract["input_mapping"], {"dataset_profile": "$context.outputs.dataset_profile"})
        self.assertEqual(run_contract["output_key"], "smoke_run_result")

        overridden = TotalControlState.update_workspace(
            state,
            workspace["id"],
            {
                "setup_command": "python -m pip install -r requirements.txt",
                "run_command": "python train.py --smoke",
            },
        )
        overridden_nodes = {node["kind"]: node for node in overridden["nodes"]}

        self.assertEqual(overridden_nodes["env.prepare"]["config"]["setup_command"], "python -m pip install -r requirements.txt")
        self.assertEqual(overridden_nodes["run.command"]["config"]["run_command"], "python train.py --smoke")

    def test_update_workflow_template_preserves_io_contract_when_creating_workspace(self) -> None:
        state = make_registry_state()
        template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
        nodes = json.loads(json.dumps(template["nodes"]))
        run_node = next(node for node in nodes if node["kind"] == "run.command")
        run_node["input_mapping"] = {
            "repo_profile": "$context.outputs.repo_profile",
            "dataset_profile": "$context.outputs.dataset_profile",
            "env_ready": "$context.outputs.env_ready",
            "gpu_allocation": "$context.outputs.gpu_allocation",
        }
        run_node["output_key"] = "template_run_result"

        updated_template = TotalControlState.update_workflow_template(
            state,
            template["id"],
            {
                "nodes": nodes,
                "workspace_dir": "/tmp/template-io-contract",
                "env_name": "template-io-contract",
                "setup_command": "pip install -r requirements.txt",
                "run_command": "python train.py --contract",
            },
        )
        updated_template_nodes = {node["kind"]: node for node in updated_template["nodes"]}

        self.assertEqual(updated_template_nodes["run.command"]["input_mapping"], run_node["input_mapping"])
        self.assertEqual(updated_template_nodes["run.command"]["output_key"], "template_run_result")

        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "goal_text": "复现模板 IO 契约",
                    "repo_urls": ["https://github.com/example/io-contract.git"],
                },
            },
        )
        workspace_nodes = {node["kind"]: node for node in workspace["nodes"]}
        snapshot_nodes = {node["kind"]: node for node in workspace["template_snapshot"]["nodes"]}
        automation = workspace["automation"]
        contract_nodes = {
            node["kind"]: node
            for node in automation["workflow_contract"]["nodes"]
        }
        context_steps = {
            step["node_kind"]: step
            for step in automation["execution_context"]["step_results"]
        }
        orchestration_nodes = {
            node["kind"]: node
            for lane in automation["orchestration_contract"]["lanes"]
            for node in lane["nodes"]
        }

        self.assertEqual(snapshot_nodes["run.command"]["input_mapping"], run_node["input_mapping"])
        self.assertEqual(snapshot_nodes["run.command"]["output_key"], "template_run_result")
        self.assertEqual(workspace_nodes["run.command"]["input_mapping"], run_node["input_mapping"])
        self.assertEqual(workspace_nodes["run.command"]["output_key"], "template_run_result")
        self.assertEqual(contract_nodes["run.command"]["input_mapping"], run_node["input_mapping"])
        self.assertEqual(contract_nodes["run.command"]["output_key"], "template_run_result")
        self.assertEqual(contract_nodes["run.command"]["input_status"], "ready")
        self.assertEqual(context_steps["run.command"]["input_mapping"], run_node["input_mapping"])
        self.assertEqual(context_steps["run.command"]["output_key"], "template_run_result")
        self.assertEqual(orchestration_nodes["run.command"]["output_key"], "template_run_result")

        result = TotalControlState.run_workspace_workflow(state, workspace["id"])
        run_job = next(job for job in result["jobs"] if job["metadata"]["node_kind"] == "run.command")
        run_job_contract = run_job["metadata"]["workflow_contract_node"]
        execution_run = next(node for node in result["workspace"]["execution"]["nodes"] if node["kind"] == "run.command")

        self.assertEqual(run_job_contract["input_mapping"], run_node["input_mapping"])
        self.assertEqual(run_job_contract["output_key"], "template_run_result")
        self.assertEqual(execution_run["workflow_contract_node"]["input_mapping"], run_node["input_mapping"])
        self.assertEqual(execution_run["workflow_contract_node"]["output_key"], "template_run_result")

    def test_run_workspace_workflow_from_template_sequences_jobs_and_current_node(self) -> None:
        scenarios = [
            {
                "template_source": "repo",
                "inputs": {
                    "repo_urls": ["https://github.com/example/repo.git"],
                },
            },
            {
                "template_source": "paper",
                "inputs": {
                    "paper_urls": ["https://arxiv.org/abs/2401.00001"],
                },
            },
            {
                "template_source": "idea",
                "inputs": {
                    "goal_text": "先检索资料，再准备环境并运行评估",
                },
            },
        ]

        for scenario in scenarios:
            with self.subTest(template_source=scenario["template_source"]):
                state = make_registry_state()
                template = next(item for item in state.workflow_templates if item["source"]["type"] == scenario["template_source"])
                TotalControlState.update_workflow_template(
                    state,
                    template["id"],
                    {
                        "workspace_dir": f"/tmp/{scenario['template_source']}-workspace",
                        "env_name": f"{scenario['template_source']}-env",
                        "python_version": "3.11",
                        "setup_command": "python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt",
                        "run_command": "python train.py --smoke",
                        "report_command": "python eval.py --summary",
                    },
                )
                updated_template = state.workflow_template_by_id(template["id"])
                self.assertIsNotNone(updated_template)

                workspace = TotalControlState.create_workspace(
                    state,
                    {
                        "template_id": template["id"],
                        "inputs": scenario["inputs"],
                    },
                )
                state.workspaces = [workspace]

                result = TotalControlState.run_workspace_workflow(state, workspace["id"])
                jobs = result["jobs"]
                executable_nodes = [
                    node
                    for node in workspace["nodes"]
                    if node["kind"] in server_module.WORKSPACE_EXECUTABLE_NODE_KINDS
                ]

                self.assertEqual([job["metadata"]["node_kind"] for job in jobs], [node["kind"] for node in executable_nodes])
                self.assertEqual(result["workspace"]["execution"]["current_node_id"], executable_nodes[0]["id"])
                self.assertEqual(
                    result["workspace"]["execution"]["current_agent_id"],
                    str(executable_nodes[0].get("handler", {}).get("agent_id") or ""),
                )
                self.assertEqual(result["workspace"]["execution"]["counts"]["queued"], len(executable_nodes))
                self.assertEqual(
                    result["workspace"]["execution"]["counts"]["pending"],
                    len(workspace["nodes"]) - len(executable_nodes),
                )

                for index, job in enumerate(jobs):
                    expected_targets = [] if index == 0 else [jobs[index - 1]["id"]]
                    self.assertEqual(job["target_job_ids"], expected_targets)
                    self.assertIn("resource_plan", job["metadata"])
                    self.assertIn("artifact_plan", job["metadata"])
                    self.assertIn("workflow_contract_node", job["metadata"])
                    contract = job["metadata"]["workflow_contract_node"]
                    self.assertEqual(contract["node_kind"], executable_nodes[index]["kind"])
                    self.assertIn("input_mapping", contract)
                    self.assertIn("output_key", contract)
                    self.assertIn("context", contract)
                    self.assertEqual(contract["context"]["outputs_key"], "$context.outputs")
                    if executable_nodes[index]["kind"] == "run.command":
                        self.assertEqual(contract["output_key"], "run_result")
                        self.assertIn("gpu_allocation", contract["input_mapping"])
                        self.assertTrue(any(tool["id"] == "job.run" for tool in contract["tools"]))
                    if executable_nodes[index]["kind"] == "repo.inspect":
                        self.assertIn("suggest_run:", job["command"])
                    if executable_nodes[index]["kind"] in {"repo.inspect", "env.prepare", "run.command", "eval.report"}:
                        self.assertEqual(job["metadata"]["resource_plan"]["cwd"], job["cwd"])
                    elif executable_nodes[index]["kind"] != "repo.clone":
                        self.assertEqual(job["cwd"], "")
                    if index > 0:
                        self.assertEqual(job["metadata"]["workflow_prev_job_id"], jobs[index - 1]["id"])

                execution_nodes = {item["id"]: item for item in result["workspace"]["execution"]["nodes"]}
                for node in executable_nodes:
                    node_state = execution_nodes[node["id"]]
                    self.assertIn("workflow_contract_node", node_state)
                    self.assertEqual(node_state["workflow_contract_node"]["node_kind"], node["kind"])
                    self.assertIn("input_mapping", node_state["workflow_contract_node"])
                    self.assertIn("output_key", node_state["workflow_contract_node"])
                    self.assertEqual(node_state["workflow_contract_node"]["context"]["previous_key"], "$prev.output")
                    self.assertGreaterEqual(len(node_state["trace"]), 2)
                    self.assertTrue(any(item["label"] == "已提交队列" for item in node_state["trace"]))
                    self.assertIn("server_id", node_state["resources"])
                    self.assertGreaterEqual(len(node_state["artifacts"]), 1)
                artifact_state = next(item for item in execution_nodes.values() if item["kind"] == "artifact.collect")
                self.assertTrue(any(item["label"] == "产物路径" for item in artifact_state["artifacts"]))

    def test_update_agent_definition_renames_template_bindings(self) -> None:
        state = make_registry_state()
        target_agent_id = "repo-scout"
        template = state.workflow_templates[0]
        template["model"] = {
            **(template.get("model") if isinstance(template.get("model"), dict) else {}),
            "chat_agent_id": target_agent_id,
        }
        self.assertTrue(
            any(
                str((node.get("handler") or {}).get("agent_id") or "") == target_agent_id
                for template in state.workflow_templates
                for node in (template.get("nodes") if isinstance(template.get("nodes"), list) else [])
                if isinstance(node, dict)
            )
        )

        updated = TotalControlState.update_agent_definition(
            state,
            target_agent_id,
            {
                "id": "repo-scout-v2",
                "name": "Repo Scout V2",
            },
        )

        self.assertEqual(updated["id"], "repo-scout-v2")
        self.assertTrue(
            any(
                str((node.get("handler") or {}).get("agent_id") or "") == "repo-scout-v2"
                and str((node.get("handler") or {}).get("name") or "") == "Repo Scout V2"
                for template in state.workflow_templates
                for node in (template.get("nodes") if isinstance(template.get("nodes"), list) else [])
                if isinstance(node, dict)
            )
        )
        self.assertFalse(
            any(
                str((node.get("handler") or {}).get("agent_id") or "") == target_agent_id
                for template in state.workflow_templates
                for node in (template.get("nodes") if isinstance(template.get("nodes"), list) else [])
                if isinstance(node, dict)
            )
        )
        self.assertTrue(
            any(
                str((template.get("model") or {}).get("chat_agent_id") or "") == "repo-scout-v2"
                for template in state.workflow_templates
            )
        )

    def test_update_tool_definition_renames_agent_allowlists(self) -> None:
        state = make_registry_state()
        self.assertTrue(any("chat.write" in agent.get("tools", []) for agent in state.agent_definitions))

        updated = TotalControlState.update_tool_definition(
            state,
            "chat.write",
            {
                "id": "chat.compose",
                "label": "Chat Compose",
            },
        )

        self.assertEqual(updated["id"], "chat.compose")
        self.assertFalse(any("chat.write" in agent.get("tools", []) for agent in state.agent_definitions))
        self.assertTrue(any("chat.compose" in agent.get("tools", []) for agent in state.agent_definitions))

    def test_status_payload_includes_global_workflow_registries(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.config = AppConfig(poll_interval_seconds=7)
        state.config_path = Path("/tmp/test-config.toml")
        state.servers = [ServerConfig(id="local", name="Local")]
        state.last_refresh = time.time() - 1.0
        state.last_refreshed_at = "2026-06-06T10:00:00"
        state.statuses = [{"id": "local", "online": True}]
        state.jobs = []
        state.workspaces = []
        state.tool_definitions = server_module.workspace_default_tools()
        state.agent_definitions = server_module.workspace_default_agents()
        state.workflow_templates = server_module.build_default_workflow_templates(
            state.agent_definitions,
            state.tool_definitions,
        )

        payload = TotalControlState.status_payload(state)

        self.assertTrue(payload["workflow_templates"])
        self.assertTrue(payload["agent_definitions"])
        self.assertTrue(payload["tool_definitions"])
        self.assertEqual(payload["workflow_templates"][0]["agent_count"], len(payload["workflow_templates"][0]["agent_ids"]))

    def test_create_workspace_from_template_copies_snapshot_and_inputs(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.jobs = []
        state.workspaces = []
        state.save_workspaces = lambda: None
        state.tool_definitions = server_module.workspace_default_tools()
        state.agent_definitions = server_module.workspace_default_agents()
        state.workflow_templates = server_module.build_default_workflow_templates(
            state.agent_definitions,
            state.tool_definitions,
        )

        template = state.workflow_templates[0]
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "goal_text": "复现这个 repo 对应的论文实验，并整理执行报告",
                    "repo_urls": ["https://github.com/example/repo.git"],
                    "paper_urls": ["https://arxiv.org/abs/2401.00001"],
                    "references": ["/tmp/local-note.md"],
                    "context_blocks": ["GPU 预算 1 张 4090", "优先用 conda 环境"],
                },
            },
        )

        self.assertEqual(workspace["template_id"], template["id"])
        self.assertEqual(workspace["template_name"], template["name"])
        self.assertEqual(workspace["inputs"]["goal_text"], "复现这个 repo 对应的论文实验，并整理执行报告")
        self.assertEqual(workspace["inputs"]["repo_urls"], ["https://github.com/example/repo.git"])
        self.assertEqual(workspace["inputs"]["paper_urls"], ["https://arxiv.org/abs/2401.00001"])
        self.assertEqual(workspace["inputs"]["context_blocks"], ["GPU 预算 1 张 4090", "优先用 conda 环境"])
        self.assertEqual(workspace["source"]["type"], "mixed")
        self.assertTrue(workspace["template_snapshot"]["nodes"])
        self.assertTrue(workspace["template_snapshot"]["agents"])
        self.assertTrue(workspace["template_snapshot"]["tools"])

    def test_workspace_public_payload_includes_automation_readiness_checks(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": state.workflow_templates[0]["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                },
            },
        )
        state.workspaces = [workspace]

        payload = TotalControlState.workspace_public_payload(state, workspace)
        automation = payload["automation"]
        required_cockpit_sections = {
            "checks",
            "evidence",
            "evidence_backfill",
            "run_plan",
            "workflow_contract",
            "orchestration_contract",
            "execution_context",
            "reproduction_manifest",
            "agent_topology",
            "resource_orchestration",
            "execution_readiness",
            "playbook",
            "preflight",
            "report",
            "advance",
            "next_action",
        }
        checks = {item["id"]: item for item in automation["checks"]}

        self.assertIn("automation", payload)
        self.assertTrue(required_cockpit_sections.issubset(automation.keys()))
        self.assertIsInstance(automation["evidence"], list)
        self.assertIsInstance(automation["evidence_backfill"]["items"], list)
        self.assertIsInstance(automation["run_plan"]["nodes"], list)
        self.assertIsInstance(automation["workflow_contract"]["nodes"], list)
        self.assertIsInstance(automation["orchestration_contract"]["lanes"], list)
        self.assertIsInstance(automation["execution_context"]["step_results"], list)
        self.assertIsInstance(automation["execution_context"]["outputs"], list)
        self.assertIsInstance(automation["reproduction_manifest"]["items"], list)
        self.assertIsInstance(automation["agent_topology"]["stages"], list)
        self.assertIsInstance(automation["resource_orchestration"]["items"], list)
        self.assertIsInstance(automation["execution_readiness"]["steps"], list)
        self.assertIsInstance(automation["playbook"]["steps"], list)
        self.assertIsInstance(automation["preflight"]["items"], list)
        self.assertIsInstance(automation["report"]["highlights"], list)
        self.assertEqual(checks["source"]["status"], "ready")
        self.assertEqual(checks["starter_chain"]["status"], "ready")
        self.assertEqual(checks["run"]["status"], "blocked")
        self.assertIn(checks["run"], automation["missing"])
        self.assertEqual(automation["run_plan"]["status"], "blocked")
        self.assertTrue(any(item["node_kind"] == "run.command" for item in automation["run_plan"]["blocking"]))
        self.assertGreaterEqual(automation["run_plan"]["node_count"], 1)
        contract = automation["workflow_contract"]
        contract_nodes = {item["kind"]: item for item in contract["nodes"]}
        self.assertEqual(contract["context"]["outputs_key"], "$context.outputs")
        self.assertIn("run.command", contract_nodes)
        self.assertEqual(contract_nodes["run.command"]["output_key"], "run_result")
        self.assertEqual(contract_nodes["run.command"]["context"]["previous_key"], "$prev.output")
        self.assertIn("gpu_allocation", contract_nodes["run.command"]["input_mapping"])
        self.assertTrue(any(tool["id"] == "job.run" for tool in contract_nodes["run.command"]["tools"]))
        orchestration = automation["orchestration_contract"]
        orchestration_nodes = [
            node
            for lane in orchestration["lanes"]
            for node in lane["nodes"]
        ]
        self.assertIn("agent", orchestration["layers"])
        self.assertIn("tool", orchestration["layers"])
        self.assertIn("ai", orchestration["layers"])
        self.assertGreaterEqual(orchestration["lane_count"], 1)
        self.assertTrue(any(lane["id"] == "run" for lane in orchestration["lanes"]))
        self.assertTrue(any(node["kind"] == "run.command" and node["output_key"] == "run_result" for node in orchestration_nodes))
        self.assertTrue(any("Agent" in node["agent"]["name"] or node["agent"]["id"] for node in orchestration_nodes))
        context_bus = automation["execution_context"]
        context_steps = {item["node_kind"]: item for item in context_bus["step_results"]}
        self.assertEqual(context_bus["context"]["outputs_key"], "$context.outputs")
        self.assertIn("run.command", context_steps)
        self.assertEqual(context_steps["run.command"]["output_key"], "run_result")
        self.assertIn("gpu_allocation", context_steps["run.command"]["input_mapping"])
        self.assertTrue(any(item["key"] == "run_result" for item in context_bus["outputs"]))
        manifest = automation["reproduction_manifest"]
        manifest_items = {item["id"]: item for item in manifest["items"]}
        delivery_contract = manifest["delivery_contract"]
        self.assertIn("run", manifest_items)
        self.assertIn("environment", manifest_items)
        self.assertIn("gpu", manifest_items)
        self.assertIn("artifacts", manifest_items)
        self.assertEqual(delivery_contract["mode"], "reproduce")
        self.assertEqual(delivery_contract["label"], "自动复现")
        self.assertIn("acceptance_criteria", delivery_contract)
        self.assertTrue(any("可复现命令" in item for item in delivery_contract["acceptance_criteria"]))
        self.assertEqual(manifest["commands"]["run_command"], "")
        self.assertEqual(manifest_items["run"]["status"], "blocked")
        self.assertEqual(manifest_items["run"]["node_kind"], "run.command")
        self.assertTrue(manifest_items["run"]["node_id"])
        self.assertEqual(manifest["next_action"]["node_id"], manifest_items["checkout"]["node_id"])
        self.assertEqual(manifest["next_action"]["id"], "checkout")
        bundle = manifest["execution_bundle"]
        bundle_steps = {item["id"]: item for item in bundle["steps"]}
        self.assertEqual(bundle["status"], "blocked")
        self.assertFalse(bundle["ready_to_execute"])
        self.assertEqual(bundle["target"]["mode"], "reproduce")
        self.assertEqual(bundle["delivery_contract"]["mode"], "reproduce")
        self.assertEqual(bundle["next_action"]["action"], "select-execution-node")
        self.assertEqual(bundle["next_action"]["node_id"], manifest_items["checkout"]["node_id"])
        package = bundle["package_manifest"]
        self.assertEqual(package["schema"], "relaygraph.execution_package.v1")
        self.assertFalse(package["ready_to_execute"])
        self.assertEqual(package["target"]["mode"], "reproduce")
        self.assertTrue(any(item["field"] == "run_command" for item in package["missing"]))
        self.assertEqual(bundle["command_script"]["shell"], "bash")
        self.assertFalse(bundle["command_script"]["ready"])
        self.assertIn("run_command", bundle["command_script"]["text"])
        self.assertTrue(any(item["field"] == "run_command" for item in bundle["command_script"]["blocked"]))
        self.assertIn("run", bundle_steps)
        self.assertEqual(bundle_steps["run"]["status"], "blocked")
        self.assertEqual(bundle_steps["run"]["node_id"], manifest_items["run"]["node_id"])
        self.assertTrue(any(item["field"] == "run_command" for item in bundle["missing"]))
        run_missing = next(item for item in bundle["missing"] if item["field"] == "run_command")
        self.assertEqual(run_missing["node_kind"], "run.command")
        self.assertEqual(run_missing["node_id"], manifest_items["run"]["node_id"])
        self.assertEqual(run_missing["fix_action"]["action"], "select-execution-node")
        self.assertEqual(run_missing["fix_action"]["node_id"], manifest_items["run"]["node_id"])
        self.assertEqual(run_missing["fix_action"]["target_id"], "workspaceExecutionDetail")
        self.assertEqual(run_missing["fix_action"]["tab"], "home")
        self.assertEqual(automation["advance"]["action"], "discover")
        self.assertIn("发现链证据", automation["advance"]["reason"])
        topology = automation["agent_topology"]
        self.assertEqual(topology["layers"]["agent"]["assigned_count"], topology["agent_count"])
        self.assertGreaterEqual(topology["stage_count"], 4)
        self.assertTrue(any(stage["id"] == "discover" for stage in topology["stages"]))
        self.assertTrue(any(tool["id"] == "dataset.find" for stage in topology["stages"] for tool in stage["tools"]))
        self.assertTrue(any(gap["type"] == "model_profile" for gap in topology["gaps"]))
        resources = automation["resource_orchestration"]
        self.assertEqual(resources["status"], "blocked")
        self.assertEqual(len(resources["items"]), 6)
        self.assertEqual(resources["next_action"]["id"], "paths")
        self.assertTrue(any(item["id"] == "run" and item["status"] == "blocked" for item in resources["items"]))
        readiness = automation["execution_readiness"]
        readiness_steps = {item["id"]: item for item in readiness["steps"]}
        self.assertEqual(readiness["status"], "blocked")
        self.assertEqual(readiness["gate"]["status"], "blocked")
        self.assertEqual(readiness_steps["hard_gate"]["status"], "blocked")
        self.assertEqual(readiness_steps["full_run"]["status"], "blocked")
        self.assertEqual(readiness_steps["resource_binding"]["status"], "blocked")
        self.assertEqual(readiness["force_run"]["status"], "blocked")
        self.assertTrue(any(item["node_kind"] == "run.command" for item in readiness["blockers"]))
        run_blocker = next(item for item in readiness["blockers"] if item["node_kind"] == "run.command")
        self.assertEqual(run_blocker["node_id"], manifest_items["run"]["node_id"])
        self.assertEqual(run_blocker["field"], "run_command")
        self.assertIn("fix_action", run_blocker)
        self.assertTrue(any(item.get("node_id") == manifest_items["run"]["node_id"] for item in readiness["gate"]["blockers"]))
        self.assertTrue(any(item.get("field") == "run_command" for item in readiness["force_run"]["blockers"]))
        playbook = automation["playbook"]
        self.assertEqual(playbook["current_step_id"], "discover")
        self.assertTrue(any(step["id"] == "execute" and step["button_action"] in {"advance-workspace-automation", "run-selected-workspace"} for step in playbook["steps"]))
        self.assertEqual(playbook["current_action"]["action"], "run-workspace-discovery")
        preflight = automation["preflight"]
        preflight_items = {item["id"]: item for item in preflight["items"]}
        self.assertEqual(len(preflight_items), 8)
        self.assertEqual(preflight["status"], "blocked")
        self.assertIn("launcher", preflight_items)
        self.assertIn("workflow_chain", preflight_items)
        self.assertIn("data_paths", preflight_items)
        self.assertIn("environment", preflight_items)
        self.assertIn("scheduler", preflight_items)
        self.assertIn("agent_tool_ai", preflight_items)
        self.assertIn("execution_package", preflight_items)
        self.assertIn("run_records", preflight_items)
        self.assertEqual(preflight_items["execution_package"]["status"], "blocked")
        self.assertTrue(preflight_items["execution_package"]["missing"])
        self.assertEqual(preflight_items["agent_tool_ai"]["layer"], "agent_tool_ai")
        self.assertEqual(preflight_items["workflow_chain"]["action_button"]["action"], "switch-workspace-tab")
        self.assertGreater(automation["score"], 0)
        self.assertLess(automation["score"], 100)

    def test_workspace_automation_readiness_becomes_ready_when_chain_inputs_are_complete(self) -> None:
        state = make_registry_state()
        state.statuses = [
            {
                "id": "local",
                "online": True,
                "gpus": [
                    {
                        "index": 0,
                        "state": "idle",
                        "memory_free_mib": 24576,
                    }
                ],
            }
        ]
        template = state.workflow_templates[0]
        TotalControlState.update_workflow_template(
            state,
            template["id"],
            {
                "workspace_dir": "/tmp/relaygraph-ready",
                "env_name": "relaygraph-ready",
                "setup_command": "pip install -r requirements.txt",
                "run_command": "python train.py --smoke",
                "report_command": "python eval.py --summary",
            },
        )
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                    "references": ["/datasets/imagenet-mini"],
                },
            },
        )
        state.workspaces = [workspace]

        payload = TotalControlState.workspace_public_payload(state, workspace)
        automation = payload["automation"]
        checks = {item["id"]: item for item in automation["checks"]}

        self.assertEqual(automation["status"], "ready")
        self.assertEqual(automation["score"], 100)
        self.assertFalse(automation["missing"])
        self.assertEqual(automation["run_plan"]["status"], "ready")
        self.assertTrue(automation["run_plan"]["nodes"])
        self.assertEqual(automation["run_plan"]["nodes"][0]["kind"], "repo.clone")
        self.assertTrue(any(item["phase"] == "run" for item in automation["run_plan"]["nodes"]))
        contract = automation["workflow_contract"]
        self.assertEqual(contract["status"], "ready")
        self.assertEqual(contract["mapped_count"], contract["node_count"])
        self.assertEqual(contract["input_gap_count"], 0)
        self.assertTrue(any(item["kind"] == "dataset.find" and item["output_key"] == "dataset_profile" for item in contract["nodes"]))
        self.assertTrue(any(item["kind"] == "artifact.collect" and item["next_node_title"] for item in contract["nodes"]))
        orchestration = automation["orchestration_contract"]
        orchestration_nodes = [
            node
            for lane in orchestration["lanes"]
            for node in lane["nodes"]
        ]
        self.assertGreaterEqual(orchestration["lane_count"], 4)
        self.assertEqual(orchestration["blocked_node_count"], 0)
        self.assertTrue(any(node["kind"] == "run.command" and node["input_count"] >= 1 for node in orchestration_nodes))
        self.assertTrue(any(node["kind"] == "run.command" and any(tool["id"] == "job.run" for tool in node["tools"]) for node in orchestration_nodes))
        self.assertEqual(automation["advance"]["action"], "discover")
        topology = automation["agent_topology"]
        self.assertGreaterEqual(topology["required_tool_count"], 8)
        self.assertEqual(topology["layers"]["tool"]["status"], "ready")
        self.assertTrue(any(stage["id"] == "run" and any(agent["id"] == "runner" for agent in stage["agents"]) for stage in topology["stages"]))
        resources = automation["resource_orchestration"]
        self.assertEqual(resources["status"], "ready")
        self.assertEqual(resources["resource_candidates"]["recommended_server_id"], "local")
        self.assertEqual(resources["resource_candidates"]["recommended_gpu_index"], "0")
        scheduler = resources["scheduler"]
        self.assertEqual(scheduler["status"], "ready")
        self.assertEqual(scheduler["selected"]["server_id"], "local")
        self.assertEqual(scheduler["selected"]["gpu_index"], "0")
        self.assertTrue(scheduler["candidates"])
        self.assertTrue(any("显存空闲" in reason for reason in scheduler["selected"]["reasons"]))
        self.assertTrue(any(item["id"] == "gpu" and item["status"] == "ready" for item in resources["items"]))
        self.assertTrue(any(item["id"] == "run" and "python train.py --smoke" in item["value"] for item in resources["items"]))
        dataset_plan = automation["dataset_discovery"]
        self.assertEqual(dataset_plan["status"], "ready")
        self.assertIn("/datasets/imagenet-mini", dataset_plan["local_roots"])
        self.assertTrue(dataset_plan["queries"])
        manifest = automation["reproduction_manifest"]
        self.assertEqual(manifest["status"], "ready")
        self.assertTrue(manifest["ready_to_run"])
        self.assertEqual(manifest["commands"]["run_command"], "python train.py --smoke")
        self.assertEqual(manifest["dataset_discovery"]["local_roots"], dataset_plan["local_roots"])
        self.assertEqual(manifest["delivery_contract"]["status"], "ready")
        self.assertTrue(any("python train.py --smoke" in item for item in manifest["delivery_contract"]["acceptance_criteria"]))
        bundle = manifest["execution_bundle"]
        bundle_steps = {item["id"]: item for item in bundle["steps"]}
        self.assertEqual(bundle["status"], "ready")
        self.assertTrue(bundle["ready_to_execute"])
        self.assertFalse(bundle["missing"])
        self.assertEqual(bundle["delivery_contract"]["status"], "ready")
        self.assertEqual(bundle["next_action"]["action"], "run-selected-workspace")
        self.assertEqual(bundle["next_action"]["label"], "提交执行包")
        self.assertEqual(bundle["target"]["server_id"], "local")
        self.assertEqual(bundle["target"]["gpu_index"], "0")
        self.assertEqual(bundle["target"]["env_name"], "relaygraph-ready")
        self.assertEqual(bundle_steps["run"]["command"], "python train.py --smoke")
        self.assertEqual(bundle_steps["run"]["cwd"], "/tmp/relaygraph-ready")
        self.assertEqual(bundle_steps["run"]["env"]["CUDA_VISIBLE_DEVICES"], "0")
        script = bundle["command_script"]
        self.assertEqual(script["shell"], "bash")
        self.assertEqual(script["status"], "ready")
        self.assertTrue(script["ready"])
        self.assertFalse(script["blocked"])
        self.assertIn("cd /tmp/relaygraph-ready", script["text"])
        self.assertIn("pip install -r requirements.txt", script["text"])
        self.assertIn("python train.py --smoke", script["text"])
        self.assertIn("python eval.py --summary", script["text"])
        self.assertIn("CUDA_VISIBLE_DEVICES=0", script["text"])
        self.assertIn("CONDA_DEFAULT_ENV=relaygraph-ready", script["text"])
        package = bundle["package_manifest"]
        self.assertEqual(package["schema"], "relaygraph.execution_package.v1")
        self.assertTrue(package["ready_to_execute"])
        self.assertEqual(package["workspace"]["id"], workspace["id"])
        self.assertEqual(package["target"]["server_id"], "local")
        self.assertEqual(package["scheduler"]["selected"]["gpu_index"], "0")
        self.assertIn("python train.py --smoke", package["command_script"]["text"])
        self.assertEqual(package["commands"]["run_command"], "python train.py --smoke")
        self.assertEqual(package["paths"]["workspace_dir"], "/tmp/relaygraph-ready")
        self.assertEqual(package["dataset_discovery"]["local_roots"], dataset_plan["local_roots"])
        self.assertFalse(package["missing"])
        backfill_fields = {
            (item["node_kind"], item["field"])
            for item in automation["evidence_backfill"]["items"]
            if item["status"] in {"ready", "done"}
        }
        self.assertIn(("gpu.allocate", "gpu_index"), backfill_fields)
        self.assertIn(("run.command", "gpu_index"), backfill_fields)
        self.assertTrue(any(item["id"] == "environment" and item["status"] == "ready" for item in manifest["items"]))
        self.assertTrue(any(item["id"] == "artifacts" and item["status"] == "ready" for item in manifest["items"]))
        self.assertTrue(all(item["node_id"] for item in manifest["items"] if item["id"] != "source"))
        readiness = automation["execution_readiness"]
        readiness_steps = {item["id"]: item for item in readiness["steps"]}
        self.assertEqual(readiness["gate"]["status"], "ready")
        self.assertEqual(readiness["next_action"]["action"], "discover")
        self.assertEqual(readiness_steps["safe_discovery"]["status"], "ready")
        self.assertEqual(readiness_steps["full_run"]["status"], "ready")
        self.assertEqual(readiness_steps["resource_binding"]["status"], "ready")
        self.assertEqual(readiness["job_state"]["full_run_node_count"], automation["run_plan"]["node_count"])
        playbook = automation["playbook"]
        self.assertEqual(playbook["current_step_id"], "discover")
        self.assertTrue(any(step["id"] == "execute" and step["button_action"] == "run-selected-workspace" for step in playbook["steps"]))
        self.assertTrue(any(step["id"] == "schedule" and step["metrics"]["ready_count"] >= 1 for step in playbook["steps"]))
        preflight = automation["preflight"]
        preflight_items = {item["id"]: item for item in preflight["items"]}
        self.assertEqual(preflight["status"], "warning")
        self.assertEqual(preflight_items["scheduler"]["status"], "ready")
        self.assertEqual(preflight_items["execution_package"]["status"], "ready")
        self.assertTrue(preflight_items["execution_package"]["metrics"]["ready_to_execute"])
        self.assertEqual(preflight_items["execution_package"]["action_button"]["action"], "run-selected-workspace")
        self.assertEqual(preflight_items["run_records"]["missing"], ["还没有运行记录"])
        self.assertEqual(checks["gpu"]["status"], "ready")
        self.assertEqual(checks["run"]["status"], "ready")
        self.assertEqual(checks["artifact"]["status"], "ready")

    def test_workspace_workflow_contract_blocks_explicit_broken_input_mapping(self) -> None:
        state = make_registry_state()
        template = state.workflow_templates[0]
        TotalControlState.update_workflow_template(
            state,
            template["id"],
            {
                "workspace_dir": "/tmp/relaygraph-broken-input",
                "env_name": "relaygraph-broken-input",
                "setup_command": "pip install -r requirements.txt",
                "run_command": "python train.py --smoke",
            },
        )
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {"repo_urls": ["https://github.com/example/demo.git"]},
            },
        )
        run_node = next(node for node in workspace["nodes"] if node["kind"] == "run.command")
        run_node["input_mapping"] = {
            "dataset_profile": "$context.outputs.missing_dataset_profile",
        }
        state.workspaces = [workspace]

        payload = TotalControlState.workspace_public_payload(state, workspace)
        automation = payload["automation"]
        contract = automation["workflow_contract"]
        run_contract = next(node for node in contract["nodes"] if node["kind"] == "run.command")

        self.assertEqual(contract["status"], "blocked")
        self.assertEqual(run_contract["input_status"], "blocked")
        self.assertEqual(run_contract["input_gap_count"], 1)
        self.assertEqual(run_contract["missing_inputs"][0]["upstream_output_key"], "missing_dataset_profile")
        context_bus = automation["execution_context"]
        run_step = next(step for step in context_bus["step_results"] if step["node_kind"] == "run.command")
        self.assertEqual(run_step["input_status"], "blocked")
        self.assertTrue(any(item["status"] == "blocked" for item in run_step["resolved_inputs"]))
        orchestration_nodes = [
            node
            for lane in automation["orchestration_contract"]["lanes"]
            for node in lane["nodes"]
        ]
        orchestration_run = next(node for node in orchestration_nodes if node["kind"] == "run.command")
        self.assertEqual(orchestration_run["input_gap_count"], 1)
        self.assertTrue(any(gap["type"] == "input_mapping" for gap in orchestration_run["gaps"]))

    def test_workspace_delivery_contract_detects_deploy_goal(self) -> None:
        state = make_registry_state()
        template = state.workflow_templates[0]
        TotalControlState.update_workflow_template(
            state,
            template["id"],
            {
                "workspace_dir": "/srv/relaygraph-api",
                "env_name": "relaygraph-api",
                "setup_command": "pip install -r requirements.txt",
                "run_command": "uvicorn app:app --host 0.0.0.0 --port 8000",
            },
        )
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "goal_text": "部署这个 repo 为 API 服务，并提供 /health smoke test",
                    "repo_urls": ["https://github.com/example/api.git"],
                    "context_blocks": ["端口 8000 需要健康检查"],
                },
            },
        )
        state.workspaces = [workspace]

        payload = TotalControlState.workspace_public_payload(state, workspace)
        manifest = payload["automation"]["reproduction_manifest"]
        contract = manifest["delivery_contract"]
        deployment_plan = manifest["deployment_plan"]

        self.assertEqual(contract["mode"], "deploy")
        self.assertEqual(contract["label"], "自动部署")
        self.assertEqual(contract["status"], "ready")
        self.assertTrue(any("端口" in item or "API" in item for item in contract["acceptance_criteria"]))
        self.assertTrue(any("健康检查" in item or "health" in item for item in contract["acceptance_criteria"]))
        self.assertTrue(any("uvicorn app:app" in item for item in contract["acceptance_criteria"]))
        self.assertTrue(deployment_plan["relevant"])
        self.assertEqual(deployment_plan["schema"], "relaygraph.deployment_plan.v1")
        self.assertEqual(deployment_plan["status"], "ready")
        self.assertEqual(deployment_plan["service_kind"], "asgi")
        self.assertEqual(deployment_plan["port"], "8000")
        self.assertEqual(deployment_plan["health_path"], "/health")
        self.assertEqual(deployment_plan["health_url"], "http://127.0.0.1:8000/health")
        self.assertEqual(deployment_plan["smoke_test_command"], "curl -fsS http://127.0.0.1:8000/health")
        self.assertTrue(any(":8000" in item for item in deployment_plan["observe_commands"]))
        self.assertIn("uvicorn app:app", deployment_plan["stop_command"])
        self.assertEqual(deployment_plan["next_action"]["action"], "run-selected-workspace")
        self.assertEqual(manifest["execution_bundle"]["delivery_contract"]["mode"], "deploy")
        self.assertEqual(manifest["execution_bundle"]["deployment_plan"]["port"], "8000")
        self.assertEqual(manifest["execution_bundle"]["package_manifest"]["deployment_plan"]["health_url"], "http://127.0.0.1:8000/health")
        self.assertIn("uvicorn app:app --host 0.0.0.0 --port 8000", manifest["execution_bundle"]["command_script"]["text"])
        self.assertIn("# mode: deploy", manifest["execution_bundle"]["command_script"]["text"])

    def test_workspace_execution_readiness_tracks_active_and_failed_jobs(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "repo",
                "repo_url": "https://github.com/example/demo.git",
                "workspace_dir": "/tmp/demo",
                "run_command": "python train.py",
            },
        )
        node = next(item for item in workspace["nodes"] if item["kind"] == "path.resolve")
        state.workspaces = [workspace]
        state.jobs = [
            {
                "id": "job-active",
                "status": "running",
                "created_at": "2026-06-07T12:00:00",
                "metadata": {"workspace_id": workspace["id"], "node_id": node["id"], "node_kind": node["kind"]},
            }
        ]

        payload = TotalControlState.workspace_public_payload(state, workspace)
        readiness = payload["automation"]["execution_readiness"]
        self.assertEqual(readiness["status"], "running")
        self.assertEqual(readiness["gate"]["status"], "running")
        self.assertEqual(readiness["next_action"]["action"], "watch")
        self.assertEqual(readiness["job_state"]["active_count"], 1)

        state.jobs = [
            {
                "id": "job-failed",
                "status": "failed",
                "created_at": "2026-06-07T12:00:00",
                "metadata": {"workspace_id": workspace["id"], "node_id": node["id"], "node_kind": node["kind"]},
            }
        ]

        failed_payload = TotalControlState.workspace_public_payload(state, workspace)
        failed_readiness = failed_payload["automation"]["execution_readiness"]
        self.assertEqual(failed_readiness["status"], "failed")
        self.assertEqual(failed_readiness["gate"]["status"], "failed")
        self.assertEqual(failed_readiness["next_action"]["action"], "review_failed")
        self.assertEqual(failed_readiness["job_state"]["failed_count"], 1)

    def test_workspace_agent_topology_flags_disabled_bound_agent(self) -> None:
        state = make_registry_state()
        state.statuses = [
            {
                "id": "local",
                "online": True,
                "gpus": [
                    {
                        "index": 0,
                        "state": "idle",
                        "memory_free_mib": 24576,
                    }
                ],
            }
        ]
        template = state.workflow_templates[0]
        TotalControlState.update_workflow_template(
            state,
            template["id"],
            {
                "workspace_dir": "/tmp/relaygraph-disabled-agent",
                "env_name": "relaygraph-disabled-agent",
                "setup_command": "pip install -r requirements.txt",
                "run_command": "python train.py --smoke",
            },
        )
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                    "references": ["/datasets/imagenet-mini"],
                },
            },
        )
        for agent in workspace["agents"]:
            if agent["id"] == "runner":
                agent["enabled"] = False
        state.workspaces = [workspace]

        payload = TotalControlState.workspace_public_payload(state, workspace)
        topology = payload["automation"]["agent_topology"]
        run_stage = next(stage for stage in topology["stages"] if stage["id"] == "run")

        self.assertEqual(topology["status"], "blocked")
        self.assertEqual(topology["layers"]["agent"]["status"], "blocked")
        self.assertEqual(run_stage["status"], "blocked")
        self.assertTrue(any(gap["type"] == "agent_disabled" and gap["agent_id"] == "runner" for gap in topology["gaps"]))

    def test_apply_workspace_defaults_backfills_legacy_agent_tool_allowlists(self) -> None:
        state = make_registry_state()
        template = state.workflow_templates[0]
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                },
            },
        )
        legacy_missing = {"path.resolve", "dataset.find", "env.infer", "artifact.collect"}
        workspace["tools"] = [
            tool for tool in workspace["tools"]
            if str(tool.get("id") or "") not in legacy_missing
        ]
        for agent in workspace["agents"]:
            agent["tools"] = [
                tool_id for tool_id in agent.get("tools", [])
                if str(tool_id) not in legacy_missing
            ]
        state.workspaces = [workspace]

        result = TotalControlState.apply_workspace_automation_defaults(state, workspace["id"], {"apply_evidence": False})
        updated = result["workspace"]
        tool_ids = {str(tool.get("id") or "") for tool in updated["tools"]}
        agents = {str(agent.get("id") or ""): agent for agent in updated["agents"]}
        sources = {str(item.get("source") or "") for item in result["applied"]}
        topology = updated["automation"]["agent_topology"]

        self.assertTrue(legacy_missing.issubset(tool_ids))
        self.assertIn("path.resolve", agents["repo-scout"]["tools"])
        self.assertIn("dataset.find", agents["researcher"]["tools"])
        self.assertIn("env.infer", agents["env-builder"]["tools"])
        self.assertIn("artifact.collect", agents["evaluator"]["tools"])
        self.assertIn("default_tool_backfill", sources)
        self.assertIn("default_agent_tool_backfill", sources)
        self.assertEqual(topology["layers"]["tool"]["status"], "ready")
        self.assertFalse(any(gap["type"] == "required_tool_unbound" for gap in topology["gaps"]))

    def test_apply_workspace_automation_defaults_fills_inferred_node_config(self) -> None:
        state = make_registry_state()
        state.statuses = [
            {
                "id": "local",
                "online": True,
                "gpus": [
                    {
                        "index": 0,
                        "state": "idle",
                        "memory_free_mib": 24576,
                    }
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            data_root = Path(temp_dir) / "datasets"
            project_dir.mkdir()
            data_root.mkdir()
            (project_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")
            (project_dir / "tests").mkdir()
            template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "template_id": template["id"],
                    "inputs": {
                        "repo_urls": ["https://github.com/example/demo.git"],
                        "references": [str(project_dir), str(data_root)],
                    },
                },
            )
            state.workspaces = [workspace]

            result = TotalControlState.apply_workspace_automation_defaults(state, workspace["id"], {})
            updated = result["workspace"]
            nodes = {node["kind"]: node for node in updated["nodes"]}
            applied_fields = [item["field"] for item in result["applied"]]

            self.assertEqual(updated["workspace_dir"], str(project_dir))
            self.assertIn("workspace_dir", applied_fields)
            self.assertIn(str(data_root), nodes["path.resolve"]["config"]["data_roots"].splitlines())
            self.assertEqual(nodes["env.prepare"]["config"]["setup_command"], "pip install -r requirements.txt")
            self.assertEqual(nodes["run.command"]["config"]["run_command"], "python -m pytest -q")
            self.assertEqual(nodes["gpu.allocate"]["config"]["server_id"], "local")
            self.assertEqual(nodes["gpu.allocate"]["config"]["gpu_index"], "0")
            self.assertEqual(nodes["run.command"]["config"]["server_id"], "local")
            self.assertEqual(nodes["run.command"]["config"]["gpu_index"], "0")
            job_payload = state.workspace_node_job_payload(updated, nodes["run.command"])
            self.assertEqual(job_payload["server_id"], "local")
            self.assertEqual(str(job_payload["gpu_index"]), "0")
            self.assertEqual(job_payload["metadata"]["execution_bundle"]["target"]["server_id"], "local")
            self.assertEqual(job_payload["metadata"]["execution_bundle"]["target"]["gpu_index"], "0")
            self.assertIn("python -m pytest -q", job_payload["metadata"]["execution_bundle"]["command_script"]["text"])
            self.assertEqual(updated["automation"]["checks"][0]["status"], "ready")

    def test_apply_workspace_automation_defaults_preserves_cpu_scheduler_semantics(self) -> None:
        state = make_registry_state()
        state.statuses = [
            {
                "id": "local",
                "name": "Local",
                "online": True,
                "gpus": [],
                "host_resources": {
                    "ok": True,
                    "cpu": {"util_percent": 12, "load1": 0.3},
                    "memory": {"used_percent": 34},
                },
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()
            (project_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")
            (project_dir / "tests").mkdir()
            template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "template_id": template["id"],
                    "inputs": {
                        "repo_urls": ["https://github.com/example/demo.git"],
                        "references": [str(project_dir)],
                    },
                },
            )
            for node in workspace["nodes"]:
                if node["kind"] in {"gpu.allocate", "run.command"}:
                    node["config"]["gpu_policy"] = "cpu"
            state.workspaces = [workspace]

            result = TotalControlState.apply_workspace_automation_defaults(state, workspace["id"], {})
            updated = result["workspace"]
            nodes = {node["kind"]: node for node in updated["nodes"]}
            gpu_config = nodes["gpu.allocate"]["config"]
            run_config = nodes["run.command"]["config"]

            self.assertEqual(gpu_config["server_id"], "local")
            self.assertEqual(gpu_config["gpu_policy"], "cpu")
            self.assertEqual(gpu_config["gpu_index"], "none")
            self.assertEqual(run_config["server_id"], "local")
            self.assertEqual(run_config["gpu_policy"], "cpu")
            self.assertEqual(run_config["gpu_index"], "none")
            job_payload = state.workspace_node_job_payload(updated, nodes["run.command"])
            self.assertEqual(job_payload["gpu_index"], "none")
            bundle_env = updated["automation"]["reproduction_manifest"]["execution_bundle"]["steps"][2]["env"]
            self.assertNotIn("CUDA_VISIBLE_DEVICES", bundle_env)

    def test_apply_workspace_automation_defaults_uses_explicit_gpu_scheduler_candidate(self) -> None:
        state = make_registry_state()
        state.statuses = [
            {
                "id": "large",
                "name": "Large GPU",
                "online": True,
                "gpus": [
                    {
                        "index": 0,
                        "state": "idle",
                        "memory_free_mib": 24576,
                    }
                ],
            },
            {
                "id": "target",
                "name": "Target GPU",
                "online": True,
                "host_resources": {
                    "ok": True,
                    "cpu": {"util_percent": 11, "load1": 0.4},
                    "memory": {"used_percent": 35},
                },
                "gpus": [
                    {
                        "index": 1,
                        "state": "idle",
                        "memory_free_mib": 12288,
                        "memory_total_mib": 24576,
                    }
                ],
            },
        ]
        state.servers = [
            ServerConfig(id="large", name="Large GPU", mode="ssh", ssh_alias="large"),
            ServerConfig(id="target", name="Target GPU", mode="ssh", ssh_alias="target"),
        ]
        template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                },
            },
        )
        for node in workspace["nodes"]:
            if node["kind"] == "run.command":
                node["config"]["run_command"] = "python train.py"
        state.workspaces = [workspace]

        result = TotalControlState.apply_workspace_automation_defaults(
            state,
            workspace["id"],
            {
                "apply_evidence": False,
                "force": True,
                "scheduler_candidate": {
                    "server_id": "target",
                    "gpu_index": "1",
                    "mode": "gpu",
                    "gpu_policy": "auto",
                    "min_free_memory_gib": "8",
                },
            },
        )
        updated = result["workspace"]
        nodes = {node["kind"]: node for node in updated["nodes"]}
        gpu_config = nodes["gpu.allocate"]["config"]
        run_config = nodes["run.command"]["config"]

        self.assertEqual(gpu_config["server_id"], "target")
        self.assertEqual(gpu_config["gpu_policy"], "auto")
        self.assertEqual(gpu_config["gpu_index"], "1")
        self.assertEqual(gpu_config["min_free_memory_gib"], "8")
        self.assertEqual(run_config["server_id"], "target")
        self.assertEqual(run_config["gpu_policy"], "auto")
        self.assertEqual(run_config["gpu_index"], "1")
        self.assertEqual(run_config["min_free_memory_gib"], "8")
        job_payload = state.workspace_node_job_payload(updated, nodes["run.command"])
        self.assertEqual(job_payload["server_id"], "target")
        self.assertEqual(str(job_payload["gpu_index"]), "1")
        self.assertEqual(job_payload["metadata"]["execution_bundle"]["target"]["server_id"], "target")
        self.assertEqual(job_payload["metadata"]["execution_bundle"]["target"]["gpu_index"], "1")
        scheduler_binding = job_payload["metadata"]["scheduler_binding"]
        runtime_binding = job_payload["metadata"]["runtime_binding"]
        self.assertEqual(job_payload["metadata"]["execution_mode"], "gpu")
        self.assertEqual(scheduler_binding["status"], "ready")
        self.assertEqual(scheduler_binding["mode"], "gpu")
        self.assertEqual(scheduler_binding["server_id"], "target")
        self.assertEqual(scheduler_binding["gpu_index"], "1")
        self.assertEqual(scheduler_binding["min_free_memory_gib"], "8")
        self.assertEqual(scheduler_binding["selected"]["server_id"], "target")
        self.assertEqual(scheduler_binding["selected"]["gpu_index"], "1")
        self.assertEqual(scheduler_binding["selected"]["memory_free_mib"], 12288)
        self.assertIn("CPU 11.0%", scheduler_binding["host"]["summary"])
        self.assertEqual(runtime_binding["execution_mode"], "gpu")
        self.assertEqual(runtime_binding["server_id"], "target")
        self.assertEqual(runtime_binding["gpu_index"], "1")
        self.assertEqual(runtime_binding["scheduler_status"], "ready")
        resources = server_module.workspace_node_resources(updated, nodes["run.command"], job_payload)
        self.assertEqual(resources["scheduler_binding"]["server_id"], "target")
        self.assertEqual(resources["scheduler_binding"]["gpu_index"], "1")
        self.assertEqual(resources["scheduler_status"], "ready")
        self.assertEqual(resources["runtime_binding"]["execution_mode"], "gpu")

    def test_apply_workspace_automation_defaults_uses_explicit_cpu_scheduler_candidate(self) -> None:
        state = make_registry_state()
        state.statuses = [
            {
                "id": "cpu-host",
                "name": "CPU Host",
                "online": True,
                "gpus": [],
                "host_resources": {
                    "ok": True,
                    "cpu": {"util_percent": 8, "load1": 0.2},
                    "memory": {"used_percent": 28},
                },
            }
        ]
        state.servers = [ServerConfig(id="cpu-host", name="CPU Host", mode="ssh", ssh_alias="cpu-host")]
        template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                },
            },
        )
        for node in workspace["nodes"]:
            if node["kind"] == "run.command":
                node["config"]["run_command"] = "python train.py"
        state.workspaces = [workspace]

        result = TotalControlState.apply_workspace_automation_defaults(
            state,
            workspace["id"],
            {
                "apply_evidence": False,
                "force": True,
                "scheduler_candidate": {
                    "server_id": "cpu-host",
                    "gpu_index": "none",
                    "mode": "cpu",
                    "gpu_policy": "cpu",
                },
            },
        )
        updated = result["workspace"]
        nodes = {node["kind"]: node for node in updated["nodes"]}
        gpu_config = nodes["gpu.allocate"]["config"]
        run_config = nodes["run.command"]["config"]

        self.assertEqual(gpu_config["server_id"], "cpu-host")
        self.assertEqual(gpu_config["gpu_policy"], "cpu")
        self.assertEqual(gpu_config["gpu_index"], "none")
        self.assertFalse(str(gpu_config.get("min_free_memory_gib") or "").strip())
        self.assertEqual(run_config["server_id"], "cpu-host")
        self.assertEqual(run_config["gpu_policy"], "cpu")
        self.assertEqual(run_config["gpu_index"], "none")
        job_payload = state.workspace_node_job_payload(updated, nodes["run.command"])
        self.assertEqual(job_payload["server_id"], "cpu-host")
        self.assertEqual(job_payload["gpu_index"], "none")
        self.assertEqual(job_payload["metadata"]["execution_mode"], "cpu")
        self.assertEqual(job_payload["metadata"]["runtime_binding"]["execution_mode"], "cpu")
        self.assertEqual(job_payload["metadata"]["scheduler_binding"]["mode"], "cpu")
        self.assertEqual(job_payload["metadata"]["scheduler_binding"]["policy"], "cpu")
        self.assertEqual(job_payload["metadata"]["scheduler_binding"]["gpu_index"], "none")
        self.assertEqual(job_payload["metadata"]["scheduler_binding"]["selected"]["gpu_index"], "cpu")
        resources = server_module.workspace_node_resources(updated, nodes["run.command"], job_payload)
        self.assertEqual(resources["execution_mode"], "cpu")
        self.assertEqual(resources["scheduler_binding"]["mode"], "cpu")
        self.assertEqual(resources["scheduler_binding"]["gpu_index"], "none")
        bundle_env = updated["automation"]["reproduction_manifest"]["execution_bundle"]["steps"][2]["env"]
        self.assertNotIn("CUDA_VISIBLE_DEVICES", bundle_env)

    def test_apply_workspace_automation_defaults_backfills_discovery_evidence(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace_dir = root / "project"
            data_root = root / "datasets"
            dataset_dir = data_root / "imagenet-mini"
            resolved_output_dir = root / "resolved-outputs"
            run_dir = workspace_dir / "runs"
            metric_dir = workspace_dir / "results"
            data_root.mkdir()
            dataset_dir.mkdir()
            resolved_output_dir.mkdir()

            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                    "run_command": "python train.py",
                },
            )
            state.workspaces = [workspace]
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            dataset_log = root / "dataset.log"
            dataset_log.write_text(
                "\n".join(
                    [
                        f"candidate_root: {data_root} exists=True",
                        "  match: imagenet-mini (dir)",
                    ]
                ),
                encoding="utf-8",
            )
            env_log = root / "env.log"
            env_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        "found_manifest: requirements.txt",
                        "suggest_setup: pip install -r requirements.txt",
                    ]
                ),
                encoding="utf-8",
            )
            artifact_log = root / "artifact.log"
            artifact_log.write_text(
                "\n".join(
                    [
                        f"artifact: {run_dir} exists=True",
                        f"metric: {metric_dir} exists=True",
                    ]
                ),
                encoding="utf-8",
            )
            path_log = root / "path.log"
            path_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        f"output_root: {resolved_output_dir} exists=True",
                    ]
                ),
                encoding="utf-8",
            )
            state.jobs = [
                {
                    "id": "job-path",
                    "status": "done",
                    "created_at": "2026-06-07T09:58:00",
                    "finished_at": "2026-06-07T09:59:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(path_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["path.resolve"]["id"]},
                },
                {
                    "id": "job-dataset",
                    "status": "done",
                    "created_at": "2026-06-07T10:00:00",
                    "finished_at": "2026-06-07T10:01:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(dataset_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["dataset.find"]["id"]},
                },
                {
                    "id": "job-env",
                    "status": "done",
                    "created_at": "2026-06-07T10:02:00",
                    "finished_at": "2026-06-07T10:03:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(env_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["env.infer"]["id"]},
                },
                {
                    "id": "job-artifact",
                    "status": "done",
                    "created_at": "2026-06-07T10:04:00",
                    "finished_at": "2026-06-07T10:05:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(artifact_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["artifact.collect"]["id"]},
                },
            ]

            preview = TotalControlState.workspace_public_payload(state, workspace)
            backfill = preview["automation"]["evidence_backfill"]
            ready_fields = {
                (item["node_kind"], item["field"])
                for item in backfill["items"]
                if item["status"] == "ready"
            }

            self.assertEqual(backfill["status"], "ready")
            self.assertIn(("dataset.find", "dataset_hints"), ready_fields)
            self.assertIn(("env.prepare", "setup_command"), ready_fields)
            self.assertIn(("artifact.collect", "artifact_paths"), ready_fields)
            self.assertIn(("eval.report", "metric_paths"), ready_fields)

            result = TotalControlState.apply_workspace_automation_defaults(state, workspace["id"], {})
            updated_nodes = {node["kind"]: node for node in result["workspace"]["nodes"]}
            evidence_fields = [item["field"] for item in result["evidence_applied"]]

            self.assertIn(str(data_root), updated_nodes["dataset.find"]["config"]["data_roots"].splitlines())
            self.assertIn(str(dataset_dir), updated_nodes["dataset.find"]["config"]["dataset_hints"].splitlines())
            self.assertEqual(updated_nodes["env.prepare"]["config"]["setup_command"], "pip install -r requirements.txt")
            self.assertIn(str(resolved_output_dir), updated_nodes["path.resolve"]["config"]["output_roots"].splitlines())
            self.assertIn(str(resolved_output_dir), updated_nodes["artifact.collect"]["config"]["artifact_paths"].splitlines())
            self.assertIn(str(run_dir), updated_nodes["artifact.collect"]["config"]["artifact_paths"].splitlines())
            self.assertIn(str(metric_dir), updated_nodes["artifact.collect"]["config"]["metric_paths"].splitlines())
            self.assertIn(str(metric_dir), updated_nodes["eval.report"]["config"]["metric_paths"].splitlines())
            self.assertIn("dataset_hints", evidence_fields)
            self.assertIn("setup_command", evidence_fields)
            self.assertIn(str(resolved_output_dir), result["workspace"]["automation"]["reproduction_manifest"]["paths"]["artifact_paths"])
            self.assertTrue(all(item.get("source") == "evidence" for item in result["evidence_applied"]))

    def test_apply_workspace_automation_defaults_applies_single_backfill_item(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace_dir = root / "project"
            data_root = root / "datasets"
            dataset_dir = data_root / "imagenet-mini"
            data_root.mkdir()
            dataset_dir.mkdir()

            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                    "run_command": "python train.py",
                },
            )
            state.workspaces = [workspace]
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            dataset_log = root / "dataset.log"
            dataset_log.write_text(
                "\n".join(
                    [
                        f"candidate_root: {data_root} exists=True",
                        "  match: imagenet-mini (dir)",
                    ]
                ),
                encoding="utf-8",
            )
            env_log = root / "env.log"
            env_log.write_text("suggest_setup: pip install -r requirements.txt\n", encoding="utf-8")
            state.jobs = [
                {
                    "id": "job-dataset",
                    "status": "done",
                    "created_at": "2026-06-07T10:00:00",
                    "finished_at": "2026-06-07T10:01:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(dataset_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["dataset.find"]["id"]},
                },
                {
                    "id": "job-env",
                    "status": "done",
                    "created_at": "2026-06-07T10:02:00",
                    "finished_at": "2026-06-07T10:03:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(env_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["env.infer"]["id"]},
                },
            ]

            result = TotalControlState.apply_workspace_automation_defaults(
                state,
                workspace["id"],
                {
                    "apply_defaults": False,
                    "apply_evidence": False,
                    "backfill_item": {
                        "node_kind": "dataset.find",
                        "field": "dataset_hints",
                    },
                },
            )
            updated_nodes = {node["kind"]: node for node in result["workspace"]["nodes"]}

            self.assertIn(str(dataset_dir), updated_nodes["dataset.find"]["config"]["dataset_hints"].splitlines())
            self.assertFalse(str(updated_nodes["env.prepare"]["config"].get("setup_command") or "").strip())
            self.assertEqual([item["field"] for item in result["evidence_applied"]], ["dataset_hints"])
            self.assertEqual(result["evidence_applied"][0]["node_kind"], "dataset.find")
            self.assertTrue(all(item.get("source") == "evidence" for item in result["evidence_applied"]))

    def test_repo_inspect_log_feeds_discovery_evidence_backfill(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace_dir = root / "project"
            workspace_dir.mkdir()
            for child in ["datasets", "runs", "results"]:
                (workspace_dir / child).mkdir()
            (workspace_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")
            (workspace_dir / "README.md").write_text("# demo\n", encoding="utf-8")

            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                    "run_command": "python train.py",
                },
            )
            state.workspaces = [workspace]
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            repo_log = root / "repo-inspect.log"
            repo_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        "found: README.md",
                        "found: requirements.txt",
                        "top_level: README.md, datasets/, results/, runs/, src/",
                    ]
                ),
                encoding="utf-8",
            )
            state.jobs = [
                {
                    "id": "job-repo-inspect",
                    "status": "done",
                    "created_at": "2026-06-07T09:00:00",
                    "finished_at": "2026-06-07T09:01:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(repo_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["repo.inspect"]["id"]},
                }
            ]

            payload = TotalControlState.workspace_public_payload(state, workspace)
            repo_state = next(item for item in payload["execution"]["nodes"] if item["kind"] == "repo.inspect")
            artifact_pairs = {(item["label"], item["resolved_path"]) for item in repo_state["artifacts"]}
            evidence = {item["id"]: item for item in payload["automation"]["evidence"]}
            backfill = payload["automation"]["evidence_backfill"]
            ready_fields = {
                (item["node_kind"], item["field"])
                for item in backfill["items"]
                if item["status"] == "ready"
            }

            self.assertIn(("环境清单", str(workspace_dir / "requirements.txt")), artifact_pairs)
            self.assertIn(("候选数据根", str(workspace_dir / "datasets")), artifact_pairs)
            self.assertIn(("输出目录", str(workspace_dir / "results")), artifact_pairs)
            self.assertIn(("产物路径", str(workspace_dir / "runs")), artifact_pairs)
            self.assertTrue(
                any(
                    item["label"] == "安装建议" and item["value"] == "pip install -r requirements.txt"
                    for item in evidence["env"]["items"]
                )
            )
            self.assertIn(("dataset.find", "data_roots"), ready_fields)
            self.assertIn(("env.prepare", "setup_command"), ready_fields)
            self.assertIn(("artifact.collect", "artifact_paths"), ready_fields)
            self.assertIn(("eval.report", "metric_paths"), ready_fields)

    def test_repo_inspect_log_backfills_run_command_suggestion(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace_dir = root / "project"
            workspace_dir.mkdir()
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                },
            )
            state.workspaces = [workspace]
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            nodes["run.command"]["config"]["run_command"] = ""
            repo_log = root / "repo-inspect-run.log"
            repo_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        "found: README.md",
                        "top_level: README.md, train.py, configs/, outputs/",
                    ]
                ),
                encoding="utf-8",
            )
            state.jobs = [
                {
                    "id": "job-repo-inspect-run",
                    "status": "done",
                    "created_at": "2026-06-07T09:10:00",
                    "finished_at": "2026-06-07T09:11:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(repo_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["repo.inspect"]["id"]},
                }
            ]

            preview = TotalControlState.workspace_public_payload(state, workspace)
            evidence = {item["id"]: item for item in preview["automation"]["evidence"]}
            ready_fields = {
                (item["node_kind"], item["field"])
                for item in preview["automation"]["evidence_backfill"]["items"]
                if item["status"] == "ready"
            }

            self.assertTrue(
                any(
                    item["label"] == "运行命令候选" and item["value"] == "python train.py --help"
                    for item in evidence["run"]["items"]
                )
            )
            self.assertIn(("run.command", "run_command"), ready_fields)

            result = TotalControlState.apply_workspace_automation_defaults(state, workspace["id"], {})
            updated_nodes = {node["kind"]: node for node in result["workspace"]["nodes"]}
            evidence_fields = [item["field"] for item in result["evidence_applied"]]

            self.assertEqual(updated_nodes["run.command"]["config"]["run_command"], "python train.py --help")
            self.assertIn("run_command", evidence_fields)
            self.assertEqual(
                result["workspace"]["automation"]["reproduction_manifest"]["commands"]["run_command"],
                "python train.py --help",
            )

    def test_run_workspace_discovery_applies_defaults_and_sequences_safe_nodes(self) -> None:
        state = make_registry_state()
        state.statuses = [
            {
                "id": "local",
                "online": True,
                "gpus": [
                    {
                        "index": 0,
                        "state": "idle",
                        "memory_free_mib": 16384,
                    }
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            data_root = Path(temp_dir) / "datasets"
            project_dir.mkdir()
            data_root.mkdir()
            (project_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")
            template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "template_id": template["id"],
                    "inputs": {
                        "repo_urls": ["https://github.com/example/demo.git"],
                        "references": [str(project_dir), str(data_root)],
                    },
                },
            )
            state.workspaces = [workspace]

            result = TotalControlState.run_workspace_discovery(state, workspace["id"], {})
            jobs = result["jobs"]
            job_kinds = [job["metadata"]["node_kind"] for job in jobs]

            self.assertEqual(
                job_kinds,
                ["path.resolve", "repo.inspect", "dataset.find", "env.infer", "gpu.allocate", "artifact.collect"],
            )
            self.assertTrue(result["applied"])
            self.assertFalse(result["skipped"])
            self.assertEqual(result["workspace"]["workspace_dir"], str(project_dir))
            self.assertEqual([job["metadata"]["workflow_phase"] for job in jobs], ["discovery"] * len(jobs))
            self.assertEqual(jobs[0]["target_job_ids"], [])
            for index, job in enumerate(jobs[1:], start=1):
                self.assertEqual(job["target_job_ids"], [jobs[index - 1]["id"]])
            self.assertEqual(jobs[0]["cwd"], "")
            self.assertEqual(jobs[1]["cwd"], str(project_dir))
            self.assertNotIn("run.command", job_kinds)
            self.assertNotIn("env.prepare", job_kinds)
            self.assertIn("run_id", result)
            self.assertEqual(result["run"]["kind"], "discovery")
            self.assertEqual(len(result["run"]["steps"]), len(jobs))
            self.assertEqual(
                [job["metadata"]["execution_run_id"] for job in jobs],
                [result["run_id"]] * len(jobs),
            )
            self.assertEqual(
                [job["metadata"]["step_index"] for job in jobs],
                list(range(len(jobs))),
            )
            runs = result["workspace"].get("runs")
            self.assertIsInstance(runs, list)
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["id"], result["run_id"])
            self.assertEqual(len(runs[0]["steps"]), len(jobs))

    def test_run_workspace_discovery_bootstraps_missing_repo_source_first(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = str(Path(temp_dir) / "cloned-demo")
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": workspace_dir,
                    "run_command": "python train.py",
                },
            )
            state.workspaces = [workspace]

            result = TotalControlState.run_workspace_discovery(
                state,
                workspace["id"],
                {"apply_defaults": True, "include_source": True},
            )
            jobs = result["jobs"]
            job_kinds = [job["metadata"]["node_kind"] for job in jobs]

            self.assertEqual(
                job_kinds,
                [
                    "repo.clone",
                    "path.resolve",
                    "repo.inspect",
                    "dataset.find",
                    "env.infer",
                    "gpu.allocate",
                    "artifact.collect",
                ],
            )
            self.assertFalse(Path(workspace_dir).exists())
            self.assertEqual(jobs[0]["cwd"], "")
            self.assertIn("git clone", jobs[0]["command"])
            self.assertEqual(jobs[0]["target_job_ids"], [])
            for index, job in enumerate(jobs[1:], start=1):
                self.assertEqual(job["target_job_ids"], [jobs[index - 1]["id"]])
            self.assertEqual(jobs[2]["cwd"], workspace_dir)
            self.assertNotIn("env.prepare", job_kinds)
            self.assertNotIn("run.command", job_kinds)

    def test_run_workspace_workflow_auto_backfills_discovery_before_gate(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = Path(temp_dir) / "project"
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                    "run_command": "python train.py",
                    "report_command": "python eval.py",
                },
            )
            state.workspaces = [workspace]
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            env_log = Path(temp_dir) / "env.log"
            env_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        "found_manifest: requirements.txt",
                        "suggest_setup: pip install -r requirements.txt",
                    ]
                ),
                encoding="utf-8",
            )
            state.jobs = [
                {
                    "id": "job-env-discovery",
                    "status": "done",
                    "created_at": "2026-06-07T11:00:00",
                    "finished_at": "2026-06-07T11:01:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(env_log),
                    "metadata": {"workspace_id": workspace["id"], "node_id": nodes["env.infer"]["id"]},
                }
            ]

            result = TotalControlState.run_workspace_workflow(state, workspace["id"])
            job_kinds = [job["metadata"]["node_kind"] for job in result["jobs"]]
            updated_nodes = {node["kind"]: node for node in result["workspace"]["nodes"]}

            self.assertIn("env.prepare", job_kinds)
            self.assertEqual(updated_nodes["env.prepare"]["config"]["setup_command"], "pip install -r requirements.txt")
            self.assertIn("setup_command", [item["field"] for item in result["evidence_applied"]])
            self.assertTrue(result["applied"])
            self.assertEqual(result["jobs"][job_kinds.index("env.prepare")]["command"], "pip install -r requirements.txt")

    def test_advance_workspace_automation_starts_with_safe_discovery(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(project_dir),
                    "run_command": "python train.py",
                },
            )
            state.workspaces = [workspace]

            result = TotalControlState.advance_workspace_automation(state, workspace["id"], {})
            job_kinds = [job["metadata"]["node_kind"] for job in result["jobs"]]

            self.assertEqual(result["action"], "discover")
            self.assertEqual(result["decision"]["action"], "watch")
            self.assertIn("观察", result["decision"]["reason"])
            self.assertIn("path.resolve", job_kinds)
            self.assertIn("dataset.find", job_kinds)
            self.assertNotIn("env.prepare", job_kinds)
            self.assertNotIn("run.command", job_kinds)
            first_contract = result["jobs"][0]["metadata"]["workflow_contract_node"]
            self.assertEqual(first_contract["context"]["previous_key"], "$prev.output")
            self.assertIn("output_key", first_contract)

    def test_advance_workspace_automation_waits_for_active_jobs(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "repo",
                "repo_url": "https://github.com/example/demo.git",
                "workspace_dir": "/tmp/demo",
                "run_command": "python train.py",
            },
        )
        node = next(item for item in workspace["nodes"] if item["kind"] == "path.resolve")
        state.workspaces = [workspace]
        state.jobs = [
            {
                "id": "job-active",
                "status": "running",
                "created_at": "2026-06-07T12:00:00",
                "metadata": {"workspace_id": workspace["id"], "node_id": node["id"], "node_kind": node["kind"]},
            }
        ]

        result = TotalControlState.advance_workspace_automation(state, workspace["id"], {})

        self.assertEqual(result["action"], "watch")
        self.assertEqual(result["decision"]["action"], "watch")
        self.assertIn("当前有任务", result["decision"]["reason"])
        self.assertFalse(result["jobs"])
        self.assertEqual(result["active_job_ids"], ["job-active"])

    def test_advance_workspace_automation_runs_after_discovery_evidence(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = Path(temp_dir) / "project"
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                    "run_command": "python train.py",
                    "report_command": "python eval.py",
                },
            )
            state.workspaces = [workspace]
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            env_log = Path(temp_dir) / "env.log"
            env_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        "found_manifest: requirements.txt",
                        "suggest_setup: pip install -r requirements.txt",
                    ]
                ),
                encoding="utf-8",
            )
            state.jobs = [
                {
                    "id": "job-env-discovery",
                    "status": "done",
                    "created_at": "2026-06-07T12:10:00",
                    "finished_at": "2026-06-07T12:11:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(env_log),
                    "metadata": {
                        "workspace_id": workspace["id"],
                        "node_id": nodes["env.infer"]["id"],
                        "node_kind": "env.infer",
                        "workflow_phase": "discovery",
                    },
                }
            ]

            result = TotalControlState.advance_workspace_automation(state, workspace["id"], {})
            job_kinds = [job["metadata"]["node_kind"] for job in result["jobs"]]

            self.assertEqual(result["action"], "run")
            self.assertEqual(result["decision"]["action"], "watch")
            self.assertIn("观察", result["decision"]["reason"])
            self.assertIn("env.prepare", job_kinds)
            self.assertIn("setup_command", [item["field"] for item in result["evidence_applied"]])
            updated_nodes = {node["kind"]: node for node in result["workspace"]["nodes"]}
            self.assertEqual(updated_nodes["env.prepare"]["config"]["setup_command"], "pip install -r requirements.txt")

    def test_advance_workspace_automation_runs_after_discovered_run_command(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = Path(temp_dir) / "project"
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                    "report_command": "python eval.py",
                },
            )
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            nodes["run.command"]["config"]["run_command"] = ""
            state.workspaces = [workspace]
            env_log = Path(temp_dir) / "env.log"
            env_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        "found_manifest: requirements.txt",
                        "suggest_setup: pip install -r requirements.txt",
                    ]
                ),
                encoding="utf-8",
            )
            repo_log = Path(temp_dir) / "repo-inspect.log"
            repo_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {workspace_dir}",
                        "found: README.md",
                        "top_level: README.md, train.py, configs/, outputs/",
                    ]
                ),
                encoding="utf-8",
            )
            state.jobs = [
                {
                    "id": "job-repo-discovery",
                    "status": "done",
                    "created_at": "2026-06-07T12:00:00",
                    "finished_at": "2026-06-07T12:01:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(repo_log),
                    "metadata": {
                        "workspace_id": workspace["id"],
                        "node_id": nodes["repo.inspect"]["id"],
                        "node_kind": "repo.inspect",
                        "workflow_phase": "discovery",
                    },
                },
                {
                    "id": "job-env-discovery",
                    "status": "done",
                    "created_at": "2026-06-07T12:02:00",
                    "finished_at": "2026-06-07T12:03:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(env_log),
                    "metadata": {
                        "workspace_id": workspace["id"],
                        "node_id": nodes["env.infer"]["id"],
                        "node_kind": "env.infer",
                        "workflow_phase": "discovery",
                    },
                },
            ]

            result = TotalControlState.advance_workspace_automation(state, workspace["id"], {})
            updated_nodes = {node["kind"]: node for node in result["workspace"]["nodes"]}
            job_kinds = [job["metadata"]["node_kind"] for job in result["jobs"]]

            self.assertEqual(result["action"], "run")
            self.assertEqual(updated_nodes["run.command"]["config"]["run_command"], "python train.py --help")
            self.assertIn("run_command", [item["field"] for item in result["evidence_applied"]])
            self.assertIn("run.command", job_kinds)
            run_job = result["jobs"][job_kinds.index("run.command")]
            self.assertEqual(run_job["command"], "python train.py --help")

    def test_run_workspace_workflow_blocks_before_partial_job_creation_when_not_ready(self) -> None:
        state = make_registry_state()
        template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                },
            },
        )
        state.workspaces = [workspace]

        with self.assertRaises(server_module.WorkspaceWorkflowReadinessError) as raised:
            TotalControlState.run_workspace_workflow(state, workspace["id"])

        self.assertFalse(state.jobs)
        self.assertTrue(any(item["id"] == "run" for item in raised.exception.blocked_checks))
        self.assertIn("工作流运行前检查未通过", str(raised.exception))

    def test_run_workspace_workflow_force_still_validates_all_node_payloads_before_creation(self) -> None:
        state = make_registry_state()
        template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": template["id"],
                "inputs": {
                    "repo_urls": ["https://github.com/example/demo.git"],
                },
            },
        )
        state.workspaces = [workspace]

        with self.assertRaises(server_module.WorkspaceWorkflowReadinessError) as raised:
            TotalControlState.run_workspace_workflow(state, workspace["id"], {"force": True})

        self.assertFalse(state.jobs)
        blocked_kinds = {item["node_kind"] for item in raised.exception.blocked_checks}
        self.assertIn("run.command", blocked_kinds)
        self.assertIn("env.prepare", blocked_kinds)

    def test_run_workspace_workflow_until_node_runs_prefix_without_future_run_gate(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = Path(temp_dir) / "project"
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "source_type": "repo",
                    "repo_url": "https://github.com/example/demo.git",
                    "workspace_dir": str(workspace_dir),
                },
            )
            nodes = {node["kind"]: node for node in workspace["nodes"]}
            nodes["env.prepare"]["config"]["setup_command"] = "pip install -r requirements.txt"
            nodes["run.command"]["config"]["run_command"] = ""
            state.workspaces = [workspace]

            result = TotalControlState.run_workspace_workflow(
                state,
                workspace["id"],
                {
                    "until_node_id": nodes["env.prepare"]["id"],
                    "auto_apply": False,
                },
            )
            job_kinds = [job["metadata"]["node_kind"] for job in result["jobs"]]

            self.assertEqual(job_kinds[-1], "env.prepare")
            self.assertIn("repo.clone", job_kinds)
            self.assertIn("dataset.find", job_kinds)
            self.assertNotIn("gpu.allocate", job_kinds)
            self.assertNotIn("run.command", job_kinds)
            self.assertEqual(result["jobs"][-1]["command"], "pip install -r requirements.txt")
            self.assertEqual(result["jobs"][-1]["metadata"]["workflow_phase"], "run_to_node")
            self.assertEqual(result["jobs"][-1]["metadata"]["workflow_until_node_id"], nodes["env.prepare"]["id"])
            self.assertEqual(result["execution_package"]["scope"]["mode"], "run_to_node")
            self.assertEqual(result["execution_package"]["scope"]["target_node_kind"], "env.prepare")

    def test_workspace_public_payload_derives_execution_state_for_template_instance(self) -> None:
        state = object.__new__(TotalControlState)
        state.lock = threading.RLock()
        state.jobs = []
        state.workspaces = []
        state.save_workspaces = lambda: None
        state.tool_definitions = server_module.workspace_default_tools()
        state.agent_definitions = server_module.workspace_default_agents()
        state.workflow_templates = server_module.build_default_workflow_templates(
            state.agent_definitions,
            state.tool_definitions,
        )

        workspace = TotalControlState.create_workspace(
            state,
            {
                "template_id": state.workflow_templates[0]["id"],
                "inputs": {
                    "goal_text": "先整理 repo 运行链，再准备环境并跑一轮验证",
                    "repo_urls": ["https://github.com/example/demo.git"],
                },
            },
        )
        state.workspaces = [workspace]
        executable_nodes = [node for node in workspace["nodes"] if node["kind"] in server_module.WORKSPACE_EXECUTABLE_NODE_KINDS]
        self.assertGreaterEqual(len(executable_nodes), 2)
        first_node = executable_nodes[0]
        second_node = executable_nodes[1]
        first_handler = first_node.get("handler") if isinstance(first_node.get("handler"), dict) else {}
        second_handler = second_node.get("handler") if isinstance(second_node.get("handler"), dict) else {}
        state.jobs = [
            {
                "id": "job-done",
                "status": "done",
                "created_at": "2026-06-06T10:00:00",
                "started_at": "2026-06-06T10:00:01",
                "finished_at": "2026-06-06T10:01:00",
                "server_id": "local",
                "gpu_index": "none",
                "log_path": "/tmp/job-done.log",
                "metadata": {
                    "workspace_id": workspace["id"],
                    "node_id": first_node["id"],
                },
            },
            {
                "id": "job-running",
                "status": "running",
                "created_at": "2026-06-06T10:10:00",
                "started_at": "2026-06-06T10:10:01",
                "server_id": "local",
                "gpu_index": "none",
                "log_path": "/tmp/job-running.log",
                "metadata": {
                    "workspace_id": workspace["id"],
                    "node_id": second_node["id"],
                },
            },
        ]

        payload = TotalControlState.workspace_public_payload(state, workspace)
        execution = payload["execution"]

        self.assertEqual(execution["current_node_id"], second_node["id"])
        self.assertEqual(execution["current_agent_id"], str(second_handler.get("agent_id") or ""))
        self.assertEqual(execution["counts"]["done"], 1)
        self.assertEqual(execution["counts"]["running"], 1)
        self.assertGreaterEqual(execution["counts"]["pending"], 1)
        self.assertEqual(execution["last_job_id"], "job-running")
        self.assertEqual(execution["last_job_status"], "running")
        node_states = {item["id"]: item for item in execution["nodes"]}
        self.assertEqual(node_states[first_node["id"]]["status"], "done")
        self.assertEqual(node_states[first_node["id"]]["agent_id"], str(first_handler.get("agent_id") or ""))
        self.assertEqual(node_states[second_node["id"]]["status"], "running")
        self.assertEqual(node_states[second_node["id"]]["job_id"], "job-running")
        self.assertTrue(any(item["status"] == "done" for item in node_states[first_node["id"]]["trace"]))
        self.assertTrue(any(item["status"] == "running" for item in node_states[second_node["id"]]["trace"]))
        self.assertEqual(node_states[second_node["id"]]["resources"]["server_id"], "local")
        running_contract = node_states[second_node["id"]]["workflow_contract_node"]
        self.assertEqual(running_contract["node_id"], second_node["id"])
        self.assertEqual(running_contract["node_kind"], second_node["kind"])
        self.assertEqual(running_contract["context"]["outputs_key"], "$context.outputs")
        self.assertIn("input_mapping", running_contract)
        self.assertIn("output_key", running_contract)
        self.assertTrue(any(item["label"] == "最近日志" for item in node_states[second_node["id"]]["artifacts"]))

    def test_workspace_public_payload_merges_node_log_discovery(self) -> None:
        state = make_registry_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            data_root = Path(temp_dir) / "datasets"
            dataset_dir = data_root / "imagenet-mini"
            project_dir.mkdir()
            data_root.mkdir()
            dataset_dir.mkdir()
            (project_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")

            template = next(item for item in state.workflow_templates if item["source"]["type"] == "repo")
            TotalControlState.update_workflow_template(
                state,
                template["id"],
                {
                    "workspace_dir": str(project_dir),
                    "env_name": "relaygraph-log-check",
                    "run_command": "python train.py --smoke",
                },
            )
            workspace = TotalControlState.create_workspace(
                state,
                {
                    "template_id": template["id"],
                    "inputs": {
                        "repo_urls": ["https://github.com/example/demo.git"],
                    },
                },
            )
            state.workspaces = [workspace]
            dataset_node = next(node for node in workspace["nodes"] if node["kind"] == "dataset.find")
            env_node = next(node for node in workspace["nodes"] if node["kind"] == "env.infer")
            run_node = next(node for node in workspace["nodes"] if node["kind"] == "run.command")
            dataset_log = Path(temp_dir) / "dataset.log"
            dataset_log.write_text(
                "\n".join(
                    [
                        f"candidate_root: {data_root} exists=True",
                        "  match: imagenet-mini (dir)",
                    ]
                ),
                encoding="utf-8",
            )
            env_log = Path(temp_dir) / "env.log"
            env_log.write_text(
                "\n".join(
                    [
                        f"workspace_dir: {project_dir}",
                        "found_manifest: requirements.txt",
                        "suggest_setup: pip install -r requirements.txt",
                    ]
                ),
                encoding="utf-8",
            )
            run_log = Path(temp_dir) / "run.log"
            run_log.write_text(
                "\n".join(
                    [
                        "epoch=1 train_loss=0.42",
                        "accuracy: 91.3%",
                        "mAP=0.56",
                    ]
                ),
                encoding="utf-8",
            )
            state.jobs = [
                {
                    "id": "job-dataset",
                    "status": "done",
                    "created_at": "2026-06-06T10:00:00",
                    "started_at": "2026-06-06T10:00:01",
                    "finished_at": "2026-06-06T10:01:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(dataset_log),
                    "metadata": {
                        "workspace_id": workspace["id"],
                        "node_id": dataset_node["id"],
                    },
                },
                {
                    "id": "job-env",
                    "status": "done",
                    "created_at": "2026-06-06T10:02:00",
                    "started_at": "2026-06-06T10:02:01",
                    "finished_at": "2026-06-06T10:03:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(env_log),
                    "metadata": {
                        "workspace_id": workspace["id"],
                        "node_id": env_node["id"],
                    },
                },
                {
                    "id": "job-run",
                    "status": "done",
                    "created_at": "2026-06-06T10:04:00",
                    "started_at": "2026-06-06T10:04:01",
                    "finished_at": "2026-06-06T10:05:00",
                    "server_id": "local",
                    "gpu_index": "none",
                    "log_path": str(run_log),
                    "metadata": {
                        "workspace_id": workspace["id"],
                        "node_id": run_node["id"],
                    },
                },
            ]

            payload = TotalControlState.workspace_public_payload(state, workspace)
            node_states = {item["id"]: item for item in payload["execution"]["nodes"]}
            dataset_artifacts = node_states[dataset_node["id"]]["artifacts"]
            env_state = node_states[env_node["id"]]
            run_state = node_states[run_node["id"]]

            self.assertTrue(
                any(
                    item["label"] == "候选数据集" and item["resolved_path"] == str(dataset_dir)
                    for item in dataset_artifacts
                )
            )
            self.assertTrue(any(item["label"] == "环境清单" and item["status"] == "found" for item in env_state["artifacts"]))
            self.assertEqual(env_state["resources"]["setup_suggestion"], "pip install -r requirements.txt")
            self.assertEqual(env_state["resources"]["found_manifests"], ["requirements.txt"])
            self.assertTrue(any(item["key"] == "accuracy" and item["value"] == "91.3%" for item in run_state["resources"]["metrics"]))
            self.assertTrue(any(item["key"] == "mAP" and item["value"] == "0.56" for item in run_state["resources"]["metrics"]))
            evidence = {item["id"]: item for item in payload["automation"]["evidence"]}
            self.assertTrue(
                any(
                    item["label"] == "候选数据集" and item["value"] == str(dataset_dir)
                    for item in evidence["dataset"]["items"]
                )
            )
            self.assertTrue(
                any(
                    item["label"] == "安装建议" and item["value"] == "pip install -r requirements.txt"
                    for item in evidence["env"]["items"]
                )
            )
            self.assertTrue(
                any(
                    item["label"] == "accuracy" and item["value"] == "accuracy=91.3%"
                    for item in evidence["metric"]["items"]
                )
            )
            self.assertGreaterEqual(evidence["dataset"]["count"], 2)
            self.assertGreaterEqual(evidence["env"]["count"], 2)
            self.assertGreaterEqual(evidence["metric"]["count"], 3)
            report = payload["automation"]["report"]
            self.assertEqual(report["status"], "blocked")
            self.assertIn("阻塞", report["headline"])
            self.assertTrue(any(item["label"] == "核心指标" and "accuracy=91.3%" in item["value"] for item in report["highlights"]))
            self.assertTrue(report["next_actions"])


class WorkspaceExecutionRunTests(unittest.TestCase):
    def test_workspace_public_payload_includes_refreshed_runs(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "idea",
                "idea_text": "demo",
                "brief": "demo",
            },
        )
        state.workspaces = [workspace]
        job = {
            "id": "job-run-sync-1",
            "status": "queued",
            "created_at": "2026-06-10T10:00:00+08:00",
            "started_at": "",
            "finished_at": "",
            "error": "",
            "metadata": {
                "workspace_id": workspace["id"],
                "node_id": "node-1",
                "node_kind": "path.resolve",
                "node_title": "路径解析",
                "execution_run_id": "run-sync-1",
                "step_index": 0,
            },
        }
        state.jobs = [job]
        workspace["runs"] = [
            {
                "id": "run-sync-1",
                "workspace_id": workspace["id"],
                "kind": "discovery",
                "status": "queued",
                "trigger": "user",
                "summary": "测试发现",
                "steps": [
                    {
                        "index": 0,
                        "node_id": "node-1",
                        "node_kind": "path.resolve",
                        "node_title": "路径解析",
                        "executor": "job",
                        "job_id": "job-run-sync-1",
                        "status": "queued",
                    }
                ],
                "created_at": "2026-06-10T10:00:00+08:00",
                "updated_at": "2026-06-10T10:00:00+08:00",
            }
        ]
        public = state.workspace_public_payload(workspace)
        self.assertEqual(public["runs"][0]["status"], "queued")

        job["status"] = "done"
        job["finished_at"] = "2026-06-10T10:05:00+08:00"
        state.sync_workspace_execution_runs_from_jobs(workspace["id"])
        public_done = state.workspace_public_payload(workspace)
        self.assertEqual(public_done["runs"][0]["status"], "done")
        self.assertEqual(public_done["runs"][0]["steps"][0]["status"], "done")
        self.assertEqual(public_done["runs"][0]["progress"]["percent"], 100)

    def test_list_workspace_execution_runs_endpoint_payload(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "idea",
                "idea_text": "demo",
                "brief": "demo",
            },
        )
        state.workspaces = [workspace]
        created = state.create_workspace_execution_run(
            workspace["id"],
            {"kind": "agent_debug", "summary": "手动调试"},
        )
        listing = state.list_workspace_execution_runs(workspace["id"])
        self.assertEqual(listing["workspace_id"], workspace["id"])
        self.assertEqual(len(listing["runs"]), 1)
        self.assertEqual(listing["runs"][0]["kind"], "agent_debug")
        self.assertEqual(created["run"]["summary"], "手动调试")


class WorkspaceCockpitNextActionTests(unittest.TestCase):
    def test_workspace_public_payload_includes_cockpit_next_action(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "repo",
                "repo_url": "https://github.com/example/demo.git",
                "workspace_dir": "/tmp/demo-cockpit",
                "run_command": "python train.py",
            },
        )
        state.workspaces = [workspace]
        payload = state.workspace_public_payload(workspace)
        cockpit = payload["automation"]["cockpit"]
        next_action = cockpit["next_action"]
        self.assertIn("primary", next_action)
        self.assertIn("action", next_action["primary"])
        self.assertTrue(next_action["primary"]["label"])
        self.assertIn("status", next_action)
        self.assertIsInstance(cockpit["chain"], list)
        self.assertGreater(len(cockpit["chain"]), 0)
        self.assertIn("config_ready", cockpit["chain"][0])

    def test_workspace_next_action_prefers_discovery_for_fresh_instance(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "repo",
                "repo_url": "https://github.com/example/fresh.git",
                "workspace_dir": "/tmp/fresh-cockpit",
            },
        )
        state.workspaces = [workspace]
        payload = state.workspace_public_payload(workspace)
        next_action = payload["automation"]["cockpit"]["next_action"]
        self.assertIn(
            next_action["primary"]["action"],
            {"run-workspace-discovery", "advance-workspace-automation", "apply-workspace-automation"},
        )

    def test_workspace_next_action_reports_running_when_jobs_active(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "repo",
                "repo_url": "https://github.com/example/running.git",
                "workspace_dir": "/tmp/running-cockpit",
            },
        )
        workspace_id = workspace["id"]
        state.workspaces = [workspace]
        state.jobs = [
            {
                "id": "job-active-1",
                "name": "repo.clone",
                "status": "running",
                "metadata": {"workspace_id": workspace_id, "node_kind": "repo.clone"},
            },
        ]
        payload = state.workspace_public_payload(workspace)
        next_action = payload["automation"]["cockpit"]["next_action"]
        self.assertEqual(next_action["status"], "running")
        self.assertEqual(next_action["primary"]["action"], "open-last-workspace-log")

    def test_derive_workspace_cockpit_chain_includes_job_and_error(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "repo",
                "repo_url": "https://github.com/example/chain.git",
                "workspace_dir": "/tmp/chain-cockpit",
            },
        )
        node_id = workspace["nodes"][1]["id"]
        workspace_id = workspace["id"]
        state.workspaces = [workspace]
        state.jobs = [
            {
                "id": "job-chain-1",
                "name": "repo.clone",
                "status": "failed",
                "error": "clone failed: permission denied",
                "metadata": {"workspace_id": workspace_id, "node_id": node_id},
            },
        ]
        payload = state.workspace_public_payload(workspace)
        chain = payload["automation"]["cockpit"]["chain"]
        matched = next((item for item in chain if item.get("id") == node_id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["job_id"], "job-chain-1")
        self.assertEqual(matched["job_status"], "failed")
        self.assertIn("permission denied", matched["error"])

    def test_workspace_cockpit_payload_matches_public_automation(self) -> None:
        state = make_registry_state()
        workspace = TotalControlState.create_workspace(
            state,
            {
                "source_type": "idea",
                "idea_text": "复现某个 baseline",
                "brief": "demo idea",
            },
        )
        state.workspaces = [workspace]
        public = state.workspace_public_payload(workspace)
        cockpit_payload = state.workspace_cockpit_payload(workspace["id"])
        self.assertEqual(cockpit_payload["workspace_id"], workspace["id"])
        self.assertEqual(
            cockpit_payload["cockpit"],
            public["automation"]["cockpit"],
        )


if __name__ == "__main__":
    unittest.main()
