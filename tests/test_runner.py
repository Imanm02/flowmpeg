import io
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from math import inf, nan
from pathlib import Path
from typing import cast

import pytest

from flowmpeg import (
    BinaryNotFoundError,
    BinaryUnusableError,
    ExecutionError,
    GraphError,
    JobCancelledError,
    JobTimeoutError,
    OutputExistsError,
    Progress,
    input,
    output,
)
from flowmpeg.processes import (
    _WINDOWS_CREATE_NEW_PROCESS_GROUP,
    _signal_process_tree,
    stop_process_tree,
)
from flowmpeg.runner import (
    _put_latest,
    _read_stderr,
    _TextTail,
    _warn_unconfirmed_cleanup,
)


def test_runner_reports_missing_binary(tmp_path: Path) -> None:
    target = tmp_path / "copy.mp4"
    plan = output(input("movie.mp4").video(), to=target)

    with pytest.raises(BinaryNotFoundError, match="was not found"):
        plan.run(ffmpeg="missing-flowmpeg-ffmpeg")


def test_runner_reports_unusable_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    def deny_start(*args: object, **kwargs: object) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(subprocess, "Popen", deny_start)

    with pytest.raises(BinaryUnusableError, match="could not be started"):
        plan.run(ffmpeg="blocked-ffmpeg")


def test_runner_refuses_existing_output(tmp_path: Path) -> None:
    target = tmp_path / "copy.mp4"
    target.touch()
    plan = output(input("movie.mp4").video(), to=target)

    with pytest.raises(OutputExistsError, match="already exists"):
        plan.run()


def test_runner_refuses_dangling_output_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "copy.mp4"
    plan = output(input("movie.mp4").video(), to=target)
    original_lexists = os.path.lexists

    def report_dangling_link(path: str | os.PathLike[str]) -> bool:
        return os.fspath(path) == os.fspath(target) or original_lexists(path)

    monkeypatch.setattr(os.path, "lexists", report_dangling_link)

    with pytest.raises(OutputExistsError, match="already exists"):
        plan.run()


@pytest.mark.parametrize("name", ["copy file.mp4", "copy%20file.mp4", "copy#file.mp4"])
def test_runner_refuses_existing_file_protocol_path(
    tmp_path: Path,
    name: str,
) -> None:
    target = tmp_path / name
    target.touch()
    plan = output(input("movie.mp4").video(), to=f"file:{target}")

    with pytest.raises(OutputExistsError, match="already exists"):
        plan.run()


def test_plan_rejects_dash_output() -> None:
    with pytest.raises(GraphError, match="start with a dash"):
        output(input("movie.mp4").video(), to="-")


def test_runner_rejects_output_pipe_conflicts() -> None:
    plan = output(input("movie.mp4").video(), to="pipe:1")

    with pytest.raises(GraphError, match="reserves standard output"):
        plan.run()


@pytest.mark.parametrize("source", ["-", "pipe:0"])
def test_runner_rejects_input_pipe_conflicts(source: str, tmp_path: Path) -> None:
    plan = output(input(source).video(), to=tmp_path / "copy.mp4")

    with pytest.raises(GraphError, match="does not accept standard input"):
        plan.run()


def test_stderr_tail_keeps_the_latest_text() -> None:
    tail = _TextTail(10)

    tail.append("12345678")
    tail.append("abcde")

    assert tail.text() == "45678abcde"


def test_stderr_reader_redacts_before_bounding() -> None:
    tail = _TextTail(64)
    stream = io.StringIO(
        "https://media.example/video?token=" + "x" * 9_000 + "hidden-value\n"
    )

    _read_stderr(stream, tail)

    assert "hidden-value" not in tail.text()
    assert "token=<redacted>" in tail.text()


@pytest.mark.parametrize("value", [0.0, -1.0, inf, nan, True, "1"])
def test_runner_rejects_invalid_expected_duration(
    tmp_path: Path,
    value: object,
) -> None:
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(ValueError, match="positive and finite"):
        plan.run(expected_duration=cast(float, value))


@pytest.mark.parametrize("value", [0.0, -1.0, inf, nan, True, "1"])
def test_runner_rejects_invalid_timeout(tmp_path: Path, value: object) -> None:
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(ValueError, match="positive and finite"):
        plan.run(timeout=cast(float, value))


