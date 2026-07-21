"""Run named media plans with cancellation and clear result states."""

from __future__ import annotations

import math
import os
import tempfile
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Literal, TypeAlias

from flowmpeg.diagnostics import redact_text
from flowmpeg.errors import FlowmpegError, JobCancelledError
from flowmpeg.plan import Plan
from flowmpeg.progress import Progress

BatchStatus: TypeAlias = Literal["completed", "failed", "cancelled", "skipped"]
Pathish: TypeAlias = str | os.PathLike[str]


@dataclass(frozen=True, slots=True)
class BatchJob:
    """One named plan and its execution limits."""

    name: str
    plan: Plan
    expected_duration: float | None = None
    timeout: float | None = None
    cwd: Pathish | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Batch job names cannot be empty")
        if not isinstance(self.plan, Plan):
            raise TypeError("Batch jobs require a Plan")
        _optional_positive("Expected duration", self.expected_duration)
        _optional_positive("Timeout", self.timeout)
        if self.cwd is not None and not isinstance(self.cwd, str | os.PathLike):
            raise TypeError("Batch job working directories must be path-like")
        if self.cwd is not None and os.fspath(self.cwd) == "":
            raise ValueError("Batch job working directories cannot be empty")


@dataclass(frozen=True, slots=True)
class BatchItemResult:
    """The final state of one named batch job."""

    name: str
    status: BatchStatus
    elapsed: float = 0.0
    outputs: tuple[str, ...] = ()
    error: str | None = None
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Ordered results for one batch execution."""

    items: tuple[BatchItemResult, ...]
    elapsed: float

    @property
    def completed(self) -> int:
        return self._count("completed")

    @property
    def failed(self) -> int:
        return self._count("failed")

    @property
    def cancelled(self) -> int:
        return self._count("cancelled")

    @property
    def skipped(self) -> int:
        return self._count("skipped")

    @property
    def ok(self) -> bool:
        return bool(self.items) and self.completed == len(self.items)

    def _count(self, status: BatchStatus) -> int:
        return sum(item.status == status for item in self.items)


class CancellationToken:
    """A thread-safe cancellation signal shared by related jobs."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation for the current and remaining jobs."""

        self._event.set()

    def is_cancelled(self) -> bool:
        """Return true after cancellation has been requested."""

        return self._event.is_set()


class BatchWorkspace:
    """A temporary directory removed when its context exits."""

    def __init__(self, parent: Pathish | None = None) -> None:
        directory = None if parent is None else os.fspath(parent)
        self._temporary = tempfile.TemporaryDirectory(
            prefix="flowmpeg-batch-",
            dir=directory,
        )
        self._root = Path(self._temporary.name)
        self._closed = False

    @property
    def root(self) -> Path:
        """Return the live workspace root."""

        self._require_open()
        return self._root

    def path(self, relative: Pathish) -> Path:
        """Return a safe path contained by this workspace."""

        self._require_open()
        value = PurePath(os.fspath(relative))
        if value.is_absolute() or not value.parts or ".." in value.parts:
            raise ValueError("Workspace paths must stay under the workspace root")
        return self._root.joinpath(*value.parts)

    def allocate(self, relative: Pathish) -> Path:
        """Return a contained path after creating its parent directory."""

        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def cleanup(self) -> None:
        """Remove this workspace and every temporary file under it."""

        if self._closed:
            return
        self._temporary.cleanup()
        self._closed = True

    def __enter__(self) -> BatchWorkspace:
        self._require_open()
        return self

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        traceback: object,
    ) -> None:
        del error_type, error, traceback
        self.cleanup()

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("Batch workspace is closed")


def run_batch(
    jobs: Iterable[BatchJob],
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    probe_timeout: float | None = 10.0,
    token: CancellationToken | None = None,
    continue_on_error: bool = False,
    on_progress: Callable[[BatchJob, Progress], None] | None = None,
    on_item: Callable[[BatchItemResult], None] | None = None,
    progress_interval: float = 0.5,
    stderr_limit: int = 128_000,
    termination_grace: float = 2.0,
) -> BatchResult:
    """Run plans in order and return one result for every job."""

    values = tuple(jobs)
    _validate_jobs(values)
    cancellation = token if token is not None else CancellationToken()
    if not isinstance(cancellation, CancellationToken):
        raise TypeError("Batch token must be a CancellationToken")
    if not isinstance(continue_on_error, bool):
        raise TypeError("Continue-on-error must be Boolean")
    if on_progress is not None and not callable(on_progress):
        raise TypeError("Batch progress callback must be callable")
    if on_item is not None and not callable(on_item):
        raise TypeError("Batch item callback must be callable")

    started = time.monotonic()
    items: list[BatchItemResult] = []
    for index, job in enumerate(values):
        if cancellation.is_cancelled():
            items.extend(_remaining(values[index:], "cancelled", on_item))
            break

        def report(progress: Progress, current: BatchJob = job) -> None:
            if on_progress is not None:
                on_progress(current, progress)

        job_started = time.monotonic()
        try:
            result = job.plan.run(
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
                probe_timeout=probe_timeout,
                cwd=job.cwd,
                cancelled=cancellation.is_cancelled,
                on_progress=report if on_progress is not None else None,
                expected_duration=job.expected_duration,
                timeout=job.timeout,
                progress_interval=progress_interval,
                stderr_limit=stderr_limit,
                termination_grace=termination_grace,
            )
        except JobCancelledError as error:
            item = BatchItemResult(
                job.name,
                "cancelled",
                time.monotonic() - job_started,
                error=redact_text(str(error)),
                error_type=type(error).__name__,
            )
            items.append(item)
            _notify(on_item, item)
            items.extend(_remaining(values[index + 1 :], "cancelled", on_item))
            break
        except FlowmpegError as error:
            item = BatchItemResult(
                job.name,
                "failed",
                time.monotonic() - job_started,
                error=redact_text(str(error)),
                error_type=type(error).__name__,
            )
            items.append(item)
            _notify(on_item, item)
            if not continue_on_error:
                items.extend(_remaining(values[index + 1 :], "skipped", on_item))
                break
        else:
            item = BatchItemResult(
                job.name,
                "completed",
                result.elapsed,
                result.outputs,
            )
            items.append(item)
            _notify(on_item, item)

    return BatchResult(tuple(items), time.monotonic() - started)


def _remaining(
    jobs: Iterable[BatchJob],
    status: Literal["cancelled", "skipped"],
    callback: Callable[[BatchItemResult], None] | None = None,
) -> list[BatchItemResult]:
    items = [BatchItemResult(job.name, status) for job in jobs]
    for item in items:
        _notify(callback, item)
    return items


def _notify(
    callback: Callable[[BatchItemResult], None] | None,
    item: BatchItemResult,
) -> None:
    if callback is not None:
        callback(item)


def _validate_jobs(jobs: tuple[BatchJob, ...]) -> None:
    if not jobs:
        raise ValueError("Batches require at least one job")
    if not all(isinstance(job, BatchJob) for job in jobs):
        raise TypeError("Batches require BatchJob values")
    names = [job.name for job in jobs]
    if len(set(names)) != len(names):
        raise ValueError("Batch job names must be unique")


def _optional_positive(name: str, value: float | None) -> None:
    if value is None:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be positive and finite")


__all__ = [
    "BatchItemResult",
    "BatchJob",
    "BatchResult",
    "BatchStatus",
    "BatchWorkspace",
    "CancellationToken",
    "run_batch",
]
