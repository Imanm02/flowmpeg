from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from flowmpeg.errors import GraphError
from flowmpeg.silence import _parse_intervals, detect_silence


class _FinishedProcess:
    def __init__(self, stderr: str, returncode: int = 0) -> None:
        self.stderr = stderr
        self.returncode = returncode
        self.pid = 123

    def communicate(self, timeout: float | None = None) -> tuple[None, str]:
        del timeout
        return None, self.stderr


def test_detect_silence_builds_typed_intervals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[tuple[str, ...]] = []
    stderr = """
[silencedetect] silence_start: 0
[silencedetect] silence_end: 0.72 | silence_duration: 0.72
[silencedetect] silence_start: 5.25
[silencedetect] silence_end: 7.5 | silence_duration: 2.25
"""

    def start(argv: tuple[str, ...], **kwargs: object) -> _FinishedProcess:
        del kwargs
        started.append(argv)
        return _FinishedProcess(stderr)

    monkeypatch.setattr(subprocess, "Popen", start)

    result = detect_silence(
        "interview.wav",
        track=1,
        noise_db=-45,
        minimum_duration=0.4,
        timeout=5,
    )

    assert len(result.intervals) == 2
    assert result.intervals[1].start == 5.25
    assert result.total_silence == pytest.approx(2.97)
    assert result.longest_silence == 2.25
    assert "0:a:1" in started[0]
    assert "silencedetect=noise=-45dB:d=0.4" in started[0]


def test_silence_parser_recovers_an_interval_without_a_start() -> None:
    intervals = _parse_intervals(
        "[silencedetect] silence_end: 4.5 | silence_duration: 1.25"
    )

    assert len(intervals) == 1
    assert intervals[0].start == 3.25
    assert intervals[0].end == 4.5


def test_silence_parser_ignores_invalid_and_unfinished_ranges() -> None:
    intervals = _parse_intervals(
        "\n".join(
            (
                "silence_start: 1",
                "silence_end: 0.5 | silence_duration: -0.5",
                "silence_start: 4",
            )
        )
    )

    assert intervals == ()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track": True},
        {"track": -1},
        {"noise_db": -121},
        {"noise_db": 1},
        {"minimum_duration": 0},
        {"timeout": float("nan")},
    ],
)
def test_detect_silence_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        detect_silence("interview.wav", **cast(Any, kwargs))


@pytest.mark.integration
def test_detect_silence_runs_on_generated_audio(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "gapped.wav"
    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=8000:cl=mono:d=0.7",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.8:sample_rate=8000",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=8000:cl=mono:d=0.6",
            "-filter_complex",
            "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
            "-map",
            "[out]",
            str(source),
        ),
        check=True,
    )

    result = detect_silence(
        source,
        ffmpeg=ffmpeg,
        noise_db=-40,
        minimum_duration=0.3,
        timeout=10,
    )

    assert len(result.intervals) == 2
    assert result.intervals[0].start == pytest.approx(0, abs=0.01)
    assert result.intervals[0].end == pytest.approx(0.7, abs=0.02)
    assert result.intervals[1].start == pytest.approx(1.5, abs=0.02)
    assert result.total_silence == pytest.approx(1.3, abs=0.03)
