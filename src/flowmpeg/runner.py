"""Synchronous FFmpeg plan execution."""

from __future__ import annotations

import math
import os
import queue
import signal
import subprocess
import threading
import time
import warnings
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import IO, Any, TextIO, TypeVar

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

_WINDOWS = os.name == "nt"
_QueueValue = TypeVar("_QueueValue")


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
    popen_options: dict[str, Any] = {}
    if _WINDOWS:
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_options["start_new_session"] = True

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
            **popen_options,
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
    progress_events: queue.Queue[Progress] = queue.Queue(maxsize=1)
    parser = ProgressParser(expected_duration)
    stderr_tail = _TextTail(stderr_limit)
    callback_events: queue.Queue[Progress] | None = None
    callback_failures: queue.Queue[BaseException] | None = None
    callback_stop = threading.Event()
    callback_thread: threading.Thread | None = None
    if on_progress is not None:
        callback_events = queue.Queue(maxsize=1)
        callback_failures = queue.Queue(maxsize=1)
        callback_thread = threading.Thread(
            target=_dispatch_progress,
            args=(
                callback_events,
                callback_stop,
                on_progress,
                callback_failures,
            ),
            name="flowmpeg-callback",
            daemon=True,
        )
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
    callback_started = False

    try:
        if callback_thread is not None:
            callback_thread.start()
            callback_started = True
        progress_thread.start()
        progress_started = True
        stderr_thread.start()
        stderr_started = True
        while process.poll() is None or progress_thread.is_alive():
            _raise_callback_failure(callback_failures)
            _raise_timeout(timeout, started)
            try:
                event = progress_events.get(timeout=0.05)
            except queue.Empty:
                continue
            last_progress = event
            if callback_events is not None:
                _put_latest(callback_events, event)

        remaining = _take_latest_progress(progress_events)
        if remaining is not None:
            last_progress = remaining
            if callback_events is not None:
                _put_latest(callback_events, remaining)
        callback_stop.set()
        while callback_thread is not None and callback_thread.is_alive():
            _raise_callback_failure(callback_failures)
            _raise_timeout(timeout, started)
            callback_thread.join(timeout=0.05)
        _raise_callback_failure(callback_failures)
    except BaseException:
        if not _stop_process(process, termination_grace):
            _warn_unconfirmed_cleanup()
        raise
    finally:
        callback_stop.set()
        if progress_started:
            progress_thread.join(timeout=termination_grace)
        if stderr_started:
            stderr_thread.join(timeout=termination_grace)
        if callback_started and callback_thread is not None:
            callback_thread.join(timeout=termination_grace)
        _close_pipe(process.stdout)
        _close_pipe(process.stderr)

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
            _put_latest(events, event)


def _dispatch_progress(
    events: queue.Queue[Progress],
    stop: threading.Event,
    callback: Callable[[Progress], None],
    failures: queue.Queue[BaseException],
) -> None:
    while not stop.is_set() or not events.empty():
        try:
            event = events.get(timeout=0.05)
        except queue.Empty:
            continue
        try:
            callback(event)
        except BaseException as error:
            _put_latest(failures, error)
            stop.set()
            return


def _put_latest(
    events: queue.Queue[_QueueValue],
    event: _QueueValue,
) -> None:
    try:
        events.put_nowait(event)
        return
    except queue.Full:
        pass
    with suppress(queue.Empty):
        events.get_nowait()
    try:
        events.put_nowait(event)
    except queue.Full:
        return


def _take_latest_progress(events: queue.Queue[Progress]) -> Progress | None:
    latest: Progress | None = None
    while True:
        try:
            latest = events.get_nowait()
        except queue.Empty:
            return latest


def _raise_callback_failure(
    failures: queue.Queue[BaseException] | None,
) -> None:
    if failures is None:
        return
    try:
        error = failures.get_nowait()
    except queue.Empty:
        return
    raise error


def _raise_timeout(timeout: float | None, started: float) -> None:
    if timeout is not None and time.monotonic() - started >= timeout:
        raise JobTimeoutError(f"FFmpeg timed out after {timeout:g} seconds")


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


def _warn_unconfirmed_cleanup() -> None:
    try:
        warnings.warn(
            "FFmpeg cleanup could not confirm process exit",
            RuntimeWarning,
            stacklevel=3,
        )
    except Warning:
        return


def _stop_process(process: subprocess.Popen[str], grace: float) -> bool:
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


def _kill_process_tree(process: subprocess.Popen[str], grace: float) -> bool:
    if not _signal_process_tree(process, force=True, grace=grace):
        return False
    try:
        process.wait(timeout=grace)
        return True
    except (AttributeError, subprocess.TimeoutExpired, OSError):
        return False


def _signal_process_tree(
    process: subprocess.Popen[str],
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
    process: subprocess.Popen[str],
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
    process: subprocess.Popen[str],
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
        if path is not None and os.path.lexists(path):
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
