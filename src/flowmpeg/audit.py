"""Opinionated checks over typed FFprobe results."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from flowmpeg.probe import MediaInfo

AuditExpectation = Literal["any", "video", "audio", "av"]
AuditSeverity = Literal["warning", "error"]
AuditThreshold = Literal["never", "error", "warning"]
AUDIT_CODES = (
    "AUD001",
    "AUD101",
    "AUD102",
    "AUD201",
    "AUD202",
    "AUD203",
    "AUD204",
    "AUD211",
    "AUD212",
    "AUD213",
    "AUD214",
    "AUD215",
    "AUD216",
    "AUD217",
    "AUD221",
    "AUD222",
    "AUD223",
    "AUD224",
    "AUD225",
    "AUD226",
)


@dataclass(frozen=True, slots=True)
class AuditFinding:
    """One stable media audit result."""

    code: str
    severity: AuditSeverity
    message: str


@dataclass(frozen=True, slots=True)
class AuditConstraints:
    """Optional delivery values that an audit must match."""

    minimum_duration: float | None = None
    maximum_duration: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None


@dataclass(frozen=True, slots=True)
class AuditSummary:
    """Small media shape used by terminal and JSON reports."""

    container: str | None
    duration: float | None
    size: int | None
    video_streams: int
    audio_streams: int
    subtitle_streams: int
    width: int | None
    height: int | None
    frame_rate: float | None
    video_codec: str | None
    sample_rate: int | None
    channels: int | None
    audio_codec: str | None


@dataclass(frozen=True, slots=True)
class MediaAudit:
    """Summary and findings for one probed input."""

    expectation: AuditExpectation
    summary: AuditSummary
    findings: tuple[AuditFinding, ...]
    constraints: AuditConstraints = AuditConstraints()

    def passes(self, fail_on: AuditThreshold = "error") -> bool:
        """Return whether findings stay below a selected threshold."""

        if fail_on == "never":
            return True
        if fail_on == "warning":
            return not self.findings
        if fail_on == "error":
            return not any(item.severity == "error" for item in self.findings)
        raise ValueError(f"Unknown audit threshold: {fail_on}")


def audit_media(
    info: MediaInfo,
    *,
    expect: AuditExpectation = "any",
    constraints: AuditConstraints | None = None,
) -> MediaAudit:
    """Check a typed probe result against a requested stream shape."""

    if expect not in {"any", "video", "audio", "av"}:
        raise ValueError(f"Unknown audit expectation: {expect}")
    policy = AuditConstraints() if constraints is None else constraints
    _validate_constraints(policy)
    videos = info.video_streams
    audios = info.audio_streams
    subtitles = info.subtitle_streams
    first_video = videos[0] if videos else None
    first_audio = audios[0] if audios else None
    frame_rate = None
    if first_video is not None and first_video.average_frame_rate is not None:
        frame_rate = float(first_video.average_frame_rate)
    summary = AuditSummary(
        container=(
            None
            if info.format is None
            else info.format.format_long_name or info.format.format_name
        ),
        duration=info.duration,
        size=None if info.format is None else info.format.size,
        video_streams=len(videos),
        audio_streams=len(audios),
        subtitle_streams=len(subtitles),
        width=None if first_video is None else first_video.width,
        height=None if first_video is None else first_video.height,
        frame_rate=frame_rate,
        video_codec=None if first_video is None else first_video.codec_name,
        sample_rate=None if first_audio is None else first_audio.sample_rate,
        channels=None if first_audio is None else first_audio.channels,
        audio_codec=None if first_audio is None else first_audio.codec_name,
    )
    findings: list[AuditFinding] = []
    if not info.streams:
        findings.append(AuditFinding("AUD001", "error", "No media streams found"))
    if expect in {"video", "av"} and not videos:
        findings.append(AuditFinding("AUD101", "error", "Expected a video stream"))
    if expect in {"audio", "av"} and not audios:
        findings.append(AuditFinding("AUD102", "error", "Expected an audio stream"))
    if info.format is None:
        findings.append(
            AuditFinding("AUD201", "warning", "Container details are unavailable")
        )
    if info.duration is None or info.duration <= 0:
        findings.append(
            AuditFinding("AUD202", "warning", "Duration is missing or nonpositive")
        )
    if policy.minimum_duration is not None and (
        info.duration is None or info.duration < policy.minimum_duration
    ):
        findings.append(
            AuditFinding(
                "AUD203",
                "error",
                _expected(
                    "Duration", info.duration, f"at least {policy.minimum_duration:g}s"
                ),
            )
        )
    if policy.maximum_duration is not None and (
        info.duration is None or info.duration > policy.maximum_duration
    ):
        findings.append(
            AuditFinding(
                "AUD204",
                "error",
                _expected(
                    "Duration", info.duration, f"at most {policy.maximum_duration:g}s"
                ),
            )
        )
    if first_video is not None:
        if first_video.codec_name is None:
            findings.append(AuditFinding("AUD211", "warning", "Video codec is unknown"))
        if first_video.width is None or first_video.height is None:
            findings.append(
                AuditFinding("AUD212", "warning", "Video dimensions are incomplete")
            )
        elif first_video.width % 2 or first_video.height % 2:
            findings.append(
                AuditFinding(
                    "AUD213",
                    "warning",
                    "Video dimensions are odd and may block common encoders",
                )
            )
        if frame_rate is None or frame_rate <= 0:
            findings.append(
                AuditFinding("AUD214", "warning", "Video frame rate is unavailable")
            )
    if policy.width is not None and summary.width != policy.width:
        findings.append(
            AuditFinding(
                "AUD215",
                "error",
                _expected("Video width", summary.width, str(policy.width)),
            )
        )
    if policy.height is not None and summary.height != policy.height:
        findings.append(
            AuditFinding(
                "AUD216",
                "error",
                _expected("Video height", summary.height, str(policy.height)),
            )
        )
    if policy.video_codec is not None and not _codec_matches(
        summary.video_codec, policy.video_codec
    ):
        findings.append(
            AuditFinding(
                "AUD217",
                "error",
                _expected("Video codec", summary.video_codec, policy.video_codec),
            )
        )
    if first_audio is not None:
        if first_audio.codec_name is None:
            findings.append(AuditFinding("AUD221", "warning", "Audio codec is unknown"))
        if first_audio.sample_rate is None or first_audio.sample_rate <= 0:
            findings.append(
                AuditFinding("AUD222", "warning", "Audio sample rate is unavailable")
            )
        if first_audio.channels is None or first_audio.channels <= 0:
            findings.append(
                AuditFinding("AUD223", "warning", "Audio channel count is unavailable")
            )
    if policy.audio_codec is not None and not _codec_matches(
        summary.audio_codec, policy.audio_codec
    ):
        findings.append(
            AuditFinding(
                "AUD224",
                "error",
                _expected("Audio codec", summary.audio_codec, policy.audio_codec),
            )
        )
    if policy.sample_rate is not None and summary.sample_rate != policy.sample_rate:
        findings.append(
            AuditFinding(
                "AUD225",
                "error",
                _expected(
                    "Audio sample rate", summary.sample_rate, str(policy.sample_rate)
                ),
            )
        )
    if policy.channels is not None and summary.channels != policy.channels:
        findings.append(
            AuditFinding(
                "AUD226",
                "error",
                _expected("Audio channels", summary.channels, str(policy.channels)),
            )
        )
    return MediaAudit(expect, summary, tuple(findings), policy)


def _validate_constraints(constraints: AuditConstraints) -> None:
    for name, number in (
        ("minimum duration", constraints.minimum_duration),
        ("maximum duration", constraints.maximum_duration),
    ):
        if number is not None and (
            isinstance(number, bool)
            or not isinstance(number, int | float)
            or not math.isfinite(number)
            or number <= 0
        ):
            raise ValueError(f"Audit {name} must be positive and finite")
    if (
        constraints.minimum_duration is not None
        and constraints.maximum_duration is not None
        and constraints.minimum_duration > constraints.maximum_duration
    ):
        raise ValueError("Audit minimum duration cannot exceed maximum duration")
    for name, integer in (
        ("width", constraints.width),
        ("height", constraints.height),
        ("sample rate", constraints.sample_rate),
        ("channels", constraints.channels),
    ):
        if integer is not None and (
            isinstance(integer, bool) or not isinstance(integer, int) or integer <= 0
        ):
            raise ValueError(f"Audit {name} must be a positive integer")
    for name, codec in (
        ("video codec", constraints.video_codec),
        ("audio codec", constraints.audio_codec),
    ):
        if codec is not None and (not isinstance(codec, str) or not codec.strip()):
            raise ValueError(f"Audit {name} cannot be empty")


def _codec_matches(actual: str | None, expected: str) -> bool:
    return actual is not None and actual.casefold() == expected.strip().casefold()


def _expected(name: str, actual: object, expected: str) -> str:
    actual_text = "unavailable" if actual is None else str(actual)
    return f"{name} is {actual_text}; expected {expected}"


__all__ = [
    "AUDIT_CODES",
    "AuditConstraints",
    "AuditExpectation",
    "AuditFinding",
    "AuditSeverity",
    "AuditSummary",
    "AuditThreshold",
    "MediaAudit",
    "audit_media",
]
