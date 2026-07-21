"""Background local commands started from the browser interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import subprocess
import threading
import time

MAX_JOB_OUTPUT = 200_000


class BoundedOutput:
    """Keep only the newest text from a command process."""

    def __init__(self, limit: int = MAX_JOB_OUTPUT) -> None:
        if limit < 1:
            raise ValueError("output limit must be positive")
        self.limit = limit
        self._value = ""

    def append(self, text: str) -> None:
        """Append text while retaining the configured tail."""

        self._value = (self._value + text)[-self.limit :]

    @property
    def value(self) -> str:
        """Return the retained output tail."""

        return self._value


class JobStatus(str, Enum):
    """Stable states exposed by the local job API."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class UiJob:
    """Mutable internal state for one local command process."""

    id: str
    arguments: tuple[str, ...]
    display: str
    status: JobStatus = JobStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    returncode: int | None = None
    output: str = ""
    cancel_requested: bool = False
    process: subprocess.Popen[str] | None = field(default=None, repr=False)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def snapshot(self) -> UiJobSnapshot:
        """Copy public state while holding the job lock."""

        with self.lock:
            return UiJobSnapshot(
                id=self.id,
                display=self.display,
                status=self.status,
                created_at=self.created_at,
                started_at=self.started_at,
                finished_at=self.finished_at,
                returncode=self.returncode,
                output=self.output,
            )


@dataclass(frozen=True, slots=True)
class UiJobSnapshot:
    """Public state returned to browser polling requests."""

    id: str
    display: str
    status: JobStatus
    created_at: float
    started_at: float | None
    finished_at: float | None
    returncode: int | None
    output: str


__all__ = [
    "BoundedOutput",
    "JobStatus",
    "MAX_JOB_OUTPUT",
    "UiJob",
    "UiJobSnapshot",
]
