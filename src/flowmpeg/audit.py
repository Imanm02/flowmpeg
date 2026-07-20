"""Opinionated checks over typed FFprobe results."""

from __future__ import annotations

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
    "AUD211",
    "AUD212",
    "AUD213",
    "AUD214",
    "AUD221",
    "AUD222",
    "AUD223",
)


@dataclass(frozen=True, slots=True)
class AuditFinding:
    """One stable media audit result."""

    code: str
    severity: AuditSeverity
    message: str


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
    sample_rate: int | None
    channels: int | None


@dataclass(frozen=True, slots=True)
class MediaAudit:
    """Summary and findings for one probed input."""

    expectation: AuditExpectation
    summary: AuditSummary
    findings: tuple[AuditFinding, ...]

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
) -> MediaAudit:
    """Check a typed probe result against a requested stream shape."""

    if expect not in {"any", "video", "audio", "av"}:
        raise ValueError(f"Unknown audit expectation: {expect}")
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
        sample_rate=None if first_audio is None else first_audio.sample_rate,
        channels=None if first_audio is None else first_audio.channels,
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
    return MediaAudit(expect, summary, tuple(findings))


__all__ = [
    "AUDIT_CODES",
    "AuditExpectation",
    "AuditFinding",
    "AuditSeverity",
    "AuditSummary",
    "AuditThreshold",
    "MediaAudit",
    "audit_media",
]
