"""Rank crop rectangles reported by FFmpeg."""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass

from flowmpeg.analysis import run_ffmpeg_analysis
from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import BinaryNotFoundError, ExecutionError, GraphError

_CROP = re.compile(r"\bcrop=(\d+):(\d+):(-?\d+):(-?\d+)")


@dataclass(frozen=True, slots=True)
class CropCandidate:
    """One crop rectangle and the number of matching frame samples."""

    width: int
    height: int
    x: int
    y: int
    samples: int

    @property
    def filter_value(self) -> str:
        """Return the rectangle in FFmpeg crop-filter order."""

        return f"crop={self.width}:{self.height}:{self.x}:{self.y}"


@dataclass(frozen=True, slots=True)
class CropReport:
    """Ranked crop candidates and the scan options that produced them."""

    source: str
    track: int
    limit: float
    round_to: int
    skip_frames: int
    start: float | None
    duration: float | None
    sample_count: int
    candidates: tuple[CropCandidate, ...]

    @property
    def recommended(self) -> CropCandidate | None:
        """Return the most frequently reported rectangle, if one exists."""

        return self.candidates[0] if self.candidates else None

    @property
    def agreement(self) -> float | None:
        """Return the fraction of samples matching the recommendation."""

        if self.recommended is None or self.sample_count == 0:
            return None
        return self.recommended.samples / self.sample_count

    def recommended_json(self) -> dict[str, int | str] | None:
        """Return JSON-ready recommendation fields."""

        if self.recommended is None:
            return None
        data: dict[str, int | str] = asdict(self.recommended)
        data["filter_value"] = self.recommended.filter_value
        return data


def detect_crop(
    source: str | os.PathLike[str],
    *,
    track: int = 0,
    limit: float = 24,
    round_to: int = 2,
    skip_frames: int = 2,
    start: float | None = None,
    duration: float | None = 60,
    ffmpeg: str = "ffmpeg",
    timeout: float | None = None,
) -> CropReport:
    """Rank crop rectangles without writing an output file."""

    source_text = os.fspath(source)
    if not source_text or source_text.startswith("-"):
        raise GraphError("Crop detection sources cannot be empty or start with a dash")
    _nonnegative_integer("video track", track)
    _bounded("crop limit", limit, 0, 65_535)
    _positive_integer("crop rounding", round_to)
    _nonnegative_integer("skipped frames", skip_frames)
    if start is not None:
        _bounded("scan start", start, 0, math.inf)
    if duration is not None:
        _bounded("scan duration", duration, 0, math.inf, lower_open=True)
    if timeout is not None:
        _bounded("timeout", timeout, 0, math.inf, lower_open=True)
    if not ffmpeg:
        raise BinaryNotFoundError(
            "The FFmpeg executable cannot be empty",
            tool="ffmpeg",
        )

    crop_filter = (
        f"cropdetect=limit={float(limit):g}:round={round_to}:skip={skip_frames}:reset=0"
    )
    argv_parts = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-i",
        source_text,
    ]
    if start is not None:
        argv_parts.extend(("-ss", f"{float(start):g}"))
    if duration is not None:
        argv_parts.extend(("-t", f"{float(duration):g}"))
    argv_parts.extend(
        (
            "-map",
            f"0:v:{track}",
            "-an",
            "-sn",
            "-dn",
            "-vf",
            crop_filter,
            "-f",
            "null",
            "-",
        )
    )
    argv = tuple(argv_parts)
    stderr, returncode = run_ffmpeg_analysis(
        argv,
        timeout=timeout,
        activity="crop detection",
    )
    if returncode != 0:
        raise ExecutionError(
            f"FFmpeg exited with code {returncode} while detecting a crop",
            returncode=returncode,
            stderr=redact_text(stderr)[-8_000:].strip(),
            command=display_argv(argv),
        )
    candidates, sample_count = _parse_candidates(stderr)
    return CropReport(
        source=source_text,
        track=track,
        limit=float(limit),
        round_to=round_to,
        skip_frames=skip_frames,
        start=None if start is None else float(start),
        duration=None if duration is None else float(duration),
        sample_count=sample_count,
        candidates=candidates,
    )


def _parse_candidates(stderr: str) -> tuple[tuple[CropCandidate, ...], int]:
    counts: Counter[tuple[int, int, int, int]] = Counter()
    for match in _CROP.finditer(stderr):
        width, height, x, y = (int(value) for value in match.groups())
        if width <= 0 or height <= 0 or x < 0 or y < 0:
            continue
        counts[(width, height, x, y)] += 1
    ranked = sorted(
        counts.items(),
        key=lambda item: (-item[1], -(item[0][0] * item[0][1]), item[0]),
    )
    candidates = tuple(
        CropCandidate(width, height, x, y, samples)
        for (width, height, x, y), samples in ranked
    )
    return candidates, sum(counts.values())


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


def _positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GraphError(f"{name.capitalize()} must be a positive integer")


def _nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphError(f"{name.capitalize()} must be a nonnegative integer")


__all__ = ["CropCandidate", "CropReport", "detect_crop"]
