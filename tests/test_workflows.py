from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from flowmpeg.errors import GraphError, OutputExistsError
from flowmpeg.loudness import LoudnessMeasurement, measure_loudness
from flowmpeg.plan import Plan
from flowmpeg.runner import RunResult
from flowmpeg.workflows import (
    LoudnessWorkflowResult,
    normalize_loudness_two_pass,
)


def _measurement(
    *,
    source: str = "voice.wav",
    track: int = 0,
    target_integrated: float = -16,
) -> LoudnessMeasurement:
    return LoudnessMeasurement(
        source=source,
        track=track,
        integrated_lufs=-21.4,
        true_peak_dbfs=-5.2,
        loudness_range_lu=2.1,
        threshold_lufs=-31.8,
        target_offset_lu=0.2,
        target_integrated_lufs=target_integrated,
        target_true_peak_dbfs=-1.5,
        target_loudness_range_lu=11,
    )


def test_two_pass_workflow_builds_exact_second_pass() -> None:
    workflow = normalize_loudness_two_pass("voice.wav", "exact.wav")

    plan = workflow.plan(_measurement())
    graph = plan.filter_graph()

    assert graph is not None
    assert "measured_I=-21.4" in graph
    assert "measured_LRA=2.1" in graph
    assert "measured_TP=-5.2" in graph
    assert "measured_thresh=-31.8" in graph
    assert "offset=0.2" in graph
    assert "linear=1" in graph
    assert plan.raw_argv()[-3:] == ("-c:a", "pcm_s16le", "exact.wav")


def test_workflow_explains_first_pass_without_running() -> None:
    workflow = normalize_loudness_two_pass("voice.wav", "exact.wav")

    explanation = workflow.explain("custom-ffmpeg")

    assert "Pass 1: measure EBU R128 values" in explanation
    assert "custom-ffmpeg" in explanation
    assert "print_format=json" in explanation
    assert "Pass 2: apply measured values" in explanation


def test_workflow_rejects_mismatched_measurement() -> None:
    workflow = normalize_loudness_two_pass("voice.wav", "exact.wav")

    with pytest.raises(GraphError, match="input must match"):
        workflow.plan(_measurement(source="other.wav"))
    with pytest.raises(GraphError, match="targets must match"):
        workflow.plan(_measurement(target_integrated=-23))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track": True},
        {"track": -1},
        {"target_integrated": -80},
        {"target_peak": 1},
        {"target_range": True},
        {"sample_rate": 0},
        {"codec": "copy"},
        {"codec": "alac"},
        {"overwrite": 1},
    ],
)
def test_workflow_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        normalize_loudness_two_pass("voice.wav", "exact.wav", **cast(Any, kwargs))


def test_workflow_checks_existing_output_before_measurement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "exact.wav"
    target.touch()
    workflow = normalize_loudness_two_pass("voice.wav", target)
    measured = False

    def measurement(*args: object, **kwargs: object) -> LoudnessMeasurement:
        nonlocal measured
        measured = True
        return _measurement()

    monkeypatch.setattr("flowmpeg.workflows.measure_loudness", measurement)

    with pytest.raises(OutputExistsError):
        workflow.run()
    assert not measured


def test_workflow_runs_measurement_then_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = normalize_loudness_two_pass("voice.wav", "exact.wav")
    measurement = _measurement()
    encoded = RunResult(0, 1.25, "", None, ("exact.wav",))
    calls: list[str] = []

    def measure(*args: object, **kwargs: object) -> LoudnessMeasurement:
        calls.append("measure")
        return measurement

    def run(self: Plan, **kwargs: object) -> RunResult:
        calls.append("encode")
        return encoded

    monkeypatch.setattr("flowmpeg.workflows.measure_loudness", measure)
    monkeypatch.setattr(Plan, "run", run)

    result = workflow.run(measurement_timeout=10, timeout=20)

    assert result == LoudnessWorkflowResult(measurement, encoded)
    assert calls == ["measure", "encode"]


@pytest.mark.integration
def test_two_pass_workflow_normalizes_generated_audio(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "quiet.wav"
    target = tmp_path / "exact.wav"
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
            "-af",
            "volume=0.2",
            str(source),
        ),
        check=True,
    )
    workflow = normalize_loudness_two_pass(
        source,
        target,
        target_integrated=-18,
    )

    result = workflow.run(
        ffmpeg=ffmpeg,
        measurement_timeout=15,
        timeout=15,
    )
    after = measure_loudness(
        target,
        target_integrated=-18,
        ffmpeg=ffmpeg,
        timeout=15,
    )

    assert target.exists()
    assert result.measurement.integrated_lufs is not None
    assert after.integrated_lufs == pytest.approx(-18, abs=0.5)
