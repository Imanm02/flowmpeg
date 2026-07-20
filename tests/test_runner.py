import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest

from flowmpeg import (
    BinaryNotFoundError,
    BinaryUnusableError,
    ExecutionError,
    GraphError,
    OutputExistsError,
    Progress,
    input,
    output,
)
from flowmpeg.runner import _stop_process, _TextTail


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


def test_process_cleanup_does_not_mask_a_job_error() -> None:
    class BrokenProcess:
        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            raise OSError("terminate failed")

        def kill(self) -> None:
            raise OSError("kill failed")

    process = cast(subprocess.Popen[str], BrokenProcess())

    _stop_process(process, 0.0)


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
