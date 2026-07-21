from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from flowmpeg.demo import DemoMediaResult, generate_demo_media
from flowmpeg.errors import (
    BinaryNotFoundError,
    FlowmpegError,
    JobTimeoutError,
    OutputExistsError,
)


def test_demo_result_has_stable_json_fields(tmp_path: Path) -> None:
    result = DemoMediaResult(
        directory=tmp_path,
        files=(tmp_path / "sample.mp4",),
        video_duration=2.0,
    )

    assert result.as_dict() == {
        "directory": str(tmp_path),
        "files": ["sample.mp4"],
        "video_duration": 2.0,
    }


@pytest.mark.parametrize("timeout", [True, "30", None])
def test_demo_generator_rejects_non_numeric_timeouts(
    tmp_path: Path,
    timeout: object,
) -> None:
    with pytest.raises(TypeError, match="timeout must be a number"):
        generate_demo_media(tmp_path, timeout=timeout)  # type: ignore[arg-type]


@pytest.mark.parametrize("timeout", [0, -1.0])
def test_demo_generator_rejects_nonpositive_timeouts(
    tmp_path: Path,
    timeout: float,
) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        generate_demo_media(tmp_path, timeout=timeout)


def test_demo_generator_reports_missing_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("flowmpeg.demo.shutil.which", lambda value: None)

    with pytest.raises(BinaryNotFoundError, match="ffmpeg executable") as error:
        generate_demo_media(tmp_path)

    assert error.value.tool == "ffmpeg"


def test_demo_generator_protects_existing_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("flowmpeg.demo.shutil.which", lambda value: value)
    (tmp_path / "sample.mp4").write_bytes(b"existing")

    with pytest.raises(OutputExistsError, match="sample.mp4"):
        generate_demo_media(tmp_path)


def test_demo_generator_builds_the_example_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[tuple[str, ...]] = []

    def run(
        command: tuple[str, ...],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        commands.append(command)
        stdout = json.dumps({"format": {"duration": "2.000000"}})
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr("flowmpeg.demo.shutil.which", lambda value: value)
    monkeypatch.setattr("flowmpeg.demo.subprocess.run", run)

    result = generate_demo_media(tmp_path)

    assert result.directory == tmp_path.resolve()
    assert len(result.files) == 12
    assert result.video_duration == 2.0
    assert len(commands) == 9
    assert (
        (tmp_path / "captions.srt")
        .read_text(encoding="utf-8")
        .endswith("Flowmpeg demo caption\n")
    )


def test_demo_generator_maps_process_timeouts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise subprocess.TimeoutExpired(("ffmpeg",), 3)

    monkeypatch.setattr("flowmpeg.demo.shutil.which", lambda value: value)
    monkeypatch.setattr("flowmpeg.demo.subprocess.run", timeout)

    with pytest.raises(JobTimeoutError, match="exceeded 3 seconds"):
        generate_demo_media(tmp_path, timeout=3)


def test_demo_generator_bounds_process_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(
        command: tuple[str, ...],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="first line\nconversion failed",
        )

    monkeypatch.setattr("flowmpeg.demo.shutil.which", lambda value: value)
    monkeypatch.setattr("flowmpeg.demo.subprocess.run", fail)

    with pytest.raises(FlowmpegError, match="conversion failed"):
        generate_demo_media(tmp_path)
