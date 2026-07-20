"""Measured media workflows that own more than one FFmpeg pass."""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from dataclasses import dataclass

from flowmpeg import shortcuts
from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import GraphError, OutputExistsError
from flowmpeg.loudness import (
    LoudnessMeasurement,
    _measurement_argv,
    measure_loudness,
)
from flowmpeg.pathing import local_path, same_destination
from flowmpeg.plan import Plan
from flowmpeg.progress import Progress
from flowmpeg.runner import RunResult
from flowmpeg.shortcuts import AudioCodec


@dataclass(frozen=True, slots=True)
class LoudnessWorkflowResult:
    """First-pass measurements and the completed encoding result."""

    measurement: LoudnessMeasurement
    encoding: RunResult


@dataclass(frozen=True, slots=True)
class LoudnessWorkflow:
    """A measured EBU R128 normalization followed by one encoding pass."""

    source: str
    destination: str
    track: int = 0
    target_integrated: float = -16
    target_peak: float = -1.5
    target_range: float = 11
    sample_rate: int = 48_000
    codec: AudioCodec = "wav"
    bitrate: str | None = None
    overwrite: bool = False

    def __post_init__(self) -> None:
        _validate_workflow(self)

    def measurement_command(self, ffmpeg: str = "ffmpeg") -> str:
        """Return the redacted first-pass command without starting FFmpeg."""

        return display_argv(
            _measurement_argv(
                self.source,
                track=self.track,
                target_integrated=self.target_integrated,
                target_peak=self.target_peak,
                target_range=self.target_range,
                ffmpeg=ffmpeg,
            )
        )

    def explain(self, ffmpeg: str = "ffmpeg") -> str:
        """Describe both passes without reading the source."""

        return "\n".join(
            (
                "Pass 1: measure EBU R128 values",
                f"  {self.measurement_command(ffmpeg)}",
                "Pass 2: apply measured values and encode audio",
                f"  output: {redact_text(self.destination)}",
                f"  codec: {self.codec}",
                f"  sample rate: {self.sample_rate} Hz",
                f"Overwrite: {'yes' if self.overwrite else 'no'}",
            )
        )

    def measure(
        self,
        *,
        ffmpeg: str = "ffmpeg",
        timeout: float | None = None,
    ) -> LoudnessMeasurement:
        """Run the analysis pass without writing an output file."""

        return measure_loudness(
            self.source,
            track=self.track,
            target_integrated=self.target_integrated,
            target_peak=self.target_peak,
            target_range=self.target_range,
            ffmpeg=ffmpeg,
            timeout=timeout,
        )

    def plan(self, measurement: LoudnessMeasurement) -> Plan:
        """Build the encoding plan from matching first-pass measurements."""

        _require_matching_measurement(self, measurement)
        return shortcuts.normalize_loudness_measured(
            self.source,
            self.destination,
            measurement,
            track=self.track,
            sample_rate=self.sample_rate,
            codec=self.codec,
            bitrate=self.bitrate,
            overwrite=self.overwrite,
        )

    def run(
        self,
        *,
        ffmpeg: str = "ffmpeg",
        measurement_timeout: float | None = None,
        timeout: float | None = None,
        on_progress: Callable[[Progress], None] | None = None,
        expected_duration: float | None = None,
    ) -> LoudnessWorkflowResult:
        """Measure the source, then encode it with the measured values."""

        _check_existing_output(self)
        measurement = self.measure(ffmpeg=ffmpeg, timeout=measurement_timeout)
        encoding = self.plan(measurement).run(
            ffmpeg=ffmpeg,
            on_progress=on_progress,
            expected_duration=expected_duration,
            timeout=timeout,
        )
        return LoudnessWorkflowResult(measurement, encoding)


def normalize_loudness_two_pass(
    source: str | os.PathLike[str],
    destination: str | os.PathLike[str],
    *,
    track: int = 0,
    target_integrated: float = -16,
    target_peak: float = -1.5,
    target_range: float = 11,
    sample_rate: int = 48_000,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> LoudnessWorkflow:
    """Build a measured loudness workflow without starting either pass."""

    return LoudnessWorkflow(
        os.fspath(source),
        os.fspath(destination),
        track,
        target_integrated,
        target_peak,
        target_range,
        sample_rate,
        codec,
        bitrate,
        overwrite,
    )


def _validate_workflow(workflow: LoudnessWorkflow) -> None:
    if not workflow.source or workflow.source.startswith("-"):
        raise GraphError("Workflow sources cannot be empty or start with a dash")
    if not workflow.destination or workflow.destination.startswith("-"):
        raise GraphError("Workflow outputs cannot be empty or start with a dash")
    if same_destination(workflow.source, workflow.destination):
        raise GraphError("A workflow output cannot replace its input")
    if isinstance(workflow.track, bool) or not isinstance(workflow.track, int):
        raise GraphError("Audio track must be a nonnegative integer")
    if workflow.track < 0:
        raise GraphError("Audio track must be a nonnegative integer")
    _bounded("target integrated loudness", workflow.target_integrated, -70, -5)
    _bounded("target true peak", workflow.target_peak, -9, 0)
    _bounded("target loudness range", workflow.target_range, 1, 50)
    if (
        isinstance(workflow.sample_rate, bool)
        or not isinstance(workflow.sample_rate, int)
        or workflow.sample_rate <= 0
    ):
        raise GraphError("Sample rate must be a positive integer")
    if workflow.codec == "copy":
        raise GraphError("Normalized audio must be encoded")
    if workflow.codec not in {"mp3", "aac", "opus", "wav", "flac"}:
        raise GraphError(f"Unknown audio codec: {workflow.codec}")
    if not isinstance(workflow.overwrite, bool):
        raise GraphError("Overwrite state must be Boolean")


def _require_matching_measurement(
    workflow: LoudnessWorkflow,
    measurement: LoudnessMeasurement,
) -> None:
    if not isinstance(measurement, LoudnessMeasurement):
        raise GraphError("Workflow plans require a loudness measurement")
    if measurement.source != workflow.source or measurement.track != workflow.track:
        raise GraphError("Loudness measurement input must match the workflow")
    expected_targets = (
        workflow.target_integrated,
        workflow.target_peak,
        workflow.target_range,
    )
    measured_targets = (
        measurement.target_integrated_lufs,
        measurement.target_true_peak_dbfs,
        measurement.target_loudness_range_lu,
    )
    if measured_targets != expected_targets:
        raise GraphError("Loudness measurement targets must match the workflow")


def _check_existing_output(workflow: LoudnessWorkflow) -> None:
    path = local_path(workflow.destination)
    if path is not None and os.path.lexists(path) and not workflow.overwrite:
        raise OutputExistsError(f"Output already exists: {workflow.destination}")


def _bounded(name: str, value: float, lower: float, upper: float) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GraphError(f"{name.capitalize()} must be a finite number")
    if not math.isfinite(value) or value < lower or value > upper:
        raise GraphError(
            f"{name.capitalize()} must be at least {lower:g} and at most {upper:g}"
        )


__all__ = [
    "LoudnessWorkflow",
    "LoudnessWorkflowResult",
    "normalize_loudness_two_pass",
]
