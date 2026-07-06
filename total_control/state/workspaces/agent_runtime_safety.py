"""Workspace Agent runtime safety helpers."""

from __future__ import annotations

import os
import re
import shlex

from total_control.path_safety import sensitive_path_block_reason

RUNTIME_OBSERVATION_SECRET_PATTERN = re.compile(
    r"(?i)"
    r"((?:api[_-]?key|access[_-]?token|secret|password|passphrase|credential)\s*[:=]\s*)"
    r"([^\s'\";&|]+)"
)


def redact_runtime_observation_text(text: str) -> str:
    value = str(text or "")
    if not value:
        return ""
    value = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[A-Za-z0-9._~+/=-]{8,}", r"\1***", value)
    value = re.sub(r"(?i)(authorization\s*[:=]\s*)(?!bearer\s+\*\*\*)[^\s'\";&|]+", r"\1***", value)
    value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}", r"\1***", value)
    value = RUNTIME_OBSERVATION_SECRET_PATTERN.sub(r"\1***", value)
    return value


def workspace_tool_command_block_reason(tool_id: str, command: str) -> str:
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
    diagnostic_reason = workspace_tool_host_exec_diagnostic_block_reason(text)
    if diagnostic_reason:
        return diagnostic_reason
    return ""


def workspace_tool_host_exec_diagnostic_block_reason(command: str) -> str:
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
        if workspace_tool_host_exec_version_only(executable, args):
            return ""
        return "host.exec 的解释器命令只允许版本探测；脚本执行请走配置化 job.run。"

    for arg in parts:
        if sensitive_path_block_reason(arg):
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
        if executable == "ps":
            return workspace_tool_host_exec_ps_block_reason(args)
        return workspace_tool_host_exec_option_block_reason(executable, args)
    if executable == "top":
        if workspace_tool_host_exec_top_is_bounded(args):
            return ""
        return "host.exec 只允许有界 top 诊断，例如 top -b -n 1。"
    if executable == "systemctl":
        return workspace_tool_host_exec_systemctl_block_reason(args)
    if executable == "git":
        return workspace_tool_host_exec_git_block_reason(args)
    if executable == "conda":
        return workspace_tool_host_exec_conda_block_reason(args)
    if executable in {"pip", "pip3"}:
        if workspace_tool_host_exec_version_only(executable, args):
            return ""
        return "host.exec 的 pip 命令只允许版本探测；安装/卸载请走配置化 env.prepare。"
    if executable == "docker":
        return workspace_tool_host_exec_docker_block_reason(args)
    return "host.exec 仅允许主机/环境诊断命令；运行程序、训练或环境变更请使用配置化 job.run/env.prepare。"


