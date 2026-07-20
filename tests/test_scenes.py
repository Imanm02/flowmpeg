from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from flowmpeg.errors import GraphError
from flowmpeg.scenes import _parse_changes, detect_scenes


class _FinishedProcess:
    def __init__(self, stderr: str, returncode: int = 0) -> None:
        self.stderr = stderr
        self.returncode = returncode
        self.pid = 123

    def communicate(self, timeout: float | None = None) -> tuple[None, str]:
        del timeout
        return None, self.stderr


def test_detect_scenes_builds_typed_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[tuple[str, ...]] = []
    stderr = """
[metadata] frame:0 pts:10240 pts_time:1
[metadata] lavfi.scene_score=0.400000
[metadata] frame:1 pts:20480 pts_time:2
[metadata] lavfi.scene_score=0.910000
"""

    def start(argv: tuple[str, ...], **kwargs: object) -> _FinishedProcess:
        del kwargs
        started.append(argv)
        return _FinishedProcess(stderr)

    monkeypatch.setattr(subprocess, "Popen", start)

    result = detect_scenes("interview.mp4", track=1, threshold=0.3, timeout=5)

    assert len(result.changes) == 2
    assert result.changes[0].time == 1
    assert result.strongest_change == result.changes[1]
    assert "0:v:1" in started[0]
    assert "select=gt(scene\\,0.3),metadata=mode=print" in started[0]


def test_scene_parser_ignores_unpaired_and_invalid_values() -> None:
    changes = _parse_changes(
        "\n".join(
            (
                "frame:0 pts:1 pts_time:1",
                "lavfi.scene_score=1.5",
                "lavfi.scene_score=0.8",
                "frame:1 pts:2 pts_time:2.5",
                "lavfi.scene_score=0.7",
            )
        )
    )

    assert len(changes) == 1
    assert changes[0].time == 2.5


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track": True},
        {"track": -1},
        {"threshold": 0},
        {"threshold": 1.1},
        {"timeout": float("nan")},
    ],
)
def test_detect_scenes_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        detect_scenes("interview.mp4", **cast(Any, kwargs))


@pytest.mark.integration
def test_detect_scenes_runs_on_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "scene-cuts.mp4"
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
            "color=c=red:s=128x128:d=1:r=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=128x128:d=1:r=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=128x128:d=1:r=10",
            "-filter_complex",
            "[0:v][1:v][2:v]concat=n=3:v=1:a=0[out]",
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-g",
            "100",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ),
        check=True,
    )

    result = detect_scenes(
        source,
        ffmpeg=ffmpeg,
        threshold=0.1,
        timeout=10,
    )

    assert len(result.changes) == 2
    assert result.changes[0].time == pytest.approx(1, abs=0.11)
    assert result.changes[1].time == pytest.approx(2, abs=0.11)
    assert result.strongest_change is not None
    assert result.strongest_change.score >= 0.9
