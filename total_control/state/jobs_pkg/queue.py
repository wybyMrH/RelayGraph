"""Auto-split from jobs.py — queue."""

from __future__ import annotations

from ._deps import *  # noqa: F403


class QueueJobsMixin:
    def reorder_job(self, job_id: str, direction: str) -> dict[str, Any]:
        job_id = str(job_id or "").strip()
        move = str(direction or "").strip().lower()
        if move not in {"top", "up", "down"}:
            raise ValueError("direction must be top, up or down")
        with self.lock:
            job = next((item for item in self.jobs if item.get("id") == job_id), None)
            if not job:
                raise ValueError("job not found")
            if str(job.get("status") or "") not in {"queued", "blocked"}:
                raise ValueError("只能调整等待中的任务顺序")
            waiting = sorted(
                [item for item in self.jobs if str(item.get("status") or "") in {"queued", "blocked"}],
                key=self.queue_sort_key,
            )
            index = next((idx for idx, item in enumerate(waiting) if item.get("id") == job_id), -1)
            if index < 0:
                raise ValueError("job not found")
            if move == "top":
                target_index = 0
            elif move == "up":
                target_index = max(0, index - 1)
            else:
                target_index = min(len(waiting) - 1, index + 1)
            if target_index != index:
                moved = waiting.pop(index)
                waiting.insert(target_index, moved)
                for order, item in enumerate(waiting, 1):
                    item["queue_rank"] = order
            self.next_queue_rank = len(waiting) + 1
            queue_position = next(
                (idx + 1 for idx, item in enumerate(waiting) if item.get("id") == job_id),
                0,
            )
        self.save_jobs()
        return {
            "job": job,
            "queue_position": queue_position,
            "total_waiting": len(waiting),
        }
