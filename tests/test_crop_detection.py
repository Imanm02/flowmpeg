from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from flowmpeg.crop_detection import _parse_candidates, detect_crop
from flowmpeg.errors import GraphError


class _FinishedProcess:
    def __init__(self, stderr: str, returncode: int = 0) -> None:
        self.stderr = stderr
        self.returncode = returncode
        self.pid = 123

    def communicate(self, timeout: float | None = None) -> tuple[None, str]:
        del timeout
        return None, self.stderr


def test_detect_crop_ranks_repeated_rectangles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[tuple[str, ...]] = []
    stderr = "\n".join(
        (
            "crop=120:100:20:10",
            "crop=118:100:22:10",
            "crop=120:100:20:10",
            "crop=120:100:20:10",
        )
    )

    def start(argv: tuple[str, ...], **kwargs: object) -> _FinishedProcess:
        del kwargs
        started.append(argv)
        return _FinishedProcess(stderr)

    monkeypatch.setattr(subprocess, "Popen", start)

    result = detect_crop(
        "letterboxed.mp4",
        track=1,
        limit=20,
        round_to=4,
        skip_frames=3,
        start=10,
        duration=20,
        timeout=5,
    )

    assert result.sample_count == 4
    assert result.recommended is not None
    assert result.recommended.filter_value == "crop=120:100:20:10"
    assert result.agreement == 0.75
    assert "0:v:1" in started[0]
    assert "cropdetect=limit=20:round=4:skip=3:reset=0" in started[0]
    assert started[0][started[0].index("-ss") + 1] == "10"
    assert started[0][started[0].index("-t") + 1] == "20"


def test_crop_parser_ignores_invalid_rectangles_and_breaks_ties_by_area() -> None:
    candidates, samples = _parse_candidates(
        "\n".join(
            (
                "crop=100:80:10:10",
                "crop=120:90:5:5",
                "crop=0:90:5:5",
                "crop=100:80:-1:10",
            )
        )
    )

    assert samples == 2
    assert candidates[0].filter_value == "crop=120:90:5:5"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track": True},
        {"track": -1},
        {"limit": -1},
        {"limit": 65_536},
        {"round_to": 0},
        {"skip_frames": True},
        {"start": -0.1},
        {"duration": 0},
        {"timeout": float("nan")},
    ],
)
def test_detect_crop_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        detect_crop("letterboxed.mp4", **cast(Any, kwargs))


@pytest.mark.integration
def test_detect_crop_runs_on_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "bordered.mp4"
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
            "color=c=black:s=160x120:d=1:r=10",
            "-vf",
            "drawbox=x=20:y=10:w=120:h=100:color=white:t=fill",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ),
        check=True,
    )

    result = detect_crop(source, ffmpeg=ffmpeg, duration=1, timeout=10)

    assert result.sample_count > 0
    assert result.recommended is not None
    assert result.recommended.width == 120
    assert result.recommended.height == 100
    assert result.recommended.x == 20
    assert result.recommended.y == 10
    assert result.agreement == 1
