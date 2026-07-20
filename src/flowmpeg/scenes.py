"""Typed scene-change timecodes reported by FFmpeg."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass

from flowmpeg.analysis import run_ffmpeg_analysis
from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import BinaryNotFoundError, ExecutionError, GraphError

_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_FRAME = re.compile(rf"\bframe:\s*\d+\s+pts:\s*-?\d+\s+pts_time:\s*({_NUMBER})")
_SCORE = re.compile(rf"\blavfi\.scene_score=({_NUMBER})")


@dataclass(frozen=True, slots=True)
class SceneChange:
    """One scene-change candidate with a time and normalized score."""

    time: float
    score: float


@dataclass(frozen=True, slots=True)
class SceneReport:
    """Scene-change candidates and the threshold used to find them."""

    source: str
    track: int
    threshold: float
    changes: tuple[SceneChange, ...]

    @property
    def strongest_change(self) -> SceneChange | None:
        """Return the highest-scoring scene change, if one exists."""

        if not self.changes:
            return None
        return max(self.changes, key=lambda item: item.score)


def detect_scenes(
    source: str | os.PathLike[str],
    *,
    track: int = 0,
    threshold: float = 0.35,
    ffmpeg: str = "ffmpeg",
    timeout: float | None = None,
) -> SceneReport:
    """Find scene-change candidates without writing an output file."""

    source_text = os.fspath(source)
    if not source_text or source_text.startswith("-"):
        raise GraphError("Scene detection sources cannot be empty or start with a dash")
    if isinstance(track, bool) or not isinstance(track, int) or track < 0:
        raise GraphError("Video track must be a nonnegative integer")
    _bounded("scene threshold", threshold, 0, 1, lower_open=True)
    if timeout is not None:
        _bounded("timeout", timeout, 0, math.inf, lower_open=True)
    if not ffmpeg:
        raise BinaryNotFoundError(
            "The FFmpeg executable cannot be empty",
            tool="ffmpeg",
        )

    scene_filter = f"select=gt(scene\\,{float(threshold):g}),metadata=mode=print"
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
        scene_filter,
        "-f",
        "null",
        "-",
    )
    stderr, returncode = run_ffmpeg_analysis(
        argv,
        timeout=timeout,
        activity="scene detection",
    )
    if returncode != 0:
        raise ExecutionError(
            f"FFmpeg exited with code {returncode} while detecting scenes",
            returncode=returncode,
            stderr=redact_text(stderr)[-8_000:].strip(),
            command=display_argv(argv),
        )
    return SceneReport(
        source=source_text,
        track=track,
        threshold=float(threshold),
        changes=_parse_changes(stderr),
    )


def _parse_changes(stderr: str) -> tuple[SceneChange, ...]:
    changes: list[SceneChange] = []
    pending_time: float | None = None
    for line in stderr.splitlines():
        frame_match = _FRAME.search(line)
        if frame_match is not None:
            pending_time = _finite(frame_match.group(1))
        score_match = _SCORE.search(line)
        if score_match is None or pending_time is None:
            continue
        score = _finite(score_match.group(1))
        if score is not None and pending_time >= 0 and 0 <= score <= 1:
            changes.append(SceneChange(pending_time, score))
        pending_time = None
    return tuple(changes)


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


__all__ = ["SceneChange", "SceneReport", "detect_scenes"]
