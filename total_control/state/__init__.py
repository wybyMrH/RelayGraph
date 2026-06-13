"""Application state split by domain — TotalControlState composes mixins."""

from __future__ import annotations

from .base import BaseMixin
from .files import FilesMixin
from .monitoring import MonitoringMixin
from .persistence import PersistenceMixin
from .registry import RegistryMixin
from .workspaces import WorkspacesMixin
from .jobs import JobsMixin
from .servers import ServersMixin
from .terminals import TerminalsMixin
from .scheduler import SchedulerMixin

class TotalControlState(BaseMixin, FilesMixin, MonitoringMixin, PersistenceMixin, RegistryMixin, WorkspacesMixin, JobsMixin, ServersMixin, TerminalsMixin, SchedulerMixin):
    """Composed application state; methods live in domain mixins."""


__all__ = ["TotalControlState"]