"""Synchronous FFmpeg plan execution."""

from __future__ import annotations

import math
import queue
import subprocess
import threading
import time
import warnings
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import IO, Any, TextIO

from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import (
    BinaryNotFoundError,
    BinaryUnusableError,
    ExecutionError,
    GraphError,
    JobTimeoutError,
    OutputExistsError,
)
from flowmpeg.pathing import local_path
from flowmpeg.plan import Plan
from flowmpeg.progress import Progress, ProgressParser


@dataclass(frozen=True, slots=True)
class RunResult:
    """The outcome of a completed FFmpeg process."""

    returncode: int
    elapsed: float
    stderr: str
    last_progress: Progress | None
    outputs: tuple[str, ...]


def run(
    plan: Plan,
    *,
    ffmpeg: str = "ffmpeg",
    on_progress: Callable[[Progress], None] | None = None,
    expected_duration: float | None = None,
    timeout: float | None = None,
    progress_interval: float = 0.5,
    stderr_limit: int = 128_000,
    termination_grace: float = 2.0,
) -> RunResult:
    """Run a plan and report machine-readable FFmpeg progress."""

    if expected_duration is not None:
        _require_positive_finite("Expected duration", expected_duration)
    if timeout is not None:
        _require_positive_finite("Timeout", timeout)
    _require_positive_finite("Progress interval", progress_interval)
    if isinstance(stderr_limit, bool) or not isinstance(stderr_limit, int):
        raise ValueError("Stderr limit must be a positive integer")
    if stderr_limit <= 0:
        raise ValueError("Stderr limit must be a positive integer")
    _require_nonnegative_finite("Termination grace", termination_grace)

    _check_outputs(plan)
    _check_pipes(plan)
    compiled = plan.compile(ffmpeg)
    argv = (
        compiled.argv[0],
        "-progress",
        "pipe:1",
        "-nostats",
        "-stats_period",
        f"{progress_interval:g}",
        *compiled.argv[1:],
    )
    command = display_argv(argv)

    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except FileNotFoundError as error:
        raise BinaryNotFoundError(
            f"FFmpeg was not found: {ffmpeg}", tool="ffmpeg"
        ) from error
    except OSError as error:
        raise BinaryUnusableError(
            f"FFmpeg could not be started: {ffmpeg}", tool="ffmpeg"
        ) from error

    assert process.stdout is not None
    assert process.stderr is not None
    progress_events: queue.Queue[Progress] = queue.Queue()
    parser = ProgressParser(expected_duration)
    stderr_tail = _TextTail(stderr_limit)
    progress_thread = threading.Thread(
        target=_read_progress,
        args=(process.stdout, parser, progress_events),
        name="flowmpeg-progress",
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_stderr,
        args=(process.stderr, stderr_tail),
        name="flowmpeg-stderr",
        daemon=True,
    )
    started = time.monotonic()
    last_progress: Progress | None = None
    progress_started = False
    stderr_started = False

    try:
        progress_thread.start()
        progress_started = True
        stderr_thread.start()
        stderr_started = True
        while process.poll() is None or progress_thread.is_alive():
            if timeout is not None and time.monotonic() - started >= timeout:
                raise JobTimeoutError(f"FFmpeg timed out after {timeout:g} seconds")
            try:
                event = progress_events.get(timeout=0.05)
            except queue.Empty:
                continue
            last_progress = event
            if on_progress is not None:
                on_progress(event)
    except BaseException:
        if not _stop_process(process, termination_grace):
            warnings.warn(
                "FFmpeg cleanup could not confirm process exit",
                RuntimeWarning,
                stacklevel=2,
            )
        raise
    finally:
        if progress_started:
            progress_thread.join(timeout=termination_grace)
        if stderr_started:
            stderr_thread.join(timeout=termination_grace)
        _close_pipe(process.stdout)
        _close_pipe(process.stderr)

    while not progress_events.empty():
        last_progress = progress_events.get_nowait()
        if on_progress is not None:
            on_progress(last_progress)

    returncode = process.wait()
    elapsed = time.monotonic() - started
    stderr = redact_text(stderr_tail.text())
    if returncode != 0:
        message = f"FFmpeg exited with code {returncode}"
        raise ExecutionError(
            message,
            returncode=returncode,
            stderr=stderr,
            command=command,
        )

    return RunResult(
        returncode,
        elapsed,
        stderr,
        last_progress,
        tuple(output.destination for output in plan.outputs),
    )


def _read_progress(
    stream: TextIO,
    parser: ProgressParser,
    events: queue.Queue[Progress],
) -> None:
    for line in stream:
        event = parser.feed_line(line)
        if event is not None:
            events.put(event)


def _require_positive_finite(name: str, value: float) -> None:
    if not _is_finite_number(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")


def _require_nonnegative_finite(name: str, value: float) -> None:
    if not _is_finite_number(value) or value < 0:
        raise ValueError(f"{name} must be nonnegative and finite")


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    return not isinstance(value, float) or math.isfinite(value)


def _read_stderr(stream: TextIO, tail: _TextTail) -> None:
    for line in stream:
        tail.append(redact_text(line))


def _stop_process(process: subprocess.Popen[str], grace: float) -> bool:
    try:
        stopped = process.poll() is not None
    except OSError:
        return _kill_process(process, grace)
    if stopped:
        return True
    try:
        process.terminate()
    except OSError:
        return _kill_process(process, grace)
    try:
        process.wait(timeout=grace)
        return True
    except (subprocess.TimeoutExpired, OSError):
        return _kill_process(process, grace)


def _kill_process(process: subprocess.Popen[str], grace: float) -> bool:
    try:
        process.kill()
    except OSError:
        return False
    try:
        process.wait(timeout=grace)
        return True
    except (subprocess.TimeoutExpired, OSError):
        return False


def _close_pipe(stream: IO[Any]) -> None:
    try:
        stream.close()
    except OSError:
        return


def _check_outputs(plan: Plan) -> None:
    if plan.overwrite_enabled:
        return
    for output in plan.outputs:
        path = local_path(output.destination)
        if path is not None and path.exists():
            raise OutputExistsError(f"Output already exists: {path}")


def _check_pipes(plan: Plan) -> None:
    if any(
        node.source == "-" or node.source.startswith("pipe:")
        for node in plan.graph.inputs
    ):
        raise GraphError("The synchronous runner does not accept standard input")
    if any(
        output.destination == "-" or output.destination.startswith("pipe:")
        for output in plan.outputs
    ):
        raise GraphError("The synchronous runner reserves standard output")


class _TextTail:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._size = 0
        self._parts: deque[str] = deque()

    def append(self, value: str) -> None:
        if len(value) >= self._limit:
            self._parts.clear()
            self._parts.append(value[-self._limit :])
            self._size = self._limit
            return
        self._parts.append(value)
        self._size += len(value)
        while self._size > self._limit and self._parts:
            removed = self._parts.popleft()
            self._size -= len(removed)
            overflow = self._size - self._limit
            if overflow < 0:
                kept = removed[overflow:]
                self._parts.appendleft(kept)
                self._size += len(kept)

    def text(self) -> str:
        return "".join(self._parts)
