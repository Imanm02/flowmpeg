"""Typed silence intervals reported by FFmpeg."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass

from flowmpeg.analysis import run_ffmpeg_analysis
from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import BinaryNotFoundError, ExecutionError, GraphError

_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_START = re.compile(rf"\bsilence_start:\s*({_NUMBER})")
_END = re.compile(
    rf"\bsilence_end:\s*({_NUMBER})\s*\|\s*silence_duration:\s*({_NUMBER})"
)


@dataclass(frozen=True, slots=True)
class SilenceInterval:
    """One continuous silent range in seconds."""

    start: float
    end: float
    duration: float


@dataclass(frozen=True, slots=True)
class SilenceReport:
    """Silence intervals and the options used to find them."""

    source: str
    track: int
    noise_db: float
    minimum_duration: float
    intervals: tuple[SilenceInterval, ...]

    @property
    def total_silence(self) -> float:
        """Return the sum of all reported silent ranges."""

        return sum(item.duration for item in self.intervals)

    @property
    def longest_silence(self) -> float | None:
        """Return the longest reported range, if one exists."""

        if not self.intervals:
            return None
        return max(item.duration for item in self.intervals)


def detect_silence(
    source: str | os.PathLike[str],
    *,
    track: int = 0,
    noise_db: float = -40,
    minimum_duration: float = 0.5,
    ffmpeg: str = "ffmpeg",
    timeout: float | None = None,
) -> SilenceReport:
    """Find silent ranges in one audio track without writing an output."""

    source_text = os.fspath(source)
    if not source_text or source_text.startswith("-"):
        raise GraphError(
            "Silence sources must be nonempty and cannot start with a dash"
        )
    if isinstance(track, bool) or not isinstance(track, int) or track < 0:
        raise GraphError("Audio track must be a nonnegative integer")
    _bounded("noise level", noise_db, -120, 0)
    _bounded("minimum duration", minimum_duration, 0, math.inf, lower_open=True)
    if timeout is not None:
        _bounded("timeout", timeout, 0, math.inf, lower_open=True)
    if not ffmpeg:
        raise BinaryNotFoundError(
            "The FFmpeg executable cannot be empty",
            tool="ffmpeg",
        )

    silence_filter = (
        f"silencedetect=noise={float(noise_db):g}dB:d={float(minimum_duration):g}"
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
        silence_filter,
        "-f",
        "null",
        "-",
    )
    stderr, returncode = run_ffmpeg_analysis(
        argv,
        timeout=timeout,
        activity="silence detection",
    )
    if returncode != 0:
        raise ExecutionError(
            f"FFmpeg exited with code {returncode} while detecting silence",
            returncode=returncode,
            stderr=redact_text(stderr)[-8_000:].strip(),
            command=display_argv(argv),
        )
    return SilenceReport(
        source=source_text,
        track=track,
        noise_db=float(noise_db),
        minimum_duration=float(minimum_duration),
        intervals=_parse_intervals(stderr),
    )


def _parse_intervals(stderr: str) -> tuple[SilenceInterval, ...]:
    intervals: list[SilenceInterval] = []
    pending_start: float | None = None
    for line in stderr.splitlines():
        start_match = _START.search(line)
        if start_match is not None:
            pending_start = _finite(start_match.group(1))
        end_match = _END.search(line)
        if end_match is None:
            continue
        end = _finite(end_match.group(1))
        duration = _finite(end_match.group(2))
        if end is None or duration is None or duration < 0:
            pending_start = None
            continue
        start = pending_start if pending_start is not None else end - duration
        pending_start = None
        if start is None or start < 0 or end < start:
            continue
        intervals.append(SilenceInterval(start, end, duration))
    return tuple(intervals)


def _finite(raw: str) -> float | None:
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
    lower_open: bool = False,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GraphError(f"{name.capitalize()} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    lower_ok = value > lower if lower_open else value >= lower
    if not finite or not lower_ok or value > upper:
        relation = "greater than" if lower_open else "at least"
        raise GraphError(
            f"{name.capitalize()} must be {relation} {lower:g} and at most {upper:g}"
        )


__all__ = ["SilenceInterval", "SilenceReport", "detect_silence"]