def workspace_tool_host_exec_ps_block_reason(args: list[str]) -> str:
    if not args:
        return ""
    safe_fields = {"pid", "ppid", "user", "uid", "stat", "comm"}
    allowed_value_flags = {"-p", "--pid", "-o", "-eo"}
    index = 0
    saw_output_fields = False
    while index < len(args):
        arg = str(args[index] or "").strip()
        lowered = arg.lower()
        if lowered in {"-p", "--pid"}:
            if index + 1 >= len(args) or not re.fullmatch(r"[0-9,]+", str(args[index + 1] or "").strip()):
                return "host.exec 的 ps -p/--pid 只允许明确的数字 PID。"
            index += 2
            continue
        if lowered.startswith("--pid="):
            pid_value = lowered.split("=", 1)[1]
            if not re.fullmatch(r"[0-9,]+", pid_value):
                return "host.exec 的 ps --pid 只允许明确的数字 PID。"
            index += 1
            continue
        if lowered in {"-o", "-eo"}:
            if index + 1 >= len(args):
                return "host.exec 的 ps 必须显式声明安全输出字段。"
            fields = [field.strip().lower() for field in str(args[index + 1] or "").split(",") if field.strip()]
            if not fields or any(field not in safe_fields for field in fields):
                return "host.exec 的 ps 只允许输出 pid,ppid,user,uid,stat,comm 安全字段。"
            saw_output_fields = True
            index += 2
            continue
        if lowered.startswith("-eo") and len(lowered) > 3:
            fields = [field.strip().lower() for field in lowered[3:].split(",") if field.strip()]
            if not fields or any(field not in safe_fields for field in fields):
                return "host.exec 的 ps 只允许输出 pid,ppid,user,uid,stat,comm 安全字段。"
            saw_output_fields = True
            index += 1
            continue
        if lowered.startswith("-o") and len(lowered) > 2:
            fields = [field.strip().lower() for field in lowered[2:].split(",") if field.strip()]
            if not fields or any(field not in safe_fields for field in fields):
                return "host.exec 的 ps 只允许输出 pid,ppid,user,uid,stat,comm 安全字段。"
            saw_output_fields = True
            index += 1
            continue
        if lowered not in allowed_value_flags:
            return "host.exec 的 ps 只允许明确 PID 和安全字段输出；请使用 ps -eo pid,ppid,user,stat,comm。"
        index += 1
    if not saw_output_fields:
        return "host.exec 的 ps 必须显式使用安全输出字段，避免泄漏命令行参数。"
    return workspace_tool_host_exec_option_block_reason("ps", args)


def workspace_tool_host_exec_option_block_reason(executable: str, args: list[str]) -> str:
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
        if not lowered:
            return "host.exec 的 printenv 必须指定明确变量名，不能打印完整环境。"
        secret_terms = ("key", "token", "secret", "password", "credential")
        for arg in lowered:
            if any(term in arg for term in secret_terms):
                return "host.exec 诊断命令不允许直接打印疑似密钥或令牌环境变量。"
    return ""


def workspace_tool_host_exec_top_is_bounded(args: list[str]) -> bool:
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


def workspace_tool_host_exec_systemctl_block_reason(args: list[str]) -> str:
    if not args:
        return "host.exec 的 systemctl 只允许状态查询子命令。"
    subcommand = args[0].lower()
    allowed = {"status", "is-active", "is-enabled", "list-units", "list-unit-files", "show"}
    if subcommand not in allowed:
        return "host.exec 的 systemctl 只允许状态查询；启动、停止或重载服务请走人工确认后的工作流。"
    return workspace_tool_host_exec_option_block_reason("systemctl", args)


def workspace_tool_host_exec_git_block_reason(args: list[str]) -> str:
    if not args:
        return "host.exec 的 git 只允许只读查询子命令。"
    subcommand = args[0].lower()
    allowed = {"status", "diff", "log", "show", "branch", "rev-parse", "remote", "describe"}
    if subcommand not in allowed:
        return "host.exec 的 git 只允许只读查询；clone/pull/checkout 等变更请走配置化工具或工作流。"
    return workspace_tool_host_exec_option_block_reason("git", args)


def workspace_tool_host_exec_conda_block_reason(args: list[str]) -> str:
    if not args:
        return "host.exec 的 conda 只允许环境查询子命令。"
    subcommand = args[0].lower()
    if subcommand in {"--version", "-v"}:
        return ""
    if subcommand in {"info", "list"}:
        return workspace_tool_host_exec_option_block_reason("conda", args)
    if subcommand == "env" and len(args) >= 2 and args[1].lower() in {"list", "export"}:
        return workspace_tool_host_exec_option_block_reason("conda", args)
    return "host.exec 的 conda 只允许 info/list/env list/env export；创建或安装请走配置化 env.prepare。"


def workspace_tool_host_exec_docker_block_reason(args: list[str]) -> str:
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
    return workspace_tool_host_exec_option_block_reason("docker", args)


def workspace_tool_host_exec_version_only(executable: str, args: list[str]) -> bool:
    _ = executable
    return len(args) == 1 and args[0].lower() in {"--version", "-v"}
