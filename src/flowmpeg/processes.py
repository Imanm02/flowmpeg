"""Cross-platform process group cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
from typing import Any

_WINDOWS = os.name == "nt"


def popen_group_options() -> dict[str, Any]:
    """Return Popen options that isolate a new process tree."""

    if _WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def stop_process_tree(process: subprocess.Popen[Any], grace: float) -> bool:
    """Stop a process group, then force it down after the grace period."""

    try:
        stopped = process.poll() is not None
    except OSError:
        return _kill_process_tree(process, grace)
    if stopped:
        return True
    _signal_process_tree(process, force=False, grace=grace)
    try:
        process.wait(timeout=grace)
        return True
    except (AttributeError, subprocess.TimeoutExpired, OSError):
        return _kill_process_tree(process, grace)


def _kill_process_tree(process: subprocess.Popen[Any], grace: float) -> bool:
    if not _signal_process_tree(process, force=True, grace=grace):
        return False
    try:
        process.wait(timeout=grace)
        return True
    except (AttributeError, subprocess.TimeoutExpired, OSError):
        return False


def _signal_process_tree(
    process: subprocess.Popen[Any],
    *,
    force: bool,
    grace: float,
) -> bool:
    if _WINDOWS:
        return _signal_windows_process_tree(process, force=force, grace=grace)
    posix_os: Any = os
    posix_signal: Any = signal
    try:
        process_group = posix_os.getpgid(process.pid)
        signal_value = posix_signal.SIGKILL if force else signal.SIGTERM
        posix_os.killpg(process_group, signal_value)
        return True
    except (AttributeError, OSError):
        return _signal_direct_process(process, force=force)


def _signal_windows_process_tree(
    process: subprocess.Popen[Any],
    *,
    force: bool,
    grace: float,
) -> bool:
    try:
        pid = process.pid
    except AttributeError:
        return _signal_direct_process(process, force=force)
    command = ["taskkill", "/PID", str(pid), "/T"]
    if force:
        command.append("/F")
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            shell=False,
            timeout=max(grace, 0.1),
        )
    except (OSError, subprocess.TimeoutExpired):
        return _signal_direct_process(process, force=force)
    if completed.returncode == 0:
        return True
    return _signal_direct_process(process, force=force)


def _signal_direct_process(
    process: subprocess.Popen[Any],
    *,
    force: bool,
) -> bool:
    try:
        if force:
            process.kill()
        else:
            process.terminate()
        return True
    except (AttributeError, OSError):
        return False
