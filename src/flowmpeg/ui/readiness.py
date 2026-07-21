"""Fast local tool checks for the browser interface."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum

from flowmpeg.diagnostics import redact_text


class ToolState(str, Enum):
    """Stable executable states shown by the local UI."""

    READY = "ready"
    MISSING = "missing"
    UNUSABLE = "unusable"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class ToolReadiness:
    """One local media executable check."""

    name: str
    state: ToolState
    path: str | None = None
    version: str | None = None
    reason: str | None = None

    @property
    def ready(self) -> bool:
        return self.state is ToolState.READY


@dataclass(frozen=True, slots=True)
class SystemReadiness:
    """The tools required by Flowmpeg media jobs."""

    ffmpeg: ToolReadiness
    ffprobe: ToolReadiness

    @property
    def ready(self) -> bool:
        return self.ffmpeg.ready and self.ffprobe.ready


def check_tool(name: str, timeout: float = 3.0) -> ToolReadiness:
    """Check one executable without changing the computer."""

    path = shutil.which(name)
    if path is None:
        return ToolReadiness(name, ToolState.MISSING)
    try:
        completed = subprocess.run(
            (path, "-version"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return ToolReadiness(
            name,
            ToolState.TIMEOUT,
            path=path,
            reason=f"Version check exceeded {timeout:g} seconds",
        )
    except OSError as error:
        return ToolReadiness(
            name,
            ToolState.UNUSABLE,
            path=path,
            reason=redact_text(str(error))[:400] or None,
        )
    lines = completed.stdout.strip().splitlines()
    version = lines[0][:400] if lines else None
    if completed.returncode != 0:
        reason_lines = redact_text(completed.stderr).strip().splitlines()
        reason = reason_lines[-1][:400] if reason_lines else None
        return ToolReadiness(
            name,
            ToolState.UNUSABLE,
            path=path,
            version=version,
            reason=reason,
        )
    return ToolReadiness(
        name,
        ToolState.READY,
        path=path,
        version=version,
    )


def check_readiness(timeout: float = 3.0) -> SystemReadiness:
    """Check the local FFmpeg pair used by Flowmpeg."""

    return SystemReadiness(
        ffmpeg=check_tool("ffmpeg", timeout),
        ffprobe=check_tool("ffprobe", timeout),
    )


__all__ = [
    "SystemReadiness",
    "ToolReadiness",
    "ToolState",
    "check_readiness",
    "check_tool",
]
