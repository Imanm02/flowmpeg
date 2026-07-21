"""Background local commands started from the browser interface."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import secrets
import sys
import threading
import time

from flowmpeg.diagnostics import redact_text
from flowmpeg.processes import popen_group_options

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


JobRunner = Callable[[UiJob], int]


class JobManager:
    """Run local commands in a small ordered worker pool."""

    def __init__(
        self,
        *,
        max_parallel: int = 1,
        runner: JobRunner | None = None,
    ) -> None:
        if max_parallel < 1 or max_parallel > 4:
            raise ValueError("max_parallel must be between 1 and 4")
        self._executor = ThreadPoolExecutor(
            max_workers=max_parallel,
            thread_name_prefix="flowmpeg-ui",
        )
        self._runner = runner or self._run_process
        self._jobs: dict[str, UiJob] = {}
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.RLock()
        self._closed = False

    def start(self, arguments: tuple[str, ...], display: str) -> UiJobSnapshot:
        """Queue one already validated Flowmpeg argument list."""

        if not arguments:
            raise ValueError("job arguments cannot be empty")
        with self._lock:
            if self._closed:
                raise RuntimeError("job manager is closed")
            job = UiJob(secrets.token_urlsafe(12), arguments, display)
            self._jobs[job.id] = job
            self._futures[job.id] = self._executor.submit(self._execute, job)
            return job.snapshot()

    def get(self, job_id: str) -> UiJobSnapshot | None:
        """Return one current job snapshot."""

        with self._lock:
            job = self._jobs.get(job_id)
        return None if job is None else job.snapshot()

    def list(self) -> tuple[UiJobSnapshot, ...]:
        """Return newest jobs first."""

        with self._lock:
            jobs = tuple(reversed(self._jobs.values()))
        return tuple(job.snapshot() for job in jobs)

    def wait(self, job_id: str, timeout: float | None = None) -> UiJobSnapshot:
        """Wait for one job, primarily for callers that need synchronization.""

        with self._lock:
            future = self._futures.get(job_id)
        if future is None:
            raise KeyError(job_id)
        future.result(timeout=timeout)
        snapshot = self.get(job_id)
        if snapshot is None:
            raise KeyError(job_id)
        return snapshot

    def close(self, *, wait: bool = True) -> None:
        """Stop accepting jobs and release worker threads.""

        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _execute(self, job: UiJob) -> None:
        with job.lock:
            if job.cancel_requested:
                job.status = JobStatus.CANCELLED
                job.finished_at = time.time()
                return
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
        try:
            returncode = self._runner(job)
        except Exception as error:
            with job.lock:
                job.output = redact_text(str(error))
            returncode = -1
        with job.lock:
            job.returncode = returncode
            job.finished_at = time.time()
            job.status = (
                JobStatus.CANCELLED
                if job.cancel_requested
                else JobStatus.SUCCEEDED
                if returncode == 0
                else JobStatus.FAILED
            )

    def _run_process(self, job: UiJob) -> int:
        process = subprocess.Popen(
            (sys.executable, "-m", "flowmpeg", *job.arguments),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=False,
            **popen_group_options(),
        )
        output = BoundedOutput()
        with job.lock:
            job.process = process
        try:
            if process.stdout is None:
                raise RuntimeError("job output pipe is unavailable")
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                output.append(chunk)
                with job.lock:
                    job.output = output.value
            return process.wait()
        finally:
            with job.lock:
                job.process = None


__all__ = [
    "BoundedOutput",
    "JobStatus",
    "JobManager",
    "JobRunner",
    "MAX_JOB_OUTPUT",
    "UiJob",
    "UiJobSnapshot",
]
