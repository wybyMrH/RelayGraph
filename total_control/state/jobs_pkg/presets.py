"""Auto-split from jobs.py — presets."""

from __future__ import annotations

from ._deps import *  # noqa: F403


class PresetsJobsMixin:
    def preset_command(self, experiment: Any, *, data_root: str, smoke: bool = False) -> str:
        parts = [
            "python",
            "smoke_test_single.py" if smoke else "train.py",
            "--arch",
            experiment.arch,
            "--ablation",
            experiment.ablation,
        ]
        if smoke:
            parts.extend(["--dino", experiment.dino, "--bs", str(experiment.batch_size), "--gpu_id", "0"])
        else:
            parts.extend(
                [
                    "--data_name",
                    experiment.dataset,
                    "--batchsize",
                    str(experiment.batch_size),
                    "--gpu_id",
                    "0",
                    "--data_root",
                    data_root,
                ]
            )
            if experiment.dino != "none":
                parts.extend(["--dino_variant", experiment.dino])
        return " ".join(shlex.quote(part) for part in parts)


    def preset_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        preview = self.task_plan_preview({**payload, "template": "preset"})
        experiments = []
        for item in preview.get("items", []):
            metadata = dict(item.get("metadata") or {})
            experiments.append(
                {
                    "estimated_mib": metadata.get("estimated_mib", item.get("estimated_mib", 0)),
                    "dataset": metadata.get("dataset", ""),
                    "arch": metadata.get("arch", ""),
                    "ablation": metadata.get("ablation", ""),
                    "dino": metadata.get("dino", ""),
                    "batch_size": metadata.get("batch_size", ""),
                    "priority": metadata.get("priority", ""),
                    "session": item.get("session", ""),
                    "command": item.get("command", ""),
                    "profile_command": item.get("profile_command", ""),
                }
            )
        return {
            **preview,
            "datasets": preview.get("metadata", {}).get("datasets", ""),
            "experiments": experiments,
        }


    def create_preset_jobs(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.create_task_plan_jobs({**payload, "template": "preset"})
        return {
            **result,
            "smoke_jobs": result.get("profile_jobs", 0),
            "train_jobs": result.get("batch_jobs", 0),
        }
