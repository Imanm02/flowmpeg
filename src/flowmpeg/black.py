"""Typed black video intervals reported by FFmpeg."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass

from flowmpeg.analysis import run_ffmpeg_analysis
from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import BinaryNotFoundError, ExecutionError, GraphError

_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_INTERVAL = re.compile(
    rf"\bblack_start:({_NUMBER})\s+black_end:({_NUMBER})\s+"
    rf"black_duration:({_NUMBER})"
)


@dataclass(frozen=True, slots=True)
class BlackInterval:
    """One continuous black picture range in seconds."""

    start: float
    end: float
    duration: float


@dataclass(frozen=True, slots=True)
class BlackReport:
    """Black intervals and the options used to find them."""

    source: str
    track: int
    picture_ratio: float
    pixel_threshold: float
    minimum_duration: float
    intervals: tuple[BlackInterval, ...]

    @property
    def total_black(self) -> float:
        """Return the sum of all reported black ranges."""

        return sum(item.duration for item in self.intervals)

    @property
    def longest_black(self) -> float | None:
        """Return the longest reported range, if one exists."""

        if not self.intervals:
            return None
        return max(item.duration for item in self.intervals)


def detect_black(
    source: str | os.PathLike[str],
    *,
    track: int = 0,
    picture_ratio: float = 0.98,
    pixel_threshold: float = 0.1,
    minimum_duration: float = 0.5,
    ffmpeg: str = "ffmpeg",
    timeout: float | None = None,
) -> BlackReport:
    """Find black ranges in one video track without writing an output."""

    source_text = os.fspath(source)
    if not source_text or source_text.startswith("-"):
        raise GraphError("Black detection sources cannot be empty or start with a dash")
    if isinstance(track, bool) or not isinstance(track, int) or track < 0:
        raise GraphError("Video track must be a nonnegative integer")
    _bounded("picture ratio", picture_ratio, 0, 1)
    _bounded("pixel threshold", pixel_threshold, 0, 1)
    _bounded("minimum duration", minimum_duration, 0, math.inf, lower_open=True)
    if timeout is not None:
        _bounded("timeout", timeout, 0, math.inf, lower_open=True)
    if not ffmpeg:
        raise BinaryNotFoundError(
            "The FFmpeg executable cannot be empty",
            tool="ffmpeg",
        )

    black_filter = (
        f"blackdetect=d={float(minimum_duration):g}:"
        f"pic_th={float(picture_ratio):g}:pix_th={float(pixel_threshold):g}"
    )
    argv = (
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-i",
        source_text,
        "-map",
        f"0:v:{track}",
        "-an",
        "-sn",
        "-dn",
        "-vf",
        black_filter,
        "-f",
        "null",
        "-",
    )
    stderr, returncode = run_ffmpeg_analysis(
        argv,
        timeout=timeout,
        activity="black frame detection",
    )
    if returncode != 0:
        raise ExecutionError(
            f"FFmpeg exited with code {returncode} while detecting black frames",
            returncode=returncode,
            stderr=redact_text(stderr)[-8_000:].strip(),
            command=display_argv(argv),
        )
    return BlackReport(
        source=source_text,
        track=track,
        picture_ratio=float(picture_ratio),
        pixel_threshold=float(pixel_threshold),
        minimum_duration=float(minimum_duration),
        intervals=_parse_intervals(stderr),
    )


def _parse_intervals(stderr: str) -> tuple[BlackInterval, ...]:
    intervals: list[BlackInterval] = []
    for match in _INTERVAL.finditer(stderr):
        start = _finite(match.group(1))
        end = _finite(match.group(2))
        duration = _finite(match.group(3))
        if (
            start is None
            or end is None
            or duration is None
            or start < 0
            or end < start
            or duration < 0
        ):
            continue
        intervals.append(BlackInterval(start, end, duration))
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


__all__ = ["BlackInterval", "BlackReport", "detect_black"]
