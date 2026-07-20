from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from flowmpeg.errors import GraphError
from flowmpeg.loudness import _loudnorm_values, measure_loudness


class _FinishedProcess:
    def __init__(self, stderr: str, returncode: int = 0) -> None:
        self.stderr = stderr
        self.returncode = returncode
        self.pid = 123

    def communicate(self, timeout: float | None = None) -> tuple[None, str]:
        del timeout
        return None, self.stderr


def test_measure_loudness_parses_ffmpeg_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[tuple[str, ...]] = []
    stderr = """
[Parsed_loudnorm_0] {
    "input_i" : "-20.42",
    "input_tp" : "-3.10",
    "input_lra" : "4.20",
    "input_thresh" : "-30.50",
    "target_offset" : "0.14"
}
"""

    def start(argv: tuple[str, ...], **kwargs: object) -> _FinishedProcess:
        del kwargs
        started.append(argv)
        return _FinishedProcess(stderr)

    monkeypatch.setattr(subprocess, "Popen", start)

    result = measure_loudness("episode.wav", track=1, timeout=5)

    assert result.integrated_lufs == -20.42
    assert result.true_peak_dbfs == -3.1
    assert result.loudness_range_lu == 4.2
    assert result.target_offset_lu == 0.14
    assert "0:a:1" in started[0]
    assert "print_format=json" in " ".join(started[0])


def test_loudness_parser_treats_infinite_values_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = _loudnorm_values('{"input_i":"-inf","input_tp":"-inf"}')

    assert values is not None
    process = _FinishedProcess(
        '{"input_i":"-inf","input_tp":"-inf","input_lra":"0",'
        '"input_thresh":"-70","target_offset":"inf"}'
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    result = measure_loudness("silence.wav")
    assert result.integrated_lufs is None
    assert result.true_peak_dbfs is None
    assert result.target_offset_lu is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track": True},
        {"track": -1},
        {"target_integrated": -71},
        {"target_peak": 1},
        {"target_range": 0},
        {"timeout": float("nan")},
    ],
)
def test_measure_loudness_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        measure_loudness("episode.wav", **cast(Any, kwargs))


@pytest.mark.integration
def test_measure_loudness_runs_on_generated_audio(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "tone.wav"
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
            "sine=frequency=440:duration=3",
            str(source),
        ),
        check=True,
    )

    result = measure_loudness(source, ffmpeg=ffmpeg, timeout=10)

    assert result.integrated_lufs is not None
    assert result.true_peak_dbfs is not None
    assert result.target_integrated_lufs == -16
