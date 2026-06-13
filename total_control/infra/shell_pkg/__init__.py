"""Shell/SSH/GPU infrastructure — split by concern."""

from .probe import (
    parse_iso_timestamp,
    remote_check_script,
    server_check_ok,
    server_check_scripts,
)

from .command import (
    run_command,
    run_shell,
    run_pty_password_command,
)

from .gpu import (
    gpu_activity_state,
    collect_server,
    reusable_connection_failure_status,
    mark_status_reused,
    collect_all,
    nvidia_smi_probe_script,
    nvidia_smi_output_looks_failed,
    ssh_transport_output_looks_failed,
)

from .host import (
    parse_csv_lines,
    parse_meminfo,
    parse_loadavg,
    parse_cpu_times,
    cpu_utilization_percent,
    parse_proc_net_dev,
    host_mount_allowed,
    disk_payload_for_mount,
    collect_local_disks,
    collect_local_host_resources,
    remote_host_resource_probe_script,
    collect_remote_host_resources,
    host_resource_error_payload,
    collect_host_resources,
)

from .jobs import (
    parse_smoke_peak_mib,
    render_task_template,
    parse_param_matrix,
    conda_bootstrap,
    build_job_script,
)

from .process import (
    ps_lookup_local,
    ps_lookup_remote,
    parse_ps_output,
    percent,
)

from .ssh import (
    ssh_command,
    ssh_command_base,
    probe_ssh_reachable,
    apply_remote_reachability,
)

from .tmux import (
    tmux_new_session_args,
    tmux_resize_commands,
    tmux_resize_shell_script,
    prepare_tmux_for_capture,
    make_session_name,
    local_log_path,
    remote_log_path,
)

from .transfer import (
    rsync_endpoint_prefix,
    server_matches_rsync_prefix,
    server_for_rsync_endpoint,
    shell_join,
    rsync_remote_shell,
    rsync_password_wrapper,
    remote_file_download_endpoint,
    download_remote_file_to_local,
    normalize_rsync_directory_source,
    transfer_item_destination_path,
    transfer_path_exists,
    check_transfer_conflicts,
    build_transfer_command,
    check_detail_text,
)

__all__ = [
    "apply_remote_reachability",
    "build_job_script",
    "build_transfer_command",
    "check_detail_text",
    "check_transfer_conflicts",
    "collect_all",
    "collect_host_resources",
    "collect_local_disks",
    "collect_local_host_resources",
    "collect_remote_host_resources",
    "collect_server",
    "conda_bootstrap",
    "cpu_utilization_percent",
    "disk_payload_for_mount",
    "download_remote_file_to_local",
    "gpu_activity_state",
    "host_mount_allowed",
    "host_resource_error_payload",
    "local_log_path",
    "make_session_name",
    "mark_status_reused",
    "normalize_rsync_directory_source",
    "nvidia_smi_output_looks_failed",
    "nvidia_smi_probe_script",
    "parse_cpu_times",
    "parse_csv_lines",
    "parse_iso_timestamp",
    "parse_loadavg",
    "parse_meminfo",
    "parse_param_matrix",
    "parse_proc_net_dev",
    "parse_ps_output",
    "parse_smoke_peak_mib",
    "percent",
    "prepare_tmux_for_capture",
    "probe_ssh_reachable",
    "ps_lookup_local",
    "ps_lookup_remote",
    "remote_check_script",
    "remote_file_download_endpoint",
    "remote_host_resource_probe_script",
    "remote_log_path",
    "render_task_template",
    "reusable_connection_failure_status",
    "rsync_endpoint_prefix",
    "rsync_password_wrapper",
    "rsync_remote_shell",
    "run_command",
    "run_pty_password_command",
    "run_shell",
    "server_check_ok",
    "server_check_scripts",
    "server_for_rsync_endpoint",
    "server_matches_rsync_prefix",
    "shell_join",
    "ssh_command",
    "ssh_command_base",
    "ssh_transport_output_looks_failed",
    "tmux_new_session_args",
    "tmux_resize_commands",
    "tmux_resize_shell_script",
    "transfer_item_destination_path",
    "transfer_path_exists",
]
