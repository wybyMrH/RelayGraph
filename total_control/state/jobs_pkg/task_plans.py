"""Auto-split from jobs.py — task_plans."""

from __future__ import annotations

from ._deps import *  # noqa: F403


class TaskPlansJobsMixin:
    def task_plan_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        template = str(payload.get("template") or "custom").strip().lower() or "custom"
        if template == "preset":
            datasets = str(payload.get("datasets") or "dataset_a").strip() or "dataset_a"
            experiments = generate_preset_experiments(datasets)
            limit = safe_int(payload.get("limit"), 0)
            if limit > 0:
                experiments = experiments[:limit]
            data_root = str(payload.get("data_root") or PRESET_DEFAULT_DATA_ROOT).strip()
            user_mem = safe_int(payload.get("max_memory_mib") or payload.get("min_free_mib"), 0)
            items: list[dict[str, Any]] = []
            for order, experiment in enumerate(experiments, 1):
                session = make_preset_session_name(
                    experiment.dataset, experiment.arch, experiment.ablation, experiment.dino
                )
                metadata = {
                    "template": "preset",
                    "order": order,
                    "dataset": experiment.dataset,
                    "arch": experiment.arch,
                    "ablation": experiment.ablation,
                    "dino": experiment.dino,
                    "batch_size": experiment.batch_size,
                    "priority": experiment.priority,
                    "estimated_mib": experiment.estimated_mib,
                }
                items.append(
                    {
                        "name": f"Preset {session}",
                        "session": session,
                        "profile_session": f"profile_{session[:40]}",
                        "command": self.preset_command(experiment, data_root=data_root, smoke=False),
                        "profile_command": self.preset_command(experiment, data_root=data_root, smoke=True),
                        "estimated_mib": experiment.estimated_mib,
                        "min_free_mib": user_mem or experiment.estimated_mib,
                        "profile_key": experiment.key,
                        "metadata": metadata,
                    }
                )
            return items

        command_template = str(payload.get("command_template") or payload.get("command") or "").strip()
        if not command_template:
            raise ValueError("command_template is required")
        name_template = str(payload.get("name_template") or payload.get("name") or "批量任务 {index}").strip()
        session_template = str(payload.get("session_template") or name_template).strip()
        profile_template = str(payload.get("profile_command_template") or "").strip()
        params = parse_param_matrix(payload.get("params") or payload.get("params_text") or "")
        default_min_free = safe_int(payload.get("min_free_mib") or payload.get("max_memory_mib"), self.config.idle_min_free_mib)
        items = []
        for row in params:
            name = render_task_template(name_template, row) or f"批量任务 {row['index']}"
            session = safe_id(render_task_template(session_template, row) or name)
            metadata = {
                "template": "custom",
                "order": row["index"],
                "params": row,
            }
            items.append(
                {
                    "name": name,
                    "session": f"tc_{session[:45]}",
                    "profile_session": f"profile_{session[:40]}",
                    "command": render_task_template(command_template, row).strip(),
                    "profile_command": render_task_template(profile_template, row).strip(),
                    "estimated_mib": default_min_free,
                    "min_free_mib": default_min_free,
                    "profile_key": session,
                    "metadata": metadata,
                }
            )
        return items


    def task_plan_preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        template = str(payload.get("template") or "custom").strip().lower() or "custom"
        items = self.task_plan_items(payload)
        profile_first = bool(payload.get("profile_first", payload.get("smoke_first", False)))
        return {
            "template": template,
            "count": len(items),
            "profile_first": profile_first,
            "items": items,
            "metadata": {
                "datasets": str(payload.get("datasets") or "dataset_a").strip() or "dataset_a"
                if template == "preset"
                else "",
            },
        }


    def create_task_plan_jobs(self, payload: dict[str, Any]) -> dict[str, Any]:
        preview = self.task_plan_preview(payload)
        items = preview["items"]
        if not items:
            raise ValueError("no task items selected")

        server_id = str(payload.get("server_id") or "auto").strip() or "auto"
        if server_id != "auto" and not self.server_by_id(server_id):
            raise ValueError(f"unknown server: {server_id}")
        candidate_server_ids = [
            str(item)
            for item in payload.get("candidate_server_ids", [])
            if str(item)
        ]
        requested_gpu = payload.get("gpu_index", "auto")
        gpu_index: int | str = "auto" if requested_gpu in (None, "", "auto") else safe_int(requested_gpu)
        env_name = str(payload.get("env_name") or "").strip()
        template = str(preview["template"])
        local_project = str(
            payload.get("local_project_dir")
            or payload.get("cwd_local")
            or (PRESET_DEFAULT_PROJECT_DIR if template == "preset" else payload.get("cwd") or "")
        ).strip()
        remote_project = str(
            payload.get("remote_project_dir")
            or payload.get("cwd_remote")
            or (PRESET_DEFAULT_REMOTE_PROJECT_DIR if template == "preset" else payload.get("cwd") or "")
        ).strip()
        cwd = str(payload.get("cwd") or "").strip()
        max_gpu_util = safe_int(payload.get("max_gpu_util"), self.config.idle_max_gpu_util)
        profile_first = bool(payload.get("profile_first", payload.get("smoke_first", False)))
        safety = max(1.0, safe_float(payload.get("profile_safety", payload.get("smoke_safety", 1.2)), 1.2))
        profile_free_override = safe_int(
            payload.get("profile_min_free_mib", payload.get("smoke_min_free_mib")),
            0,
        )
        dry_run = bool(payload.get("dry_run", False))

        now_prefix = datetime.now().strftime("%Y%m%d-%H%M%S-")
        batch_jobs: list[dict[str, Any]] = []
        profile_jobs: list[dict[str, Any]] = []
        for item in items:
            train_id = now_prefix + uuid.uuid4().hex[:8]
            item_min_free = safe_int(item.get("min_free_mib"), self.config.idle_min_free_mib)
            can_profile = profile_first and bool(item.get("profile_command"))
            metadata = dict(item.get("metadata") or {})
            metadata.update(
                {
                    "template": template,
                    "estimated_mib": safe_int(item.get("estimated_mib"), item_min_free),
                    "profile_safety": safety,
                }
            )
            batch_job = {
                "id": train_id,
                "name": str(item.get("name") or f"批量任务 {train_id}"),
                "server_id": server_id,
                "requested_server_id": server_id,
                "candidate_server_ids": candidate_server_ids,
                "gpu_index": gpu_index,
                "requested_gpu_index": gpu_index,
                "command": str(item.get("command") or ""),
                "cwd": cwd,
                "cwd_local": local_project,
                "cwd_remote": remote_project,
                "env_name": env_name,
                "min_free_mib": item_min_free,
                "max_gpu_util": max_gpu_util,
                "wait_for_idle": True,
                "status": "blocked" if can_profile else "queued",
                "session": str(item.get("session") or make_session_name(train_id)),
                "kind": "profiled-batch-item" if can_profile else "batch-item",
                "target_job_ids": [],
                "profile_key": str(item.get("profile_key") or ""),
                "profile_measured_mib": 0,
                "created_at": now_iso(),
                "started_at": "",
                "finished_at": "",
                "error": "等待 profile/smoke 完成" if can_profile else "",
                "queue_rank": 0,
                "log_path": str(local_log_path(server_id, train_id).resolve()),
                "remote_log_path": "",
                "metadata": metadata,
            }
            batch_jobs.append(batch_job)

            if can_profile:
                profile_id = now_prefix + uuid.uuid4().hex[:8]
                profile_metadata = dict(metadata)
                profile_metadata.update({"parser": "peak_allocated_mib"})
                profile_jobs.append(
                    {
                        "id": profile_id,
                        "name": f"Profile {batch_job['name']}",
                        "server_id": server_id,
                        "requested_server_id": server_id,
                        "candidate_server_ids": candidate_server_ids,
                        "gpu_index": gpu_index,
                        "requested_gpu_index": gpu_index,
                        "command": str(item.get("profile_command") or ""),
                        "cwd": cwd,
                        "cwd_local": local_project,
                        "cwd_remote": remote_project,
                        "env_name": env_name,
                        "min_free_mib": profile_free_override or item_min_free,
                        "max_gpu_util": max_gpu_util,
                        "wait_for_idle": True,
                        "status": "queued",
                        "session": str(item.get("profile_session") or f"profile_{batch_job['session'][:40]}"),
                        "kind": "profile",
                        "target_job_ids": [train_id],
                        "profile_key": str(item.get("profile_key") or ""),
                        "profile_measured_mib": 0,
                        "created_at": now_iso(),
                        "started_at": "",
                        "finished_at": "",
                        "error": "",
                        "queue_rank": 0,
                        "log_path": str(local_log_path(server_id, profile_id).resolve()),
                        "remote_log_path": "",
                        "metadata": profile_metadata,
                    }
                )

        new_jobs = [*profile_jobs, *batch_jobs] if profile_jobs else batch_jobs
        if not dry_run:
            with self.lock:
                self.reserve_queue_ranks(new_jobs)
                self.jobs = [*new_jobs, *self.jobs]
            self.save_jobs()
        return {
            "template": template,
            "created": len(new_jobs),
            "profile_jobs": len(profile_jobs),
            "batch_jobs": len(batch_jobs),
            "jobs": new_jobs,
            "dry_run": dry_run,
        }
