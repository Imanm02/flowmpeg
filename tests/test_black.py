from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from flowmpeg.black import _parse_intervals, detect_black
from flowmpeg.errors import GraphError


class _FinishedProcess:
    def __init__(self, stderr: str, returncode: int = 0) -> None:
        self.stderr = stderr
        self.returncode = returncode
        self.pid = 123

    def communicate(self, timeout: float | None = None) -> tuple[None, str]:
        del timeout
        return None, self.stderr


def test_detect_black_builds_typed_intervals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[tuple[str, ...]] = []
    stderr = """
[blackdetect] black_start:0 black_end:0.7 black_duration:0.7
[blackdetect] black_start:5.2 black_end:7.4 black_duration:2.2
"""

    def start(argv: tuple[str, ...], **kwargs: object) -> _FinishedProcess:
        del kwargs
        started.append(argv)
        return _FinishedProcess(stderr)

    monkeypatch.setattr(subprocess, "Popen", start)

    result = detect_black(
        "tape.mp4",
        track=1,
        picture_ratio=0.95,
        pixel_threshold=0.12,
        minimum_duration=0.4,
        timeout=5,
    )

    assert len(result.intervals) == 2
    assert result.intervals[1].start == 5.2
    assert result.total_black == pytest.approx(2.9)
    assert result.longest_black == 2.2
    assert "0:v:1" in started[0]
    assert "blackdetect=d=0.4:pic_th=0.95:pix_th=0.12" in started[0]


def test_black_parser_ignores_invalid_ranges() -> None:
    intervals = _parse_intervals(
        "\n".join(
            (
                "black_start:1 black_end:0.5 black_duration:-0.5",
                "black_start:nan black_end:2 black_duration:1",
                "black_start:3 black_end:4 black_duration:1",
            )
        )
    )

    assert len(intervals) == 1
    assert intervals[0].start == 3


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track": True},
        {"track": -1},
        {"picture_ratio": -0.1},
        {"picture_ratio": 1.1},
        {"pixel_threshold": -0.1},
        {"pixel_threshold": 1.1},
        {"minimum_duration": 0},
        {"timeout": float("nan")},
    ],
)
def test_detect_black_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        detect_black("tape.mp4", **cast(Any, kwargs))


@pytest.mark.integration
def test_detect_black_runs_on_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "black-ranges.mp4"
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
            "color=c=black:s=128x128:d=0.7:r=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=128x128:d=0.8:r=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=128x128:d=0.6:r=10",
            "-filter_complex",
            "[0:v][1:v][2:v]concat=n=3:v=1:a=0[out]",
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ),
        check=True,
    )

    result = detect_black(
        source,
        ffmpeg=ffmpeg,
        minimum_duration=0.3,
        timeout=10,
    )

    assert len(result.intervals) == 2
    assert result.intervals[0].start == pytest.approx(0, abs=0.01)
    assert result.intervals[0].end == pytest.approx(0.7, abs=0.11)
    assert result.intervals[1].start == pytest.approx(1.5, abs=0.11)
    assert result.total_black > 1.0
