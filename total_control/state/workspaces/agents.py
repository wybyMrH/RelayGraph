"""Workspace state — agents operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class AgentsMixin:
    def cancel_agent_execution(self, execution_id: str) -> dict[str, Any]:
        """Signal a running agent execution to abort on its next iteration."""
        active = cancel_agent_run(str(execution_id or "").strip())
        return {
            "agent_execution_id": str(execution_id or "").strip(),
            "cancelled": active,
            "active": agent_run_is_active(str(execution_id or "").strip()),
        }

    def workspace_tool_runtime(self, workspace: dict[str, Any]) -> dict[str, Any]:
        return {
            "submit_job": lambda tool_id, arguments, context: self.submit_workspace_tool_job(
                workspace,
                tool_id,
                arguments,
                context,
            ),
            "bind_gpu": lambda arguments, context: self.bind_workspace_tool_gpu_allocation(
                workspace,
                arguments,
                context,
            ),
            "control_job": lambda tool_id, arguments, context: self.control_workspace_tool_job(
                workspace,
                tool_id,
                arguments,
                context,
            ),
        }


    def workspace_tool_command_block_reason(self, tool_id: str, command: str) -> str:
        tool = str(tool_id or "").strip()
        if tool != "host.exec":
            return ""
        text = str(command or "").strip()
        if not text:
            return ""
        lowered = text.lower()
        compact = re.sub(r"\s+", " ", lowered)
        destructive_terms = {
            "mkfs": "格式化文件系统",
            "wipefs": "清除文件系统签名",
            "fdisk": "修改磁盘分区",
            "parted": "修改磁盘分区",
            "shutdown": "关闭主机",
            "poweroff": "关闭主机",
            "halt": "关闭主机",
            "reboot": "重启主机",
        }
        for term, label in destructive_terms.items():
            if re.search(rf"(^|[;&|]\s*)(sudo\s+)?{re.escape(term)}(\s|$)", compact):
                return f"host.exec 默认拒绝{label}命令；请改用人工确认后的配置化工作流。"
        if re.search(r"(^|[;&|]\s*)(sudo\s+)?(systemctl\s+)?(reboot|poweroff|halt)(\s|$)", compact):
            return "host.exec 默认拒绝重启或关机命令；请改用人工确认后的配置化工作流。"
        if re.search(r"(^|[;&|]\s*)init\s+[06](\s|$)", compact):
            return "host.exec 默认拒绝切换到关机/重启运行级别。"
        if re.search(r"dd\s+[^;&|]*(^|\s)of=/dev/", compact):
            return "host.exec 默认拒绝直接写入块设备。"
        if ":(){:|:&};:" in compact:
            return "host.exec 默认拒绝 fork bomb。"
        rm_pattern = (
            r"(^|[;&|]\s*)(sudo\s+)?rm\s+"
            r"[^;&|]*-[^\s;&|]*r[^\s;&|]*f?[^\s;&|]*"
            r"[^;&|]*(\s+--no-preserve-root)?\s+"
            r"([\"']?(/|~|\$home|\${home})(/|\*|\s|[\"']|$))"
        )
        if re.search(rm_pattern, compact):
            return "host.exec 默认拒绝删除根目录、HOME 或其整体内容。"
        if re.search(r"(^|[;&|]\s*)(sudo\s+)?chmod\s+-r\s+777\s+/", compact):
            return "host.exec 默认拒绝递归放开根目录权限。"
        if re.search(r"(^|[;&|]\s*)(sudo\s+)?chown\s+-r\s+[^;&|]+\s+/", compact):
            return "host.exec 默认拒绝递归改写根目录属主。"
        diagnostic_reason = self.workspace_tool_host_exec_diagnostic_block_reason(text)
        if diagnostic_reason:
            return diagnostic_reason
        return ""


    def workspace_tool_host_exec_diagnostic_block_reason(self, command: str) -> str:
        text = str(command or "").strip()
        if not text:
            return ""
        if re.search(r"[\n\r;&|<>`]", text) or "$(" in text:
            return "host.exec 仅允许单条只读诊断命令；复杂 shell、管道或重定向请放到配置化 job.run。"
        try:
            parts = shlex.split(text, posix=True)
        except ValueError as exc:
            return f"host.exec 命令无法安全解析：{exc}"
        if not parts:
            return ""

        executable = os.path.basename(str(parts[0] or "").strip()).lower()
        args = [str(item or "").strip() for item in parts[1:]]
        if executable in {"sudo", "su", "sh", "bash", "zsh", "fish", "powershell", "pwsh"}:
            return "host.exec 不允许通过提权或 shell 包装器执行；请改用人工确认后的配置化工作流。"
        if executable in {"python", "python3", "python.exe", "python3.exe", "node", "perl", "ruby", "php"}:
            if self.workspace_tool_host_exec_version_only(executable, args):
                return ""
            return "host.exec 的解释器命令只允许版本探测；脚本执行请走配置化 job.run。"

        sensitive_pattern = re.compile(
            r"(^|/)(\.ssh|\.gnupg|\.aws|\.azure|\.config/gcloud)(/|$)|"
            r"(^|/)(id_rsa|id_ed25519|known_hosts|authorized_keys|\.master_key)(\s|$)|"
            r"(api[_-]?key|access[_-]?token|secret|password)",
            re.IGNORECASE,
        )
        for arg in parts:
            if sensitive_pattern.search(str(arg or "")):
                return "host.exec 诊断命令不允许读取或枚举密钥、令牌、SSH 配置等敏感路径。"

        allowed_simple = {
            "pwd",
            "whoami",
            "id",
            "hostname",
            "uname",
            "date",
            "uptime",
            "df",
            "du",
            "free",
            "nvidia-smi",
            "ls",
            "stat",
            "wc",
            "ps",
            "pgrep",
            "lscpu",
            "lsmem",
            "lsblk",
            "lspci",
            "ip",
            "ss",
            "netstat",
            "mount",
            "printenv",
            "which",
            "whereis",
        }
        if executable in allowed_simple:
            return self.workspace_tool_host_exec_option_block_reason(executable, args)
        if executable == "top":
            if self.workspace_tool_host_exec_top_is_bounded(args):
                return ""
            return "host.exec 只允许有界 top 诊断，例如 top -b -n 1。"
        if executable == "systemctl":
            return self.workspace_tool_host_exec_systemctl_block_reason(args)
        if executable == "git":
            return self.workspace_tool_host_exec_git_block_reason(args)
        if executable == "conda":
            return self.workspace_tool_host_exec_conda_block_reason(args)
        if executable in {"pip", "pip3"}:
            if self.workspace_tool_host_exec_version_only(executable, args):
                return ""
            return "host.exec 的 pip 命令只允许版本探测；安装/卸载请走配置化 env.prepare。"
        if executable == "docker":
            return self.workspace_tool_host_exec_docker_block_reason(args)
        return "host.exec 仅允许主机/环境诊断命令；运行程序、训练或环境变更请使用配置化 job.run/env.prepare。"


    def workspace_tool_host_exec_option_block_reason(self, executable: str, args: list[str]) -> str:
        lowered = [arg.lower() for arg in args]
        blocked_tokens = {
            "-delete",
            "-exec",
            "-execdir",
            "-ok",
            "-okdir",
            "--remove",
            "--delete",
            "--in-place",
            "--follow",
        }
        for arg in lowered:
            if arg in blocked_tokens or arg.startswith("--output="):
                return f"host.exec 诊断命令不允许 {arg} 这类会修改、持续跟随或写出文件的参数。"
        if executable == "date":
            if any(arg in {"-s", "--set"} or arg.startswith("--set=") for arg in lowered):
                return "host.exec 诊断命令不允许修改系统时间。"
        if executable == "hostname":
            allowed = {"", "-i", "-I".lower(), "-f", "--fqdn", "-s", "--short", "--all-ip-addresses"}
            if any(arg not in allowed for arg in lowered):
                return "host.exec 诊断命令不允许修改主机名。"
        if executable == "mount":
            if any(arg and not arg.startswith("-") for arg in lowered):
                return "host.exec 的 mount 只允许查看挂载状态，不允许挂载/卸载路径。"
        if executable == "ip":
            mutating = {"set", "add", "del", "delete", "flush", "replace", "change", "append", "save", "restore", "monitor"}
            if any(arg in mutating for arg in lowered):
                return "host.exec 的 ip 只允许网络状态查询，不允许修改网络配置或持续监听。"
        if executable == "nvidia-smi":
            mutating_prefixes = (
                "-pm",
                "--persistence-mode",
                "-pl",
                "--power-limit",
                "--gpu-reset",
                "--reset-gpu",
                "-r",
                "-rac",
                "-gom",
                "-c",
                "--compute-mode",
            )
            if any(any(arg == prefix or arg.startswith(prefix + "=") for prefix in mutating_prefixes) for arg in lowered):
                return "host.exec 的 nvidia-smi 只允许查询，不允许修改 GPU 状态。"
        if executable in {"tail"} and any(arg in {"-f", "--follow"} for arg in lowered):
            return "host.exec 诊断命令不允许持续跟随日志；请使用日志接口或受控 job 输出。"
        if executable == "printenv":
            secret_terms = ("key", "token", "secret", "password", "credential")
            for arg in lowered:
                if any(term in arg for term in secret_terms):
                    return "host.exec 诊断命令不允许直接打印疑似密钥或令牌环境变量。"
        return ""


    def workspace_tool_host_exec_top_is_bounded(self, args: list[str]) -> bool:
        lowered = [arg.lower() for arg in args]
        has_batch = any(arg == "-b" or arg.startswith("-b") for arg in lowered)
        if not has_batch:
            return False
        for index, arg in enumerate(lowered):
            if arg == "-n" and index + 1 < len(lowered) and lowered[index + 1] == "1":
                return True
            if arg.startswith("-n") and arg[2:] == "1":
                return True
        return False


    def workspace_tool_host_exec_systemctl_block_reason(self, args: list[str]) -> str:
        if not args:
            return "host.exec 的 systemctl 只允许状态查询子命令。"
        subcommand = args[0].lower()
        allowed = {"status", "is-active", "is-enabled", "list-units", "list-unit-files", "show"}
        if subcommand not in allowed:
            return "host.exec 的 systemctl 只允许状态查询；启动、停止或重载服务请走人工确认后的工作流。"
        return self.workspace_tool_host_exec_option_block_reason("systemctl", args)


    def workspace_tool_host_exec_git_block_reason(self, args: list[str]) -> str:
        if not args:
            return "host.exec 的 git 只允许只读查询子命令。"
        subcommand = args[0].lower()
        allowed = {"status", "diff", "log", "show", "branch", "rev-parse", "remote", "describe"}
        if subcommand not in allowed:
            return "host.exec 的 git 只允许只读查询；clone/pull/checkout 等变更请走配置化工具或工作流。"
        return self.workspace_tool_host_exec_option_block_reason("git", args)


    def workspace_tool_host_exec_conda_block_reason(self, args: list[str]) -> str:
        if not args:
            return "host.exec 的 conda 只允许环境查询子命令。"
        subcommand = args[0].lower()
        if subcommand in {"--version", "-v"}:
            return ""
        if subcommand in {"info", "list"}:
            return self.workspace_tool_host_exec_option_block_reason("conda", args)
        if subcommand == "env" and len(args) >= 2 and args[1].lower() in {"list", "export"}:
            return self.workspace_tool_host_exec_option_block_reason("conda", args)
        return "host.exec 的 conda 只允许 info/list/env list/env export；创建或安装请走配置化 env.prepare。"


    def workspace_tool_host_exec_docker_block_reason(self, args: list[str]) -> str:
        if not args:
            return "host.exec 的 docker 只允许状态查询子命令。"
        subcommand = args[0].lower()
        allowed = {"ps", "images", "info", "version"}
        if subcommand == "stats":
            if "--no-stream" in {arg.lower() for arg in args[1:]}:
                return ""
            return "host.exec 的 docker stats 必须使用 --no-stream。"
        if subcommand not in allowed:
            return "host.exec 的 docker 只允许状态查询；启动/停止容器请走配置化工作流。"
        return self.workspace_tool_host_exec_option_block_reason("docker", args)


    def workspace_tool_host_exec_version_only(self, executable: str, args: list[str]) -> bool:
        _ = executable
        return len(args) == 1 and args[0].lower() in {"--version", "-v"}


    def workspace_tool_runtime_node_kind(self, tool_id: str) -> str:
        tool = str(tool_id or "").strip()
        if tool == "repo.clone":
            return "repo.clone"
        if tool in {"env.prepare", "env.create"}:
            return "env.prepare"
        return "run.command"


    def workspace_tool_env_create_command(
        self,
        args: dict[str, Any],
        config: dict[str, Any],
        workspace: dict[str, Any],
    ) -> str:
        command = str(args.get("command") or args.get("setup_command") or "").strip()
        if command:
            return command
        workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
        env_name = str(args.get("env_name") or config.get("env_name") or workspace_env.get("name") or "").strip()
        if not env_name:
            return ""
        manager = str(args.get("env_manager") or config.get("env_manager") or workspace_env.get("manager") or "conda").strip().lower()
        python_version = str(args.get("python_version") or config.get("python_version") or workspace_env.get("python") or "").strip()
        if manager == "venv":
            workspace_dir = str(args.get("workspace_dir") or config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            target = env_name if env_name.startswith(("/", "~", ".")) else os.path.join(workspace_dir or ".", env_name)
            return "python3 -m venv " + shlex.quote(target)
        command_parts = ["conda", "create", "-y", "-n", shlex.quote(env_name)]
        if python_version:
            command_parts.append("python=" + shlex.quote(python_version))
        return " ".join(command_parts)


    def workspace_tool_observe_options(self, args: dict[str, Any]) -> dict[str, Any]:
        data = args if isinstance(args, dict) else {}
        requested = bool(
            data.get("wait_for_completion")
            or data.get("wait_until_complete")
            or data.get("observe")
            or data.get("observe_job")
        )
        seconds = safe_float(data.get("observe_seconds"), 0.0)
        if seconds <= 0:
            seconds = safe_float(data.get("wait_timeout_seconds"), 0.0)
        if seconds <= 0 and requested:
            seconds = 30.0
        seconds = min(max(seconds, 0.0), 300.0)
        poll_interval = safe_float(data.get("poll_interval_seconds"), 0.5)
        poll_interval = min(max(poll_interval, 0.05), 5.0)
        log_tail_lines = safe_int(data.get("log_tail_lines"), 120)
        log_tail_lines = min(max(log_tail_lines, 0), 2000)
        return {
            "enabled": requested or seconds > 0,
            "seconds": seconds,
            "poll_interval": poll_interval,
            "log_tail_lines": log_tail_lines,
        }


    def workspace_tool_job_snapshot(self, job_id: str) -> dict[str, Any] | None:
        target = str(job_id or "").strip()
        if not target:
            return None
        with self.lock:
            job = next((item for item in self.jobs if str(item.get("id") or "").strip() == target), None)
            return copy.deepcopy(job) if isinstance(job, dict) else None


    def workspace_tool_run_snapshot(self, workspace_id: str, run_id: str) -> dict[str, Any] | None:
        workspace_id = str(workspace_id or "").strip()
        run_id = str(run_id or "").strip()
        if not workspace_id or not run_id:
            return None
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            runs = workspace.get("runs") if isinstance(workspace, dict) and isinstance(workspace.get("runs"), list) else []
            run = next((item for item in runs if str(item.get("id") or "").strip() == run_id), None)
            return copy.deepcopy(run) if isinstance(run, dict) else None


    def observe_workspace_tool_job(
        self,
        *,
        workspace_id: str,
        job_id: str,
        run_id: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        job_id = str(job_id or "").strip()
        run_id = str(run_id or "").strip()
        seconds = safe_float(options.get("seconds"), 0.0)
        poll_interval = safe_float(options.get("poll_interval"), 0.5)
        log_tail_lines = safe_int(options.get("log_tail_lines"), 120)
        terminal_statuses = {"done", "failed", "stopped"}
        started = time.monotonic()
        deadline = started + seconds
        timed_out = False
        last_job = self.workspace_tool_job_snapshot(job_id)

        while True:
            if last_job and str(last_job.get("status") or "").strip() in terminal_statuses:
                break
            if time.monotonic() > deadline:
                timed_out = True
                break
            try:
                self.refresh_status()
                self.monitor_jobs()
            except Exception as exc:  # noqa: BLE001 - observation reports scheduler issues in-band.
                return {
                    "observed": True,
                    "status": "error",
                    "runtime_status": "error",
                    "job_status": str((last_job or {}).get("status") or "").strip(),
                    "error": f"job observation failed: {exc}",
                    "observe_seconds": round(time.monotonic() - started, 3),
                }
            last_job = self.workspace_tool_job_snapshot(job_id)
            if last_job and str(last_job.get("status") or "").strip() in terminal_statuses:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            wait_for = min(max(poll_interval, 0.05), remaining)
            stop_event = getattr(self, "stop_event", None)
            if stop_event is not None and stop_event.wait(wait_for):
                timed_out = True
                break
            if stop_event is None:
                time.sleep(wait_for)

        if workspace_id:
            self.sync_workspace_execution_runs_from_jobs(workspace_id)
        last_job = self.workspace_tool_job_snapshot(job_id) or last_job or {}
        job_status = str(last_job.get("status") or "").strip()
        result_status = job_status if job_status in terminal_statuses else "timeout" if timed_out else job_status or "unknown"
        log_tail = ""
        log_error = ""
        if log_tail_lines > 0 and last_job:
            try:
                if hasattr(self, "job_log_payload"):
                    payload = self.job_log_payload(last_job, lines=log_tail_lines)
                    log_tail = str(payload.get("log") or "")
                else:
                    log_tail = str(self.tail_log(last_job, lines=log_tail_lines))
            except Exception as exc:  # noqa: BLE001 - log tail should not hide job status.
                log_error = str(exc)
        if len(log_tail) > 12000:
            log_tail = log_tail[-12000:]
        observed_run = self.workspace_tool_run_snapshot(workspace_id, run_id)
        payload: dict[str, Any] = {
            "observed": True,
            "status": result_status,
            "runtime_status": result_status,
            "job_status": job_status,
            "timed_out": bool(timed_out),
            "observe_seconds": round(time.monotonic() - started, 3),
            "job": copy.deepcopy(last_job) if isinstance(last_job, dict) else {},
            "job_id": job_id,
        }
        if run_id:
            payload["run_id"] = run_id
        if observed_run:
            payload["run"] = observed_run
        if log_tail:
            payload["log_tail"] = log_tail
            payload["log_line_count"] = len(log_tail.splitlines())
        if log_error:
            payload["log_error"] = log_error
        if result_status in {"failed", "stopped"}:
            payload["error"] = str(last_job.get("error") or f"job {result_status}").strip()
        elif result_status == "timeout":
            payload["message"] = "观察窗口已结束，任务仍在队列或运行中；后续状态会继续通过 run/job 事件同步。"
        elif result_status == "done":
            payload["message"] = "任务已完成，观察结果和日志尾部已返回。"
        return payload


    def submit_workspace_tool_job(
        self,
        workspace: dict[str, Any],
        tool_id: str,
        arguments: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        workspace_id = str(workspace.get("id") or "").strip()
        tool = str(tool_id or "").strip()
        args = arguments if isinstance(arguments, dict) else {}
        if not workspace_id:
            return {"status": "error", "tool": tool, "error": "workspace_id is required"}
        command = str(args.get("command") or args.get("cmd") or args.get("run_command") or args.get("setup_command") or "").strip()
        run_config = context.node_config("run.command") if context else {}
        preferred_node_kind = self.workspace_tool_runtime_node_kind(tool)
        if not command and tool == "job.run":
            command = str(run_config.get("run_command") or "").strip()
        if not command and tool == "env.prepare" and context:
            command = str(context.node_config("env.prepare").get("setup_command") or "").strip()
        if not command and tool == "env.create":
            command = self.workspace_tool_env_create_command(
                args,
                context.node_config("env.prepare") if context else {},
                workspace,
            )
        if tool == "repo.clone":
            source = context.source_payload() if context else {}
            repo_config = context.node_config("repo.clone") if context else {}
            repo_urls = source.get("repo_urls") if isinstance(source.get("repo_urls"), list) else []
            repo_url = str(args.get("repo_url") or repo_config.get("repo_url") or (repo_urls[0] if repo_urls else "")).strip()
            workspace_dir = str(args.get("workspace_dir") or args.get("cwd") or repo_config.get("workspace_dir") or source.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            if not repo_url or not workspace_dir:
                return {
                    "status": "blocked",
                    "tool": tool,
                    "controlled": True,
                    "runtime_control": "workspace_job_queue",
                    "error": "repo_url and workspace_dir are required",
                }
        elif not command:
            return {"status": "blocked", "tool": tool, "error": "command is required"}
        block_reason = self.workspace_tool_command_block_reason(tool, command)
        if block_reason:
            return {
                "status": "blocked",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_queue",
                "command": command,
                "error": block_reason,
            }

        nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
        requested_node_id = str(args.get("node_id") or "").strip()
        node = next(
            (
                item for item in nodes
                if isinstance(item, dict)
                and requested_node_id
                and str(item.get("id") or "").strip() == requested_node_id
            ),
            None,
        )
        if node is None:
            node = next(
                (
                    item for item in nodes
                    if isinstance(item, dict) and str(item.get("kind") or "").strip() == preferred_node_kind
                ),
                None,
            )
        if node is None and preferred_node_kind != "run.command":
            node = {
                "id": safe_id(f"{preferred_node_kind}-agent-runtime"),
                "kind": preferred_node_kind,
                "title": WORKSPACE_NODE_LIBRARY.get(preferred_node_kind, {}).get("title") or "Agent 受控任务",
                "config": {},
                "handler": {"mode": "system", "name": "Agent Runtime", "output_key": "runtime_result"},
            }
        if node is None:
            node = {
                "id": safe_id(f"{tool}-agent-runtime"),
                "kind": "run.command",
                "title": "Agent 受控任务",
                "config": {},
                "handler": {"mode": "system", "name": "Agent Runtime", "output_key": "run_result"},
            }
        node_copy = copy.deepcopy(node)
        config = node_copy.get("config") if isinstance(node_copy.get("config"), dict) else {}
        config["server_id"] = str(args.get("server_id") or config.get("server_id") or run_config.get("server_id") or "auto").strip() or "auto"
        config["workspace_dir"] = str(args.get("cwd") or args.get("workspace_dir") or config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
        if tool == "repo.clone":
            source = context.source_payload() if context else {}
            repo_config = context.node_config("repo.clone") if context else {}
            repo_urls = source.get("repo_urls") if isinstance(source.get("repo_urls"), list) else []
            config["repo_url"] = str(args.get("repo_url") or repo_config.get("repo_url") or (repo_urls[0] if repo_urls else "")).strip()
            config["repo_ref"] = str(args.get("repo_ref") or args.get("branch") or repo_config.get("repo_ref") or "").strip()
            config["gpu_policy"] = "cpu"
            config["gpu_index"] = "none"
        elif tool in {"env.prepare", "env.create"}:
            config["setup_command"] = command
            if args.get("env_name") is not None:
                config["env_name"] = str(args.get("env_name") or "").strip()
            if args.get("env_manager") is not None:
                config["env_manager"] = str(args.get("env_manager") or "").strip()
            if args.get("python_version") is not None:
                config["python_version"] = str(args.get("python_version") or "").strip()
            config["gpu_policy"] = "cpu"
            config["gpu_index"] = "none"
        else:
            config["run_command"] = command
        if tool == "host.exec":
            config["gpu_policy"] = "cpu"
            config["gpu_index"] = "none"
        elif tool not in {"repo.clone", "env.prepare", "env.create"}:
            if args.get("gpu_policy") is not None:
                config["gpu_policy"] = str(args.get("gpu_policy") or "").strip()
            elif not str(config.get("gpu_policy") or "").strip() and str(run_config.get("gpu_policy") or "").strip():
                config["gpu_policy"] = str(run_config.get("gpu_policy") or "").strip()
            if args.get("gpu_index") is not None:
                config["gpu_index"] = str(args.get("gpu_index") or "").strip()
            elif not str(config.get("gpu_index") or "").strip() and str(run_config.get("gpu_index") or "").strip():
                config["gpu_index"] = str(run_config.get("gpu_index") or "").strip()
        if args.get("env_name") is not None:
            config["env_name"] = str(args.get("env_name") or "").strip()
        if args.get("min_free_memory_gib") is not None:
            config["min_free_memory_gib"] = str(args.get("min_free_memory_gib") or "").strip()
        node_copy["config"] = config

        try:
            job_payload = self.workspace_node_job_payload(workspace, node_copy)
            job_payload["name"] = str(
                args.get("name")
                or f"{workspace.get('name') or workspace_id} · {tool}"
            )
            if command and tool != "repo.clone":
                job_payload["command"] = command
                job_payload["command_display"] = command
            if "wait_for_idle" in args:
                job_payload["wait_for_idle"] = bool(args.get("wait_for_idle"))
            if tool == "host.exec":
                job_payload["gpu_index"] = "none"
                metadata = job_payload.get("metadata") if isinstance(job_payload.get("metadata"), dict) else {}
                metadata["execution_mode"] = "cpu"
                runtime_binding = metadata.get("runtime_binding") if isinstance(metadata.get("runtime_binding"), dict) else {}
                runtime_binding["gpu_policy"] = "cpu"
                runtime_binding["gpu_index"] = "none"
                runtime_binding["execution_mode"] = "cpu"
                metadata["runtime_binding"] = runtime_binding
                job_payload["metadata"] = metadata
            observe_options = self.workspace_tool_observe_options(args)
            metadata = job_payload.get("metadata") if isinstance(job_payload.get("metadata"), dict) else {}
            metadata.update(
                {
                    "tool_id": tool,
                    "agent_runtime_tool": True,
                    "runtime_control": "workspace_job_queue",
                    "submitted_by": "agent_tool",
                }
            )
            job_payload["metadata"] = metadata
            job = self.create_job(job_payload, publish_events=False)
            run = self.register_workspace_execution_run(
                workspace_id,
                kind="node",
                trigger="agent_tool",
                summary=f"Agent 工具任务 · {tool}",
                jobs=[job],
            )
            with self.lock:
                persisted = self.workspace_by_id(workspace_id)
                if persisted and isinstance(persisted.get("runs"), list):
                    workspace["runs"] = copy.deepcopy(persisted["runs"])
            result = {
                "status": "submitted",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_queue",
                "runtime_side_effect": "workspace_job",
                "observed": False,
                "job": copy.deepcopy(job),
                "job_id": str(job.get("id") or "").strip(),
                "run": copy.deepcopy(run),
                "run_id": str(run.get("id") or "").strip(),
                "message": "任务已通过受控 workspace job 队列提交。",
            }
            if observe_options.get("enabled") and safe_float(observe_options.get("seconds"), 0.0) > 0:
                observation = self.observe_workspace_tool_job(
                    workspace_id=workspace_id,
                    job_id=str(job.get("id") or "").strip(),
                    run_id=str(run.get("id") or "").strip(),
                    options=observe_options,
                )
                result.update(observation)
                result["tool"] = tool
                result["controlled"] = True
                result["runtime_control"] = "workspace_job_queue"
                result["runtime_side_effect"] = "workspace_job"
            return result
        except Exception as exc:  # noqa: BLE001 - tools report errors inside the agent loop.
            return {"status": "error", "tool": tool, "controlled": True, "error": str(exc)}


    def bind_workspace_tool_gpu_allocation(
        self,
        workspace: dict[str, Any],
        arguments: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        args = arguments if isinstance(arguments, dict) else {}
        selected = args.get("selected") if isinstance(args.get("selected"), dict) else None
        if not selected and context:
            min_free_mib = safe_int(args.get("min_free_mib"), 0)
            server_id = str(args.get("server_id") or "").strip()
            selected = next((item for item in context.gpu_candidates(min_free_mib=min_free_mib, server_id=server_id) if item.get("eligible")), None)
        if not selected:
            return {
                "status": "blocked",
                "tool": "gpu.allocate",
                "controlled": True,
                "error": "没有满足条件的 GPU 候选。",
            }
        server_id = str(selected.get("server_id") or "").strip()
        gpu_index = str(selected.get("gpu_index") if selected.get("gpu_index") is not None else "").strip()
        min_free_mib = safe_int(args.get("min_free_mib"), 0)
        min_free_gib = round(min_free_mib / 1024, 2) if min_free_mib else 0
        return {
            "status": "planned",
            "tool": "gpu.allocate",
            "controlled": True,
            "runtime_control": "scheduler_plan",
            "runtime_side_effect": "none",
            "plan_only": True,
            "selected": copy.deepcopy(selected),
            "recommended_binding": {
                "server_id": server_id,
                "gpu_policy": "auto",
                "gpu_index": gpu_index,
                "min_free_memory_gib": str(min_free_gib) if min_free_gib else "",
            },
            "persisted": False,
            "message": "已生成 GPU 候选和绑定建议；未修改配置。需要持久化时请在配置中心应用调度目标，实际执行仍走 job 队列。",
        }


    def control_workspace_tool_job(
        self,
        workspace: dict[str, Any],
        tool_id: str,
        arguments: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        _ = context
        workspace_id = str(workspace.get("id") or "").strip()
        tool = str(tool_id or "").strip()
        args = arguments if isinstance(arguments, dict) else {}
        if not workspace_id:
            return {"status": "error", "tool": tool, "error": "workspace_id is required"}

        requested_job_id = str(args.get("job_id") or args.get("id") or "").strip()
        with self.lock:
            workspace_jobs = []
            for job in self.jobs:
                metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
                if str(metadata.get("workspace_id") or "").strip() == workspace_id:
                    workspace_jobs.append(job)
            if not requested_job_id and bool(args.get("latest")) and workspace_jobs:
                workspace_jobs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
                requested_job_id = str(workspace_jobs[0].get("id") or "").strip()
            job = next((item for item in workspace_jobs if str(item.get("id") or "").strip() == requested_job_id), None)

        if not requested_job_id:
            return {"status": "blocked", "tool": tool, "controlled": True, "error": "job_id is required"}
        if not job:
            return {
                "status": "blocked",
                "tool": tool,
                "controlled": True,
                "error": "job not found in this workspace",
                "job_id": requested_job_id,
            }

        if tool == "job.stop":
            current_status = str(job.get("status") or "").strip()
            if current_status in {"done", "failed", "stopped"}:
                return {
                    "status": "noop",
                    "tool": tool,
                    "controlled": True,
                    "runtime_control": "workspace_job_control",
                    "job": copy.deepcopy(job),
                    "job_id": requested_job_id,
                    "message": f"任务已是 {current_status}，无需停止。",
                }
            stopped = self.stop_job(requested_job_id)
            return {
                "status": "stopped",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_control",
                "job": copy.deepcopy(stopped),
                "job_id": requested_job_id,
                "message": "任务已通过受控 job 控制停止。",
            }

        if tool == "job.reorder":
            direction = str(args.get("direction") or args.get("move") or "top").strip().lower()
            try:
                result = self.reorder_job(requested_job_id, direction)
            except ValueError as exc:
                return {
                    "status": "blocked",
                    "tool": tool,
                    "controlled": True,
                    "runtime_control": "workspace_job_control",
                    "job_id": requested_job_id,
                    "error": str(exc),
                }
            changed_job = result.get("job") if isinstance(result.get("job"), dict) else job
            self.publish_job_event(changed_job, "job.updated")
            return {
                "status": "reordered",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_control",
                "job": copy.deepcopy(changed_job),
                "job_id": requested_job_id,
                "queue_position": result.get("queue_position"),
                "total_waiting": result.get("total_waiting"),
                "message": "任务队列顺序已通过受控 job 控制更新。",
            }

        return {"status": "error", "tool": tool, "controlled": True, "error": "unsupported job control tool"}


    def _execute_agent_on_mutable_workspace(
        self,
        workspace: dict[str, Any],
        agent: dict[str, Any],
        *,
        input_text: str,
        requested_node_kind: str = "",
        execute_llm: bool = True,
        node: dict[str, Any] | None = None,
        mapped_inputs: dict[str, Any] | None = None,
        output_key: str = "",
        output_format: str = "",
        max_iterations: int | None = None,
        timeout_seconds: float | None = None,
        run_id: str = "",
    ) -> dict[str, Any]:
        workspace_id = str(workspace.get("id") or "").strip()
        execution_run_id = str(run_id or "").strip()
        tools = normalize_workspace_tools(workspace.get("tools"), existing=workspace.get("tools"))
        model_config = workspace.get("model") if isinstance(workspace.get("model"), dict) else {}
        routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
        workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()
        agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
        effective_profile_id = workspace_profile_id
        if routing_mode == "agent_override" and agent_profile_id:
            effective_profile_id = agent_profile_id

        if not execute_llm or not input_text:
            return {
                "success": False,
                "error": "agent execution requires input text",
                "final_answer": "",
            }
        if not effective_profile_id:
            return {
                "success": False,
                "error": "No provider profile configured for this workspace/agent",
                "final_answer": "",
            }
        profile = self.provider_profile_by_id(effective_profile_id)
        if not profile:
            return {
                "success": False,
                "error": "Provider profile not found",
                "final_answer": "",
            }
        from ..registry import provider_profile_health

        health = provider_profile_health(profile)
        if not health.get("ready"):
            missing_fields = [
                str(item or "").strip()
                for item in (health.get("missing_fields") if isinstance(health.get("missing_fields"), list) else [])
                if str(item or "").strip()
            ]
            detail = ", ".join(missing_fields) if missing_fields else "profile is not ready"
            return {
                "success": False,
                "error": f"Provider profile is not ready: {detail}",
                "final_answer": "",
            }

        tool_map = {t.get("id"): t for t in tools if isinstance(t, dict) and t.get("id")}
        allowed_tool_ids = [
            tid for tid in parse_tag_list(agent.get("tools", []))
            if tid in tool_map
        ]
        allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]
        llm_client = LLMClient(profile)
        tool_executor = create_workspace_tool_executor(
            workspace,
            statuses=copy.deepcopy(self.statuses),
            jobs=copy.deepcopy(self.jobs),
            runtime=self.workspace_tool_runtime(workspace),
        )
        agent_config = dict(agent)
        if max_iterations is not None:
            agent_config = {**agent_config, "max_iterations": max_iterations}
        execution_id = make_agent_execution_id()
        cancel_check = register_agent_cancel(execution_id)
        node_kind = str(requested_node_kind or (node or {}).get("kind") or "").strip()
        trace_events: list[dict[str, Any]] = []

        def on_agent_event(event_type: str, event_payload: dict[str, Any]) -> None:
            if isinstance(event_payload, dict) and event_payload:
                trace_events.append(copy.deepcopy(event_payload))
            self.publish_event(
                event_type,
                workspace_id=workspace_id,
                run_id=execution_run_id,
                agent_execution_id=execution_id,
                payload={
                    **(event_payload if isinstance(event_payload, dict) else {}),
                    "node_id": str((node or {}).get("id") or "").strip(),
                    "node_kind": node_kind,
                    "agent_id": str(agent.get("id") or "").strip(),
                    "chat": False,
                },
            )

        def on_agent_step(step: Any) -> None:
            step_payload = step.to_dict() if hasattr(step, "to_dict") else step
            self.publish_event(
                "agent.step.created",
                workspace_id=workspace_id,
                run_id=execution_run_id,
                agent_execution_id=execution_id,
                payload={
                    "step": copy.deepcopy(step_payload) if isinstance(step_payload, dict) else {},
                    "node_id": str((node or {}).get("id") or "").strip(),
                    "node_kind": node_kind,
                    "agent_id": str(agent.get("id") or "").strip(),
                },
            )

        def on_agent_delta(delta: str, accumulated: str) -> None:
            if not str(accumulated or "").strip():
                return
            self.publish_event(
                "agent.message.delta",
                workspace_id=workspace_id,
                run_id=execution_run_id,
                agent_execution_id=execution_id,
                payload={
                    "delta": str(delta or ""),
                    "accumulated": str(accumulated or ""),
                    "node_id": str((node or {}).get("id") or "").strip(),
                    "node_kind": node_kind,
                    "agent_id": str(agent.get("id") or "").strip(),
                    "chat": False,
                },
            )

        executor = AgentExecutor(
            agent=agent_config,
            llm_client=llm_client,
            tools=allowed_tools,
            tool_executor=tool_executor,
            step_callback=on_agent_step,
            token_callback=on_agent_delta,
            event_callback=on_agent_event,
            timeout_seconds=timeout_seconds,
            cancel_check=cancel_check,
        )
        handler = (node or {}).get("handler") if isinstance((node or {}).get("handler"), dict) else {}
        effective_output_key = str(output_key or handler.get("output_key") or (node or {}).get("output_key") or "").strip()
        effective_output_format = str(
            output_format or handler.get("output_format") or (node or {}).get("output_format") or ""
        ).strip()
        try:
            execution_result = executor.run(
                input_text,
                context={
                    "workspace_id": workspace_id,
                    "workspace_name": workspace.get("name", ""),
                    "source_type": (workspace.get("source") or {}).get("type", "") if isinstance(workspace.get("source"), dict) else "",
                    "node_kind": node_kind,
                    "output_key": effective_output_key,
                    "output_format": effective_output_format,
                    "node_goal": str((node or {}).get("title") or node_kind or "").strip(),
                    "mapped_inputs": mapped_inputs if isinstance(mapped_inputs, dict) else {},
                },
            )
        finally:
            release_agent_cancel(execution_id)
        result = execution_result.to_dict()
        result["id"] = execution_id
        result["trace_events"] = normalize_agent_trace_events(trace_events)
        validation = validate_agent_output(
            output_key=effective_output_key,
            output_format=effective_output_format,
            final_answer=execution_result.final_answer,
        )
        result["output_validation"] = validation
        if execution_result.success and isinstance(node, dict):
            if effective_output_key and not collect_agent_step_output(workspace, node, output_key=effective_output_key)[1]:
                apply_final_answer_output(
                    workspace,
                    node,
                    output_key=effective_output_key,
                    final_answer=execution_result.final_answer,
                    output_format=effective_output_format,
                    validation=validation,
                )
            artifacts, output_value = collect_agent_step_output(workspace, node, output_key=effective_output_key)
            result["artifacts"] = artifacts
            if output_value:
                result["output_value"] = output_value
        self.publish_event(
            "agent.completed" if execution_result.success else "agent.failed",
            workspace_id=workspace_id,
            run_id=execution_run_id,
            agent_execution_id=execution_id,
            payload={
                "execution": copy.deepcopy(result),
                "node_id": str((node or {}).get("id") or "").strip(),
                "node_kind": node_kind,
                "agent_id": str(agent.get("id") or "").strip(),
            },
        )
        return result


    def execute_workspace_agent_node(
        self,
        workspace_id: str,
        node: dict[str, Any],
        *,
        run_context: ExecutionRunContext | None = None,
        input_text: str = "",
    ) -> StepResult:
        workspace_id = str(workspace_id or "").strip()
        node = copy.deepcopy(node) if isinstance(node, dict) else {}
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        agent_id = str(handler.get("agent_id") or "").strip()
        node_kind = str(node.get("kind") or "").strip()
        output_key = str(handler.get("output_key") or node.get("output_key") or "").strip()
        output_format = str(handler.get("output_format") or node.get("output_format") or "").strip()
        max_iterations_raw = handler.get("max_iterations")
        max_iterations = safe_int(max_iterations_raw, 0) if max_iterations_raw not in (None, "") else None
        if max_iterations is not None and max_iterations <= 0:
            max_iterations = None
        timeout_raw = handler.get("timeout_seconds")
        if timeout_raw in (None, ""):
            timeout_raw = node.get("timeout_seconds")
        timeout_seconds = float(timeout_raw) if timeout_raw not in (None, "") and safe_int(timeout_raw, 0) > 0 else None

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            workspace = copy.deepcopy(current)
            tools = normalize_workspace_tools(workspace.get("tools"), existing=workspace.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(workspace.get("agents"), existing=workspace.get("agents"), tool_ids=tool_ids)
            agent = next((item for item in agents if item["id"] == agent_id), None)
            if not agent:
                return StepResult(status="blocked", executor="agent", reason=f"agent not found: {agent_id or 'unset'}")
            if max_iterations is None:
                agent_iterations = agent.get("max_iterations")
                if agent_iterations not in (None, ""):
                    parsed = safe_int(agent_iterations, 0)
                    max_iterations = parsed if parsed > 0 else None

        context = run_context or ExecutionRunContext(workspace_id=workspace_id)
        workspace_nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
        node_index = next(
            (index for index, item in enumerate(workspace_nodes) if isinstance(item, dict) and str(item.get("id") or "").strip() == str(node.get("id") or "").strip()),
            0,
        )
        contract = workspace_io_contract_for_kind(node_kind, node_index)
        if not output_key:
            output_key = str(contract.get("output_key") or "").strip()
        input_mapping = workspace_io_input_mapping(node, contract, node_index)
        input_data = workspace_input_data_for_context(workspace)
        automation = workspace.get("automation") if isinstance(workspace.get("automation"), dict) else {}
        execution_context = automation.get("execution_context") if isinstance(automation.get("execution_context"), dict) else {}
        persisted_outputs = execution_context.get("outputs") if isinstance(execution_context.get("outputs"), dict) else {}
        context_outputs = {**copy.deepcopy(persisted_outputs), **copy.deepcopy(context.outputs)}
        node_config = node.get("config") if isinstance(node.get("config"), dict) else {}
        mapped_inputs = resolve_mapped_inputs(
            input_mapping,
            input_data=input_data,
            context_outputs=context_outputs,
            previous_output=context.previous_output,
            node_config=node_config,
        )
        if not input_text:
            goal_text = str(input_data.get("goal_text") or "").strip()
            input_text = build_agent_node_input_text(
                node_kind=node_kind,
                node_title=str(node.get("title") or node_kind or "node").strip(),
                output_key=output_key,
                mapped_inputs=mapped_inputs,
                goal_text=goal_text,
                node_config=node_config,
            )

        def agent_executor(_workspace_id: str, _agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            execution = self._execute_agent_on_mutable_workspace(
                workspace,
                agent,
                input_text=str(payload.get("input") or input_text or "").strip(),
                requested_node_kind=str(payload.get("node_kind") or node_kind or "").strip(),
                execute_llm=bool(payload.get("execute_llm", True)),
                node=node,
                mapped_inputs=payload.get("mapped_inputs") if isinstance(payload.get("mapped_inputs"), dict) else mapped_inputs,
                output_key=str(payload.get("output_key") or output_key or "").strip(),
                output_format=output_format,
                max_iterations=max_iterations,
                timeout_seconds=timeout_seconds,
                run_id=context.run_id,
            )
            return {"execution": execution}

        step_result = run_agent_node(
            workspace,
            node,
            context,
            agent_executor=agent_executor,
            mapped_inputs=mapped_inputs,
            input_text=input_text,
        )
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            existing = self.workspaces[index]
            updated = normalize_workspace_payload(workspace, existing=existing)
            self.workspaces[index] = updated
        self.save_workspaces()
        return step_result


    def debug_workspace_agent(self, workspace_id: str, agent_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_agent_id = safe_id(str(agent_id or "").strip()) if str(agent_id or "").strip() else ""
        requested_payload = payload if isinstance(payload, dict) else {}
        input_text = str(requested_payload.get("input") or requested_payload.get("text") or "").strip()
        requested_node_id = str(requested_payload.get("node_id") or "").strip()
        requested_node_kind = str(requested_payload.get("node_kind") or "").strip()
        requested_tool_ids = parse_tag_list(requested_payload.get("tool_ids", []))
        execute_llm = bool(requested_payload.get("execute_llm") or False)

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            tools = normalize_workspace_tools(current.get("tools"), existing=current.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(current.get("agents"), existing=current.get("agents"), tool_ids=tool_ids)
            model = normalize_workspace_model(current.get("model"), existing=current.get("model"))
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            agent = next((item for item in agents if item["id"] == requested_agent_id), None)
            if not agent:
                raise ValueError("agent not found")
            preview_workspace = copy.deepcopy(current)
            preview_workspace["agents"] = agents
            preview_workspace["tools"] = tools
            preview_workspace["model"] = model
            preview_workspace["chat"] = chat
            preview_workspace = self.workspace_public_payload(preview_workspace)
            target_node: dict[str, Any] | None = None
            workspace_nodes = preview_workspace.get("nodes") if isinstance(preview_workspace.get("nodes"), list) else []
            if requested_node_id:
                target_node = next(
                    (
                        item for item in workspace_nodes
                        if isinstance(item, dict) and str(item.get("id") or "").strip() == requested_node_id
                    ),
                    None,
                )
            elif requested_node_kind:
                target_node = next(
                    (
                        item for item in workspace_nodes
                        if isinstance(item, dict)
                        and str(item.get("kind") or "").strip() == requested_node_kind
                        and str((item.get("handler") or {}).get("agent_id") or "").strip() == requested_agent_id
                    ),
                    None,
                )

        debug = build_workspace_agent_debug(
            preview_workspace,
            agent,
            input_text=input_text,
            requested_node_kind=requested_node_kind or str((target_node or {}).get("kind") or "").strip(),
            requested_tool_ids=requested_tool_ids,
        )

        result = {"debug": debug}

        if execute_llm and input_text:
            if target_node and str((target_node.get("handler") or {}).get("mode") or "").strip().lower() == "agent":
                step_result = self.execute_workspace_agent_node(
                    workspace_id,
                    copy.deepcopy(target_node),
                    input_text=input_text,
                )
                result["step"] = step_result.as_dict()
                result["execution"] = {
                    "id": step_result.agent_execution_id,
                    "success": step_result.status in {"completed", "warning"},
                    "steps": step_result.agent_steps,
                    "artifacts": step_result.artifacts,
                    "output_value": None,
                    "error": "" if step_result.status in {"completed", "warning"} else step_result.detail,
                    "final_answer": step_result.detail if step_result.status in {"completed", "warning"} else "",
                }
                if step_result.output_key:
                    refreshed = self.workspace_by_id(workspace_id)
                    if refreshed:
                        outputs = (
                            refreshed.get("automation", {})
                            .get("execution_context", {})
                            .get("outputs", {})
                        )
                        if isinstance(outputs, dict) and step_result.output_key in outputs:
                            result["execution"]["output_value"] = outputs.get(step_result.output_key)
            else:
                execution_payload = self._execute_agent_on_mutable_workspace(
                    preview_workspace,
                    agent,
                    input_text=input_text,
                    requested_node_kind=requested_node_kind,
                    execute_llm=True,
                )
                result["execution"] = execution_payload
                if execution_payload.get("success"):
                    with self.lock:
                        index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
                        if index >= 0:
                            existing = self.workspaces[index]
                            updated = normalize_workspace_payload(preview_workspace, existing=existing)
                            self.workspaces[index] = updated
                    self.save_workspaces()

        return result
