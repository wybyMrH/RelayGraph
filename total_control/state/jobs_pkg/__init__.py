"""Job scheduling and execution — split by concern."""

from __future__ import annotations

from .queue import QueueJobsMixin
from .crud import CrudJobsMixin
from .paths import PathsJobsMixin
from .presets import PresetsJobsMixin
from .task_plans import TaskPlansJobsMixin
from .execution import ExecutionJobsMixin

class JobsMixin(QueueJobsMixin, CrudJobsMixin, PathsJobsMixin, PresetsJobsMixin, TaskPlansJobsMixin, ExecutionJobsMixin):
    """Composed job mixin; methods live in domain sub-mixins."""

__all__ = ["JobsMixin"]
