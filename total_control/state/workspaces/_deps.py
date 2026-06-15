"""Shared imports for workspace state mixins."""

from __future__ import annotations

import copy
import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from ...agent_executor import AgentExecutor, AgentExecutionResult
from ...agent_runtime import (
    agent_run_is_active,
    cancel_agent_run,
    register_agent_cancel,
    release_agent_cancel,
)
from ...config import AppConfig, ServerConfig, load_config, save_user_overlay
from ...constants import *  # noqa: F403
from ...utils import *  # noqa: F403
from ...infra.checks import run_server_checks, stop_server_process
from ...infra.shell import *  # noqa: F403
from ...infra.web_terminal import WebTerminal
from ...llm_client import ChatMessage, LLMClient, LLMResponse
from ...orchestration.input_mapping import (
    apply_final_answer_output,
    build_agent_node_input_text,
    collect_agent_step_output,
    resolve_mapped_inputs,
    validate_agent_output,
)
from ...orchestration.node_runner import AGENT_EXECUTABLE_KINDS, resolve_node_executor_mode, run_agent_node
from ...orchestration.types import ExecutionRunContext, StepResult
from ...orchestration.workflow_runner import WorkflowRunner, WorkflowRunnerCallbacks, run_workflow_sequence
from ...preset_matrix import (
    DEFAULT_DATA_ROOT as PRESET_DEFAULT_DATA_ROOT,
    DEFAULT_PROJECT_DIR as PRESET_DEFAULT_PROJECT_DIR,
    DEFAULT_REMOTE_PROJECT_DIR as PRESET_DEFAULT_REMOTE_PROJECT_DIR,
    generate_experiments as generate_preset_experiments,
    make_session_name as make_preset_session_name,
)
from ...tools.registry import create_workspace_tool_executor, summarize_mapped_inputs
from ...workspace.schema import *  # noqa: F403
from ...workspace.execution import *  # noqa: F403
from ...workspace.automation import *  # noqa: F403
from ...workspace.cockpit import *  # noqa: F403
from ...workspace.errors import WorkspaceWorkflowReadinessError