@pytest.mark.parametrize("value", [0.0, -1.0, inf, nan, True, "1"])
def test_runner_rejects_invalid_progress_interval(
    tmp_path: Path,
    value: object,
) -> None:
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(ValueError, match="positive and finite"):
        plan.run(progress_interval=cast(float, value))


@pytest.mark.parametrize("value", [-1.0, -inf, inf, nan, True, "1"])
def test_runner_rejects_invalid_termination_grace(
    tmp_path: Path,
    value: object,
) -> None:
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(ValueError, match="nonnegative and finite"):
        plan.run(termination_grace=cast(float, value))


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "10"])
def test_runner_rejects_invalid_stderr_limit(
    tmp_path: Path,
    value: object,
) -> None:
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(ValueError, match="positive integer"):
        plan.run(stderr_limit=cast(int, value))


def test_runner_rejects_noncallable_cancellation(tmp_path: Path) -> None:
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(ValueError, match="predicate must be callable"):
        plan.run(cancelled=cast(object, True))


def test_runner_cancels_before_starting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = False

    def start(*args: object, **kwargs: object) -> None:
        nonlocal started
        del args, kwargs
        started = True

    monkeypatch.setattr(subprocess, "Popen", start)
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(JobCancelledError, match="was cancelled"):
        plan.run(cancelled=lambda: True)

    assert not started


def test_runner_stops_process_after_cancellation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = 0
    stopped = False

    class RunningProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO()
            self.stderr = io.StringIO()

        def poll(self) -> None:
            return None

    process = RunningProcess()

    def cancelled() -> bool:
        nonlocal checks
        checks += 1
        return checks >= 3

    def stop(*args: object) -> bool:
        nonlocal stopped
        del args
        stopped = True
        return True

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr("flowmpeg.runner.stop_process_tree", stop)
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(JobCancelledError, match="was cancelled"):
        plan.run(cancelled=cancelled, termination_grace=0.01)

    assert stopped
    assert process.stdout.closed
    assert process.stderr.closed


def test_process_cleanup_does_not_mask_a_job_error() -> None:
    class BrokenProcess:
        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            raise OSError("terminate failed")

        def kill(self) -> None:
            raise OSError("kill failed")

    process = cast(subprocess.Popen[str], BrokenProcess())

    assert stop_process_tree(process, 0.0) is False


def test_cleanup_warning_cannot_mask_a_job_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_warning(*args: object, **kwargs: object) -> None:
        raise RuntimeWarning("warnings are errors")

    monkeypatch.setattr("flowmpeg.runner.warnings.warn", fail_warning)

    _warn_unconfirmed_cleanup()


def test_process_cleanup_kills_after_poll_failure() -> None:
    class PollFailure:
        def __init__(self) -> None:
            self.killed = False

        def poll(self) -> int | None:
            raise OSError("poll failed")

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return -9

    value = PollFailure()
    process = cast(subprocess.Popen[str], value)

    assert stop_process_tree(process, 0.0) is True
    assert value.killed


def test_process_cleanup_reports_unconfirmed_exit() -> None:
    class StuckProcess:
        def __init__(self) -> None:
            self.killed = False

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float | None = None) -> int:
            raise subprocess.TimeoutExpired(
                "ffmpeg",
                timeout if timeout is not None else 0.0,
            )

    value = StuckProcess()
    process = cast(subprocess.Popen[str], value)

    assert stop_process_tree(process, 0.0) is False
    assert value.killed


def test_runner_configures_a_separate_process_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FinishedProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO()
            self.stderr = io.StringIO()

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 0

    def start(*args: object, **kwargs: object) -> FinishedProcess:
        del args
        captured.update(kwargs)
        return FinishedProcess()

    monkeypatch.setattr(subprocess, "Popen", start)
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    plan.run(cwd=tmp_path)

    assert captured["cwd"] == str(tmp_path)

    if os.name == "nt":
        assert captured["creationflags"] == _WINDOWS_CREATE_NEW_PROCESS_GROUP
    else:
        assert captured["start_new_session"] is True


