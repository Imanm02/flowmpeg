import shutil
from pathlib import Path

import pytest

from flowmpeg import (
    BinaryNotFoundError,
    ExecutionError,
    OutputExistsError,
    Progress,
    input,
    output,
)
from flowmpeg.runner import _TextTail


def test_runner_reports_missing_binary(tmp_path: Path) -> None:
    target = tmp_path / "copy.mp4"
    plan = output(input("movie.mp4").video(), to=target)

    with pytest.raises(BinaryNotFoundError, match="was not found"):
        plan.run(ffmpeg="missing-flowmpeg-ffmpeg")


def test_runner_refuses_existing_output(tmp_path: Path) -> None:
    target = tmp_path / "copy.mp4"
    target.touch()
    plan = output(input("movie.mp4").video(), to=target)

    with pytest.raises(OutputExistsError, match="already exists"):
        plan.run()


def test_runner_rejects_pipe_conflicts() -> None:
    plan = output(input("movie.mp4").video(), to="pipe:1")

    with pytest.raises(ValueError, match="reserves pipes"):
        plan.run()


def test_stderr_tail_keeps_the_latest_text() -> None:
    tail = _TextTail(10)

    tail.append("12345678")
    tail.append("abcde")

    assert tail.text() == "45678abcde"


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

    assert captured.value.returncode != 0
    assert "missing_flowmpeg_codec" in captured.value.stderr
    assert captured.value.command.startswith(ffmpeg)
