"""Workspace application state — split by concern."""

from __future__ import annotations

from .crud import CrudMixin
from .defaults import DefaultsMixin
from .runs import RunsMixin
from .discovery import DiscoveryMixin
from .automation import AutomationMixin
from .debug import DebugMixin
from .nodes import NodesMixin
from .agents import AgentsMixin
from .workflow import WorkflowMixin
from .chat import ChatMixin

class WorkspacesMixin(CrudMixin, DefaultsMixin, RunsMixin, DiscoveryMixin, AutomationMixin, DebugMixin, NodesMixin, AgentsMixin, WorkflowMixin, ChatMixin):
    """Composed workspace state mixin."""

__all__ = ["WorkspacesMixin"]
