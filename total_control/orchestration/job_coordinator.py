"""One persistent graph for a Job and an optional, current-result report Agent."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
import sqlite3
from typing import Any, Callable, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .run_store import RunStore, RunStoreError


JOB_ENGINE_VERSION = "langgraph-job/n03b2b"
REPORT_ENGINE_VERSION = "langgraph-job-report/n03b2c1"
AGENT_CHILD_JOB_ENGINE_VERSION = "langgraph-agent-child-job/n04"
GRAPH_ENGINE_VERSIONS = frozenset({JOB_ENGINE_VERSION, REPORT_ENGINE_VERSION, AGENT_CHILD_JOB_ENGINE_VERSION})


class JobGraphState(TypedDict):
    run_id: str
    plan_hash: str
    job_id: str
    child_job_id: str
    observation: dict[str, Any]
    phase: str


@dataclass(frozen=True)
class JobCoordinatorCallbacks:
    submit: Callable[[str], str]
    observe: Callable[[str, str], dict[str, Any]]
    record: Callable[[str, dict[str, Any]], None]
    report: Callable[[str], dict[str, Any]] | None = None
    start_agent: Callable[[str], str] | None = None
    resume_agent: Callable[[str], dict[str, Any]] | None = None
    fail_agent: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None


class JobCoordinator:
    def __init__(self, store: RunStore, callbacks: JobCoordinatorCallbacks):
        self.store = store
        self.callbacks = callbacks
        self.path = store.path.with_name(store.path.stem + "-checkpoints.sqlite3")

    def _submit(self, state: JobGraphState) -> dict[str, Any]:
        # Re-entry uses the frozen payload and the existing durable submission key.
        if self.store.read(state["run_id"])["plan"]["engine_version"] == AGENT_CHILD_JOB_ENGINE_VERSION:
            if self.callbacks.start_agent is None:
                raise RunStoreError("child Agent callback unavailable; retained state requires reconciliation")
            return {"child_job_id": self.callbacks.start_agent(state["run_id"]), "phase": "child"}
        return {"job_id": self.callbacks.submit(state["run_id"])}

    def _observe(self, state: JobGraphState) -> dict[str, Any]:
        if self.store.read(state["run_id"])["plan"]["engine_version"] == AGENT_CHILD_JOB_ENGINE_VERSION:
            result = self.callbacks.observe(state["run_id"], state.get("child_job_id") or state.get("job_id", ""))
            if result == state.get("observation"):
                return {"observation": state.get("observation", {})}
            self.callbacks.record(state["run_id"], result)
            return {"observation": result}
        result = self.callbacks.observe(state["run_id"], state["job_id"])
        if result == state.get("observation"):
            return {"observation": state.get("observation", {})}
        self.callbacks.record(state["run_id"], result)
        return {"observation": result}

    @staticmethod
    def _wait(state: JobGraphState) -> dict[str, Any]:
        # The hint never carries completion facts. Resume always observes the Job again.
        interrupt({"kind": "job", "job_id": state.get("child_job_id") or state["job_id"]})
        return {}

    def _report(self, state: JobGraphState) -> dict[str, Any]:
        if self.callbacks.report is None:
            raise RunStoreError("report callback unavailable; retained state requires reconciliation")
        self.callbacks.report(state["run_id"])
        return {}  # The attempt ledger owns the answer; no duplicate checkpoint body.

    def _resume_agent(self, state: JobGraphState) -> dict[str, Any]:
        if self.callbacks.resume_agent is None:
            raise RunStoreError("child Agent resume callback unavailable; retained state requires reconciliation")
        self.callbacks.resume_agent(state["run_id"])
        return {"phase": "resumed"}

    def _fail_agent(self, state: JobGraphState) -> dict[str, Any]:
        if self.callbacks.fail_agent is None:
            raise RunStoreError("child Agent failure callback unavailable; retained state requires reconciliation")
        self.callbacks.fail_agent(state["run_id"], state.get("observation") or {})
        return {"phase": "failed"}

    def _after_observe(self, state: JobGraphState) -> str:
        if self.store.read(state["run_id"])["plan"]["engine_version"] == AGENT_CHILD_JOB_ENGINE_VERSION:
            status = state["observation"].get("status")
            if status == "done":
                return "resume_agent"
            if status in self.store.TERMINAL:
                return "fail_agent"
            if status in {"blocked", "reconciling", "unknown"}:
                return "fail_agent"
            return "wait"
        if state["observation"]["status"] not in self.store.TERMINAL:
            return "wait"
        plan = self.store.read(state["run_id"])["plan"]
        return "report" if plan["engine_version"] == REPORT_ENGINE_VERSION else END

    def _graph(self, saver: SqliteSaver):
        builder = StateGraph(JobGraphState)
        builder.add_node("submit", self._submit)
        builder.add_node("observe", self._observe)
        builder.add_node("wait", self._wait)
        builder.add_node("report", self._report)
        builder.add_node("resume_agent", self._resume_agent)
        builder.add_node("fail_agent", self._fail_agent)
        builder.add_edge(START, "submit")
        builder.add_edge("submit", "observe")
        builder.add_conditional_edges("observe", self._after_observe)
        builder.add_edge("wait", "observe")
        builder.add_edge("report", END)
        builder.add_edge("resume_agent", END)
        builder.add_edge("fail_agent", END)
        return builder.compile(checkpointer=saver)

    def _validate_checkpoint(self) -> None:
        if not self.path.exists():
            return
        # Check existing files read-only before saver setup can write schema/WAL.
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RunStoreError("checkpoint integrity check failed; existing file preserved")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"checkpoints", "writes"} <= tables:
                raise RunStoreError("checkpoint schema unavailable; existing file preserved")

    def advance(self, run_id: str) -> bool:
        """One scheduler wake; return whether graph/evidence may have changed."""
        with self.store.run_lock(run_id):
            evidence = self.store.read(run_id)
            if evidence["plan"]["engine_version"] not in GRAPH_ENGINE_VERSIONS:
                return False  # Historical runners are never replayed as a new graph.
            config = {"configurable": {"thread_id": run_id}}
            self._validate_checkpoint()
            with SqliteSaver.from_conn_string(str(self.path)) as saver:
                saver.conn.execute("PRAGMA synchronous=FULL")
                graph = self._graph(saver)
                snapshot = graph.get_state(config)
                if snapshot.values and (snapshot.values.get("run_id") != run_id
                                        or snapshot.values.get("plan_hash") != evidence["plan_hash"]):
                    raise RunStoreError("checkpoint identity differs from frozen plan; existing record preserved")
                if not snapshot.values:
                    # A plan may be accepted before the scheduler's first checkpoint.
                    # Submission re-entry is safe only through the durable Job adapter.
                    graph.invoke({"run_id": run_id, "plan_hash": evidence["plan_hash"],
                                  "job_id": "", "child_job_id": "", "observation": {}, "phase": ""},
                                 config, durability="sync")
                elif not snapshot.next and not snapshot.tasks:
                    return False
                elif snapshot.tasks and any(task.interrupts for task in snapshot.tasks):
                    graph.invoke(Command(resume=True), config, durability="sync")
                else:
                    # Completed task writes may hide snapshot.next before the next
                    # checkpoint commits. Resume to settle those writes/branches too.
                    graph.invoke(None, config, durability="sync")
            return True
