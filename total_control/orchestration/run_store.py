"""Transactional execution evidence. This store never advances a workflow or runs a Job."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator

from .types import RunPlan
from ..infra.report_files import report_file_descriptor
from ..utils import now_iso


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class RunConflictError(ValueError):
    """An existing execution identity cannot be reused for different work."""


class RunBusyError(RunConflictError):
    """Another local coordinator holds this run's operating-system lock."""


class RunStoreError(RuntimeError):
    """Persistent evidence is unavailable; never interpret this as an empty new store."""


class RunStore:
    SCHEMA_VERSION = 1
    TERMINAL = frozenset({"done", "failed", "stopped", "skipped"})

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_dir = path.parent / (path.stem + "-locks")
        with self._db(write=True) as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version == 0 and not tables:
                db.execute("""CREATE TABLE runs(
                    run_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, request_id TEXT,
                    request_hash TEXT NOT NULL, plan_json TEXT NOT NULL, plan_hash TEXT NOT NULL,
                    record_json TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
                    UNIQUE(workspace_id, request_id))""")
                db.execute("""CREATE TABLE attempts(
                    run_id TEXT NOT NULL REFERENCES runs(run_id), step_id TEXT NOT NULL,
                    attempt_no INTEGER NOT NULL, status TEXT NOT NULL, inputs_json TEXT NOT NULL,
                    result_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, PRIMARY KEY(run_id,step_id,attempt_no))""")
                db.execute("""CREATE TABLE submissions(
                    submit_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, step_id TEXT NOT NULL,
                    attempt_no INTEGER NOT NULL, payload_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
                    state TEXT NOT NULL, external_ref TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(run_id,step_id,attempt_no) REFERENCES attempts(run_id,step_id,attempt_no))""")
                db.execute("PRAGMA user_version=1")
            elif version != self.SCHEMA_VERSION:
                raise RunStoreError("unsupported execution store schema; existing file preserved")
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RunStoreError("execution store integrity check failed; existing file preserved")

    @contextmanager
    def _db(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=5)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            db.commit()
        except (sqlite3.DatabaseError, json.JSONDecodeError) as exc:
            raise RunStoreError("execution store unreadable or unavailable; existing file preserved") from exc
        finally:
            if db is not None:
                db.close()

    @staticmethod
    def validate_plan(plan: dict[str, Any]) -> None:
        if not isinstance(plan, dict):
            raise ValueError("execution plan must be an object")
        steps = plan.get("steps")
        if plan.get("schema_version") != 1 or not plan.get("run_id") or not plan.get("workspace_id"):
            raise ValueError("invalid execution plan identity or schema")
        if not isinstance(plan.get("workspace_snapshot"), dict) or not isinstance(plan.get("package_snapshot"), dict):
            raise ValueError("execution plan snapshots must be objects")
        if not isinstance(steps, list) or not steps:
            raise ValueError("execution plan must have steps")
        ids = []
        for index, step in enumerate(steps):
            step_id = step.get("step_id", "") if isinstance(step, dict) else ""
            if not isinstance(step_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", step_id):
                raise ValueError("invalid execution step identity")
            if step.get("index") != index or step.get("executor") not in {"job", "agent", "skip"}:
                raise ValueError("invalid execution step order or executor")
            if not isinstance(step.get("node"), dict) or step["node"].get("id") != step_id:
                raise ValueError("execution step snapshot identity mismatch")
            ids.append(step_id)
        if len(ids) != len(set(ids)) or all(step["executor"] == "skip" for step in steps):
            raise ValueError("execution plan requires unique identities and a runnable step")

    def create(self, plan: RunPlan, *, request_id: str = "", request_hash: str = "", summary: str = "") -> tuple[str, bool]:
        snapshot = asdict(plan)
        self.validate_plan(snapshot)
        encoded = canonical_json(snapshot)
        plan_hash = content_hash(snapshot)
        with self._db(write=True) as db:
            existing = db.execute("SELECT * FROM runs WHERE run_id=?", (plan.run_id,)).fetchone()
            if existing:
                if existing["plan_hash"] != plan_hash:
                    raise RunConflictError("run identity reused with a different plan")
                return plan.run_id, False
            if request_id:
                existing = db.execute("SELECT * FROM runs WHERE workspace_id=? AND request_id=?",
                                      (plan.workspace_id, request_id)).fetchone()
                if existing:
                    if existing["request_hash"] != request_hash:
                        raise RunConflictError("request_id reused with different arguments")
                    return existing["run_id"], False
            record = {"kind": "reproduction", "trigger": "user", "summary": summary,
                      "created_at": now_iso(), "updated_at": now_iso()}
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)",
                       (plan.run_id, plan.workspace_id, request_id or None, request_hash,
                        encoded, plan_hash, canonical_json(record), ""))
        return plan.run_id, True

    def find_request(self, workspace_id: str, request_id: str, request_hash: str) -> str:
        if not request_id:
            return ""
        with self._db() as db:
            row = db.execute("SELECT run_id,request_hash FROM runs WHERE workspace_id=? AND request_id=?",
                             (workspace_id, request_id)).fetchone()
            if row and row["request_hash"] != request_hash:
                raise RunConflictError("request_id reused with different arguments")
            return row["run_id"] if row else ""

    def run_ids(self, workspace_id: str) -> list[str]:
        with self._db() as db:
            return [row[0] for row in db.execute("SELECT run_id FROM runs WHERE workspace_id=?", (workspace_id,))]

    def read(self, run_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                raise ValueError("execution plan not found")
            plan = json.loads(row["plan_json"])
            try:
                self.validate_plan(plan)
            except ValueError as exc:
                raise RunStoreError("invalid persisted execution plan; existing record preserved") from exc
            if content_hash(plan) != row["plan_hash"] or plan["run_id"] != run_id or plan["workspace_id"] != row["workspace_id"]:
                raise RunStoreError("execution plan integrity mismatch; existing record preserved")
            attempts = [{**dict(item), "result": json.loads(item["result_json"]),
                         "inputs": json.loads(item["inputs_json"])} for item in db.execute(
                             "SELECT * FROM attempts WHERE run_id=? ORDER BY step_id,attempt_no", (run_id,))]
            if any(not isinstance(item["result"], dict) or not isinstance(item["inputs"], dict) for item in attempts):
                raise RunStoreError("invalid attempt evidence; existing record preserved")
            submissions = [dict(item) for item in db.execute("SELECT * FROM submissions WHERE run_id=?", (run_id,))]
            for intent in submissions:
                if content_hash(json.loads(intent["payload_json"])) != intent["payload_hash"]:
                    raise RunStoreError("submission payload integrity mismatch; existing record preserved")
            record = json.loads(row["record_json"])
            if not isinstance(record, dict):
                raise RunStoreError("invalid run metadata; existing record preserved")
            return {"plan": plan, "plan_hash": row["plan_hash"], "record": record,
                    "attempts": attempts, "submissions": submissions, "error": row["error"]}

    def begin_attempt(self, run_id: str, step_id: str, *, inputs: dict[str, Any], retry: bool = False) -> int:
        record = self.read(run_id)
        if not any(step["step_id"] == step_id for step in record["plan"]["steps"]):
            raise ValueError("step is outside the immutable plan")
        with self._db(write=True) as db:
            last = db.execute("SELECT * FROM attempts WHERE run_id=? AND step_id=? ORDER BY attempt_no DESC LIMIT 1",
                              (run_id, step_id)).fetchone()
            if last and not retry:
                if last["inputs_json"] != canonical_json(inputs):
                    raise RunConflictError("attempt identity reused with different input provenance")
                return last["attempt_no"]
            if last and last["status"] not in self.TERMINAL:
                raise RunConflictError("active attempt must be reconciled before retry")
            number = last["attempt_no"] + 1 if last else 1
            timestamp = now_iso()
            db.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)",
                       (run_id, step_id, number, "running", canonical_json(inputs), "{}", timestamp, timestamp))
            return number

    def record_result(self, run_id: str, step_id: str, attempt_no: int, result: dict[str, Any]) -> None:
        encoded = canonical_json(result)
        if result.get("node_id", step_id) != step_id:
            raise RunConflictError("attempt result belongs to another step")
        status = result["status"]
        if status not in {"pending", "running", "queued", "reconciling", "blocked", *self.TERMINAL}:
            raise ValueError("invalid attempt result status")
        with self._db(write=True) as db:
            row = db.execute("SELECT * FROM attempts WHERE run_id=? AND step_id=? AND attempt_no=?",
                             (run_id, step_id, attempt_no)).fetchone()
            if not row:
                raise ValueError("attempt not found")
            if row["result_json"] == encoded:
                return
            if row["status"] in self.TERMINAL:
                raise RunConflictError("terminal attempt evidence cannot be replaced; append a retry")
            db.execute("UPDATE attempts SET status=?,result_json=?,updated_at=? WHERE run_id=? AND step_id=? AND attempt_no=?",
                       (status, encoded, now_iso(), run_id, step_id, attempt_no))

    def claim_agent_invocation(self, run_id: str, step_id: str, attempt_no: int, execution_id: str) -> bool:
        """Persist intent before a model call. An occupied claim is never replay permission."""
        result = {"node_id": step_id, "status": "running", "executor": "agent",
                  "agent_execution_id": execution_id, "invocation_state": "claimed"}
        with self._db(write=True) as db:
            return db.execute(
                "UPDATE attempts SET result_json=?,updated_at=? "
                "WHERE run_id=? AND step_id=? AND attempt_no=? AND status='running' AND result_json='{}'",
                (canonical_json(result), now_iso(), run_id, step_id, attempt_no),
            ).rowcount == 1

    def prepare_report_file(self, run_id: str, step_id: str, attempt_no: int,
                            descriptor: dict[str, Any]) -> dict[str, Any]:
        """Record file intent after the successful answer is durable, before writing."""
        with self._db(write=True) as db:
            attempt = db.execute("SELECT status,result_json FROM attempts WHERE run_id=? AND step_id=? AND attempt_no=?",
                                 (run_id, step_id, attempt_no)).fetchone()
            if not attempt or attempt["status"] != "done":
                raise RunConflictError("report file requires a persisted successful attempt")
            row = db.execute("SELECT record_json,workspace_id FROM runs WHERE run_id=?", (run_id,)).fetchone()
            result = json.loads(attempt["result_json"])
            output = result.get("output_value", {})
            expected = report_file_descriptor(row["workspace_id"], run_id, step_id, f"a{attempt_no}", output.get("content"))
            if (descriptor != expected or output.get("storage") != "inline-answer"
                    or result.get("validation", {}).get("status") != "ok"):
                raise RunConflictError("report file differs from persisted validated answer")
            record = json.loads(row[0])
            receipts = record.setdefault("report_files", {})
            key = f"{step_id}/a{attempt_no}"
            receipt = receipts.get(key)
            if receipt:
                if any(receipt.get(k) != v for k, v in descriptor.items()):
                    raise RunConflictError("report file identity reused for a different answer")
                return receipt
            receipt = {**descriptor, "status": "prepared", "created_at": now_iso(),
                       "verified_at": "", "error": ""}
            receipts[key] = receipt
            db.execute("UPDATE runs SET record_json=? WHERE run_id=?", (canonical_json(record), run_id))
            return receipt

    def finish_report_file(self, run_id: str, step_id: str, attempt_no: int, *, error: str = "") -> None:
        with self._db(write=True) as db:
            row = db.execute("SELECT record_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
            record = json.loads(row[0])
            receipt = record["report_files"][f"{step_id}/a{attempt_no}"]
            if receipt["status"] != "prepared":
                return  # Completed delivery evidence is never overwritten by a wakeup.
            receipt.update(status="failed" if error else "verified", error=error,
                           verified_at="" if error else now_iso())
            record["updated_at"] = now_iso()
            db.execute("UPDATE runs SET record_json=? WHERE run_id=?", (canonical_json(record), run_id))

    def prepare_submission(self, run_id: str, step_id: str, attempt_no: int, payload: dict[str, Any]) -> dict[str, Any]:
        key = f"{run_id}/{step_id}/a{attempt_no}/job"
        digest = content_hash(payload)
        with self._db(write=True) as db:
            row = db.execute("SELECT * FROM submissions WHERE submit_key=?", (key,)).fetchone()
            if row and row["payload_hash"] != digest:
                raise RunConflictError("submission key reused with a different payload")
            if not row:
                db.execute("INSERT INTO submissions(submit_key,run_id,step_id,attempt_no,payload_hash,payload_json,state) VALUES(?,?,?,?,?,?,?)",
                           (key, run_id, step_id, attempt_no, digest, canonical_json(payload), "prepared"))
                row = db.execute("SELECT * FROM submissions WHERE submit_key=?", (key,)).fetchone()
            return dict(row)

    def claim_submission(self, key: str) -> bool:
        with self._db(write=True) as db:
            return db.execute("UPDATE submissions SET state='submitting' WHERE submit_key=? AND state='prepared'", (key,)).rowcount == 1

    def bind_submission(self, key: str, job_id: str) -> None:
        if not job_id:
            raise ValueError("external Job reference required")
        with self._db(write=True) as db:
            row = db.execute("SELECT * FROM submissions WHERE submit_key=?", (key,)).fetchone()
            if not row or (row["external_ref"] and row["external_ref"] != job_id):
                raise RunConflictError("submission reference conflict")
            if row["external_ref"] == job_id and row["state"] == "submitted" and not row["error"]:
                return
            db.execute("UPDATE submissions SET state='submitted',external_ref=?,error='' WHERE submit_key=?", (job_id, key))

    def reconcile_submission(self, key: str, error: str) -> None:
        with self._db(write=True) as db:
            db.execute("UPDATE submissions SET state='reconciling',error=? WHERE submit_key=?", (error, key))

    def fail_run(self, run_id: str, error: str) -> None:
        with self._db(write=True) as db:
            db.execute("UPDATE runs SET error=? WHERE run_id=?", (error, run_id))

    def update_record(self, run_id: str, *, summary: str = "", package_snapshot: dict[str, Any] | None = None) -> None:
        if not summary and package_snapshot is None:
            return
        with self._db(write=True) as db:
            row = db.execute("SELECT record_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                raise ValueError("execution plan not found")
            record = json.loads(row[0])
            if summary:
                record["summary"] = summary
            if package_snapshot is not None:
                record["package_snapshot"] = package_snapshot
            record["updated_at"] = now_iso()
            db.execute("UPDATE runs SET record_json=? WHERE run_id=?", (canonical_json(record), run_id))

    @contextmanager
    def run_lock(self, run_id: str) -> Iterator[None]:
        """Single-host exclusion without lease expiry during a slow external call."""
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        target = self.lock_dir / (hashlib.sha256(run_id.encode()).hexdigest() + ".lock")
        with target.open("a+b") as handle:
            try:
                if os.name == "nt":
                    import msvcrt
                    if handle.seek(0, 2) == 0:
                        handle.write(b"0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RunBusyError("run is already being submitted or resumed") from exc
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle, fcntl.LOCK_UN)
