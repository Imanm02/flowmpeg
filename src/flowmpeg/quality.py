"""Typed PSNR and SSIM measurements for matching video streams."""

from __future__ import annotations

import math
import os
import re
import time
from dataclasses import dataclass
from typing import Literal, TypeAlias

from flowmpeg.analysis import run_ffmpeg_analysis
from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import BinaryNotFoundError, ExecutionError, GraphError
from flowmpeg.probe import MediaInfo, VideoStreamInfo, probe

QualityMetric: TypeAlias = Literal["all", "psnr", "ssim", "vmaf"]
_PAIR = re.compile(
    r"\b([A-Za-z]+):([-+]?(?:\d+(?:\.\d*)?|\.\d+|inf))"
    r"(?:\s+\(([-+]?(?:\d+(?:\.\d*)?|\.\d+|inf))\))?",
    re.IGNORECASE,
)
_VMAF = re.compile(
    r"\bVMAF score:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+|inf))",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class QualityComponent:
    """One color or luma component reported by a quality filter."""

    name: str
    value: float
    db: float | None = None


@dataclass(frozen=True, slots=True)
class PsnrScore:
    """Peak signal-to-noise ratio values in decibels."""

    average_db: float
    minimum_db: float
    maximum_db: float
    components: tuple[QualityComponent, ...]


@dataclass(frozen=True, slots=True)
class SsimScore:
    """Structural similarity values and their decibel form."""

    all: float
    db: float
    components: tuple[QualityComponent, ...]


@dataclass(frozen=True, slots=True)
class VmafScore:
    """Video Multi-Method Assessment Fusion score."""

    score: float


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Quality measurements between one reference and one candidate video."""

    reference: str
    candidate: str
    reference_track: int
    candidate_track: int
    width: int
    height: int
    start: float | None
    duration: float | None
    psnr: PsnrScore | None
    ssim: SsimScore | None
    vmaf: VmafScore | None
    elapsed: float


def measure_quality(
    reference: str | os.PathLike[str],
    candidate: str | os.PathLike[str],
    *,
    metric: QualityMetric = "all",
    reference_track: int = 0,
    candidate_track: int = 0,
    start: float | None = None,
    duration: float | None = None,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    timeout: float | None = None,
    probe_timeout: float | None = 10.0,
) -> QualityReport:
    """Measure visual similarity without writing an output file."""

    reference_text = _source("Reference", reference)
    candidate_text = _source("Candidate", candidate)
    if metric not in {"all", "psnr", "ssim", "vmaf"}:
        raise GraphError("Quality metric must be all, psnr, ssim, or vmaf")
    _track("Reference", reference_track)
    _track("Candidate", candidate_track)
    if start is not None:
        _nonnegative("Quality start", start)
    if duration is not None:
        _positive("Quality duration", duration)
    if timeout is not None:
        _positive("Quality timeout", timeout)
    if probe_timeout is not None:
        _positive("Probe timeout", probe_timeout)
    if not ffmpeg:
        raise BinaryNotFoundError(
            "The FFmpeg executable cannot be empty", tool="ffmpeg"
        )
    if not ffprobe:
        raise BinaryNotFoundError(
            "The FFprobe executable cannot be empty",
            tool="ffprobe",
        )

    started = time.monotonic()
    reference_info = probe(
        reference_text,
        ffprobe=ffprobe,
        timeout=probe_timeout,
    )
    candidate_info = probe(
        candidate_text,
        ffprobe=ffprobe,
        timeout=probe_timeout,
    )
    reference_video = _selected_video(
        "Reference",
        reference_info,
        reference_track,
    )
    candidate_video = _selected_video(
        "Candidate",
        candidate_info,
        candidate_track,
    )
    width, height = _matching_dimensions(reference_video, candidate_video)

    psnr = None
    ssim = None
    vmaf = None
    if metric in {"all", "psnr"}:
        argv = _metric_argv(
            reference_text,
            candidate_text,
            reference_track=reference_track,
            candidate_track=candidate_track,
            metric="psnr",
            start=start,
            duration=duration,
            ffmpeg=ffmpeg,
        )
        stderr = _run_metric(argv, "PSNR measurement", timeout)
        psnr = _parse_psnr(stderr)
        if psnr is None:
            raise _missing_measurement("PSNR", argv, stderr)
    if metric in {"all", "ssim"}:
        argv = _metric_argv(
            reference_text,
            candidate_text,
            reference_track=reference_track,
            candidate_track=candidate_track,
            metric="ssim",
            start=start,
            duration=duration,
            ffmpeg=ffmpeg,
        )
        stderr = _run_metric(argv, "SSIM measurement", timeout)
        ssim = _parse_ssim(stderr)
        if ssim is None:
            raise _missing_measurement("SSIM", argv, stderr)
    if metric == "vmaf":
        argv = _metric_argv(
            reference_text,
            candidate_text,
            reference_track=reference_track,
            candidate_track=candidate_track,
            metric="libvmaf",
            start=start,
            duration=duration,
            ffmpeg=ffmpeg,
        )
        stderr = _run_metric(argv, "VMAF measurement", timeout)
        vmaf = _parse_vmaf(stderr)
        if vmaf is None:
            raise _missing_measurement("VMAF", argv, stderr)

    return QualityReport(
        reference_text,
        candidate_text,
        reference_track,
        candidate_track,
        width,
        height,
        None if start is None else float(start),
        None if duration is None else float(duration),
        psnr,
        ssim,
        vmaf,
        time.monotonic() - started,
    )


def _source(name: str, value: str | os.PathLike[str]) -> str:
    text = os.fspath(value)
    if not text or text.startswith("-"):
        raise GraphError(f"{name} sources cannot be empty or start with a dash")
    return text


def _track(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphError(f"{name} video track must be a nonnegative integer")


def _selected_video(name: str, info: MediaInfo, track: int) -> VideoStreamInfo:
    if track >= len(info.video_streams):
        raise GraphError(f"{name} video track {track} does not exist")
    video = info.video_streams[track]
    if video.width is None or video.height is None:
        raise GraphError(f"{name} video dimensions are unknown")
    return video


def _matching_dimensions(
    reference: VideoStreamInfo,
    candidate: VideoStreamInfo,
) -> tuple[int, int]:
    assert reference.width is not None
    assert reference.height is not None
    assert candidate.width is not None
    assert candidate.height is not None
    expected = (reference.width, reference.height)
    actual = (candidate.width, candidate.height)
    if actual != expected:
        raise GraphError(
            "Quality inputs must have matching dimensions: "
            f"reference is {expected[0]}x{expected[1]}, "
            f"candidate is {actual[0]}x{actual[1]}"
        )
    return expected


def _metric_argv(
    reference: str,
    candidate: str,
    *,
    reference_track: int,
    candidate_track: int,
    metric: Literal["psnr", "ssim", "libvmaf"],
    start: float | None,
    duration: float | None,
    ffmpeg: str,
) -> tuple[str, ...]:
    timing: tuple[str, ...] = ()
    if start is not None:
        timing += ("-ss", f"{start:g}")
    if duration is not None:
        timing += ("-t", f"{duration:g}")
    graph = f"[0:v:{candidate_track}][1:v:{reference_track}]{metric}=shortest=1"
    return (
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-nostats",
        *timing,
        "-i",
        candidate,
        *timing,
        "-i",
        reference,
        "-lavfi",
        graph,
        "-an",
        "-sn",
        "-dn",
        "-f",
        "null",
        "-",
    )


def _run_metric(
    argv: tuple[str, ...],
    activity: str,
    timeout: float | None,
) -> str:
    stderr, returncode = run_ffmpeg_analysis(
        argv,
        timeout=timeout,
        activity=activity,
    )
    if returncode != 0:
        raise ExecutionError(
            f"FFmpeg exited with code {returncode} during {activity}",
            returncode=returncode,
            stderr=redact_text(stderr)[-8_000:].strip(),
            command=display_argv(argv),
        )
    return stderr


def _missing_measurement(
    name: str,
    argv: tuple[str, ...],
    stderr: str,
) -> ExecutionError:
    return ExecutionError(
        f"FFmpeg did not return {name} measurements",
        returncode=0,
        stderr=redact_text(stderr)[-8_000:].strip(),
        command=display_argv(argv),
    )


def _parse_psnr(stderr: str) -> PsnrScore | None:
    values = _summary_values(stderr, "PSNR")
    if values is None:
        return None
    average = values.get("average")
    minimum = values.get("min")
    maximum = values.get("max")
    if average is None or minimum is None or maximum is None:
        return None
    components = tuple(
        QualityComponent(name, value)
        for name, (value, _) in values.items()
        if name not in {"average", "min", "max"}
    )
    return PsnrScore(average[0], minimum[0], maximum[0], components)


def _parse_ssim(stderr: str) -> SsimScore | None:
    values = _summary_values(stderr, "SSIM")
    if values is None:
        return None
    all_value = values.get("all")
    if all_value is None or all_value[1] is None:
        return None
    components = tuple(
        QualityComponent(name, value, db)
        for name, (value, db) in values.items()
        if name != "all"
    )
    return SsimScore(all_value[0], all_value[1], components)


def _parse_vmaf(stderr: str) -> VmafScore | None:
    match = next(
        (
            found
            for line in reversed(stderr.splitlines())
            if (found := _VMAF.search(line)) is not None
        ),
        None,
    )
    if match is None:
        return None
    score = _number(match.group(1))
    return None if score is None else VmafScore(score)


def _summary_values(
    stderr: str,
    marker: str,
) -> dict[str, tuple[float, float | None]] | None:
    line = next(
        (value for value in reversed(stderr.splitlines()) if f"{marker} " in value),
        None,
    )
    if line is None:
        return None
    values: dict[str, tuple[float, float | None]] = {}
    for match in _PAIR.finditer(line):
        value = _number(match.group(2))
        db = _number(match.group(3)) if match.group(3) is not None else None
        if value is not None and (match.group(3) is None or db is not None):
            values[match.group(1).casefold()] = (value, db)
    return values or None


def _number(raw: str) -> float | None:
    try:
        value = float(raw)
    except (OverflowError, ValueError):
        return None
    return None if math.isnan(value) or value == -math.inf else value


def _positive(name: str, value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise GraphError(f"{name} must be positive and finite")


def _nonnegative(name: str, value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value < 0
    ):
        raise GraphError(f"{name} must be nonnegative and finite")


__all__ = [
    "PsnrScore",
    "QualityComponent",
    "QualityMetric",
    "QualityReport",
    "SsimScore",
    "VmafScore",
    "measure_quality",
]