def test_posix_cleanup_signals_the_process_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signals: list[tuple[int, int]] = []

    class Process:
        pid = 123

    monkeypatch.setattr("flowmpeg.processes._WINDOWS", False)
    monkeypatch.setattr(os, "getpgid", lambda pid: pid + 1, raising=False)
    monkeypatch.setattr(signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(
        os,
        "killpg",
        lambda group, value: signals.append((group, value)),
        raising=False,
    )
    process = cast(subprocess.Popen[str], Process())

    assert _signal_process_tree(process, force=False, grace=0)
    assert _signal_process_tree(process, force=True, grace=0)
    assert signals == [
        (124, signal.SIGTERM),
        (124, 9),
    ]


def test_windows_cleanup_targets_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    class Process:
        pid = 456

    def run_taskkill(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("flowmpeg.processes._WINDOWS", True)
    monkeypatch.setattr(subprocess, "run", run_taskkill)
    process = cast(subprocess.Popen[str], Process())

    assert _signal_process_tree(process, force=False, grace=1)
    assert _signal_process_tree(process, force=True, grace=1)
    assert commands == [
        ["taskkill", "/PID", "456", "/T"],
        ["taskkill", "/PID", "456", "/T", "/F"],
    ]


def test_progress_queue_keeps_only_the_latest_event() -> None:
    events: queue.Queue[Progress] = queue.Queue(maxsize=1)
    first = Progress(None, None, None, None, None, None, "continue", ())
    latest = Progress(None, None, None, None, None, None, "end", ())

    _put_latest(events, first)
    _put_latest(events, latest)

    assert events.qsize() == 1
    assert events.get_nowait() is latest


def test_slow_progress_callback_does_not_block_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callback_entered = threading.Event()
    release_callback = threading.Event()

    class RunningProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("progress=continue\n")
            self.stderr = io.StringIO()

        def poll(self) -> None:
            return None

    process = RunningProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr("flowmpeg.runner.stop_process_tree", lambda *args: True)
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    def wait_on_progress(event: Progress) -> None:
        del event
        callback_entered.set()
        release_callback.wait(timeout=5)

    started = time.monotonic()
    try:
        with pytest.raises(JobTimeoutError, match="timed out"):
            plan.run(
                on_progress=wait_on_progress,
                timeout=0.1,
                termination_grace=0.01,
            )
    finally:
        release_callback.set()

    assert callback_entered.is_set()
    assert time.monotonic() - started < 1


@pytest.mark.parametrize("failed_start", [1, 2])
def test_thread_start_failure_stops_the_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_start: int,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO()
            self.stderr = io.StringIO()
            self.returncode: int | None = None
            self.terminated = False

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            assert self.returncode is not None
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    process = FakeProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    original_start = threading.Thread.start
    starts = 0

    def fail_selected_start(thread: threading.Thread) -> None:
        nonlocal starts
        starts += 1
        if starts == failed_start:
            raise RuntimeError("thread start failed")
        original_start(thread)

    monkeypatch.setattr(threading.Thread, "start", fail_selected_start)
    plan = output(input("movie.mp4").video(), to=tmp_path / "copy.mp4")

    with pytest.raises(RuntimeError, match="thread start failed"):
        plan.run()

    assert process.terminated
    assert process.stdout.closed
    assert process.stderr.closed


@pytest.mark.integration
def test_runner_executes_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")

    target = tmp_path / "generated.mp4"
    source = input(
        "testsrc2=duration=0.3:size=32x32:rate=10",
        "-f",
        "lavfi",
    )
    plan = output(
        source.video(),
        to=target,
        args=("-c:v", "mpeg4"),
    )
    events: list[Progress] = []

    result = plan.run(
        ffmpeg=ffmpeg,
        on_progress=events.append,
        expected_duration=0.3,
        timeout=10,
    )

    assert result.returncode == 0
    assert result.outputs == (str(target),)
    assert target.exists()
    assert events[-1].state == "end"


@pytest.mark.integration
def test_runner_raises_structured_execution_error(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")

    target = tmp_path / "bad.mp4"
    source = input(
        "color=black:size=16x16:duration=0.1",
        "-f",
        "lavfi",
    )
    plan = output(
        source.video(),
        to=target,
        args=("-c:v", "missing_flowmpeg_codec"),
    )

    with pytest.raises(ExecutionError) as captured:
        plan.run(ffmpeg=ffmpeg, timeout=10)

    assert str(captured.value) == f"FFmpeg exited with code {captured.value.returncode}"
    assert captured.value.returncode != 0
    assert "missing_flowmpeg_codec" in captured.value.stderr
    assert captured.value.command.startswith(ffmpeg)
