"""Synchronous FFmpeg plan execution."""

from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import (
    BinaryNotFoundError,
    BinaryUnusableError,
    ExecutionError,
    GraphError,
    JobTimeoutError,
    OutputExistsError,
)
from flowmpeg.plan import Plan
from flowmpeg.progress import Progress, ProgressParser

_protocol = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")


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

    if timeout is not None and timeout <= 0:
        raise ValueError("Timeout must be positive")
    if progress_interval <= 0:
        raise ValueError("Progress interval must be positive")
    if stderr_limit <= 0:
        raise ValueError("Stderr limit must be positive")
    if termination_grace < 0:
        raise ValueError("Termination grace cannot be negative")

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
    progress_thread.start()
    stderr_thread.start()
    last_progress: Progress | None = None

    try:
        while process.poll() is None or progress_thread.is_alive():
            if timeout is not None and time.monotonic() - started >= timeout:
                _stop_process(process, termination_grace)
                raise JobTimeoutError(f"FFmpeg timed out after {timeout:g} seconds")
            try:
                event = progress_events.get(timeout=0.05)
            except queue.Empty:
                continue
            last_progress = event
            if on_progress is not None:
                on_progress(event)
    except BaseException:
        _stop_process(process, termination_grace)
        raise
    finally:
        progress_thread.join(timeout=termination_grace)
        stderr_thread.join(timeout=termination_grace)

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


def _read_stderr(stream: TextIO, tail: _TextTail) -> None:
    for line in stream:
        tail.append(line)


def _stop_process(process: subprocess.Popen[str], grace: float) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _check_outputs(plan: Plan) -> None:
    if plan.overwrite_enabled:
        return
    for output in plan.outputs:
        path = _local_path(output.destination)
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


def _local_path(destination: str) -> Path | None:
    if destination == "-" or destination.upper() == "NUL" or destination == "/dev/null":
        return None
    drive, _ = os.path.splitdrive(destination)
    if not drive and _protocol.match(destination):
        return None
    return Path(destination)


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
