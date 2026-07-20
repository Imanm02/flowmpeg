"""EBU R128 loudness measurement through FFmpeg."""

from __future__ import annotations

import json
import math
import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import (
    BinaryNotFoundError,
    BinaryUnusableError,
    ExecutionError,
    GraphError,
    JobTimeoutError,
)
from flowmpeg.processes import popen_group_options, stop_process_tree


@dataclass(frozen=True, slots=True)
class LoudnessMeasurement:
    """Measured loudness values and the requested normalization target."""

    source: str
    track: int
    integrated_lufs: float | None
    true_peak_dbfs: float | None
    loudness_range_lu: float | None
    threshold_lufs: float | None
    target_offset_lu: float | None
    target_integrated_lufs: float
    target_true_peak_dbfs: float
    target_loudness_range_lu: float


def measure_loudness(
    source: str | os.PathLike[str],
    *,
    track: int = 0,
    target_integrated: float = -16,
    target_peak: float = -1.5,
    target_range: float = 11,
    ffmpeg: str = "ffmpeg",
    timeout: float | None = None,
) -> LoudnessMeasurement:
    """Measure one audio track without writing an output file."""

    source_text = os.fspath(source)
    if not source_text or source_text.startswith("-"):
        raise GraphError(
            "Loudness sources must be nonempty and cannot start with a dash"
        )
    if isinstance(track, bool) or not isinstance(track, int) or track < 0:
        raise GraphError("Audio track must be a nonnegative integer")
    _bounded("target integrated loudness", target_integrated, -70, -5)
    _bounded("target true peak", target_peak, -9, 0)
    _bounded("target loudness range", target_range, 1, 50)
    if timeout is not None:
        _bounded("timeout", timeout, 0, math.inf, lower_inclusive=False)
    if not ffmpeg:
        raise BinaryNotFoundError(
            "The FFmpeg executable cannot be empty",
            tool="ffmpeg",
        )

    loudnorm = (
        f"loudnorm=I={target_integrated:g}:LRA={target_range:g}:"
        f"TP={target_peak:g}:print_format=json"
    )
    argv = (
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-i",
        source_text,
        "-map",
        f"0:a:{track}",
        "-vn",
        "-sn",
        "-dn",
        "-af",
        loudnorm,
        "-f",
        "null",
        "-",
    )
    stderr, returncode = _run_measurement(argv, timeout)
    if returncode != 0:
        raise ExecutionError(
            f"FFmpeg exited with code {returncode} while measuring loudness",
            returncode=returncode,
            stderr=redact_text(stderr)[-8_000:].strip(),
            command=display_argv(argv),
        )
    values = _loudnorm_values(stderr)
    if values is None:
        raise ExecutionError(
            "FFmpeg did not return loudness measurements",
            returncode=returncode,
            stderr=redact_text(stderr)[-8_000:].strip(),
            command=display_argv(argv),
        )
    return LoudnessMeasurement(
        source=source_text,
        track=track,
        integrated_lufs=_metric(values, "input_i"),
        true_peak_dbfs=_metric(values, "input_tp"),
        loudness_range_lu=_metric(values, "input_lra"),
        threshold_lufs=_metric(values, "input_thresh"),
        target_offset_lu=_metric(values, "target_offset"),
        target_integrated_lufs=float(target_integrated),
        target_true_peak_dbfs=float(target_peak),
        target_loudness_range_lu=float(target_range),
    )


def _run_measurement(
    argv: tuple[str, ...],
    timeout: float | None,
) -> tuple[str, int]:
    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            **popen_group_options(),
        )
    except FileNotFoundError as error:
        raise BinaryNotFoundError(
            f"FFmpeg was not found: {argv[0]}",
            tool="ffmpeg",
        ) from error
    except OSError as error:
        raise BinaryUnusableError(
            f"FFmpeg could not be started: {argv[0]}",
            tool="ffmpeg",
        ) from error
    try:
        _, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        stop_process_tree(process, 2.0)
        raise JobTimeoutError("FFmpeg loudness measurement timed out") from error
    if process.returncode is None:
        raise BinaryUnusableError(
            "FFmpeg ended without a return code",
            tool="ffmpeg",
        )
    return stderr, process.returncode


def _loudnorm_values(stderr: str) -> Mapping[str, object] | None:
    decoder = json.JSONDecoder()
    for index, character in enumerate(stderr):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stderr[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping) and "input_i" in value:
            return cast(Mapping[str, object], value)
    return None


def _metric(values: Mapping[str, object], name: str) -> float | None:
    raw = values.get(name)
    if isinstance(raw, bool) or not isinstance(raw, str | int | float):
        return None
    try:
        value = float(raw)
    except (OverflowError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _bounded(
    name: str,
    value: object,
    lower: float,
    upper: float,
    *,
    lower_inclusive: bool = True,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GraphError(f"{name.capitalize()} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    lower_ok = value >= lower if lower_inclusive else value > lower
    if not finite or not lower_ok or value > upper:
        interval = "through" if lower_inclusive else "above"
        raise GraphError(
            f"{name.capitalize()} must be {interval} {lower:g} and at most {upper:g}"
        )


__all__ = ["LoudnessMeasurement", "measure_loudness"]
