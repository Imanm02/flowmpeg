"""Before-and-after media comparison values."""

from __future__ import annotations

import os
from dataclasses import dataclass

from flowmpeg.probe import MediaInfo, probe


@dataclass(frozen=True, slots=True)
class MediaSummary:
    """Selected values for one probed media input."""

    source: str
    size: int | None
    duration: float | None
    bit_rate: int | None
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None
    frame_rate: float | None
    video_streams: int
    audio_streams: int
    subtitle_streams: int


@dataclass(frozen=True, slots=True)
class MediaComparison:
    """Measured changes between two probed media inputs."""

    before: MediaSummary
    after: MediaSummary
    size_delta: int | None
    size_change_percent: float | None
    duration_delta: float | None


def compare_media(
    before: str | os.PathLike[str],
    after: str | os.PathLike[str],
    *,
    ffprobe: str = "ffprobe",
    timeout: float | None = None,
) -> MediaComparison:
    """Probe two media inputs and return measured changes."""

    before_text = os.fspath(before)
    after_text = os.fspath(after)
    before_info = probe(before_text, ffprobe=ffprobe, timeout=timeout)
    after_info = probe(after_text, ffprobe=ffprobe, timeout=timeout)
    return compare_media_info(before_text, before_info, after_text, after_info)


def compare_media_info(
    before_source: str,
    before_info: MediaInfo,
    after_source: str,
    after_info: MediaInfo,
) -> MediaComparison:
    """Compare two already-probed media values."""

    before = _summary(before_source, before_info)
    after = _summary(after_source, after_info)
    size_delta = (
        None if after.size is None or before.size is None else after.size - before.size
    )
    duration_delta = (
        None
        if after.duration is None or before.duration is None
        else after.duration - before.duration
    )
    size_change_percent = None
    if before.size is not None and before.size > 0 and after.size is not None:
        size_change_percent = (after.size - before.size) / before.size * 100
    return MediaComparison(
        before,
        after,
        size_delta,
        size_change_percent,
        duration_delta,
    )


def _summary(source: str, info: MediaInfo) -> MediaSummary:
    video = info.video_streams[0] if info.video_streams else None
    audio = info.audio_streams[0] if info.audio_streams else None
    frame_rate = None
    if video is not None and video.average_frame_rate is not None:
        frame_rate = float(video.average_frame_rate)
    return MediaSummary(
        source=source,
        size=None if info.format is None else info.format.size,
        duration=info.duration,
        bit_rate=None if info.format is None else info.format.bit_rate,
        video_codec=None if video is None else video.codec_name,
        audio_codec=None if audio is None else audio.codec_name,
        width=None if video is None else video.width,
        height=None if video is None else video.height,
        frame_rate=frame_rate,
        video_streams=len(info.video_streams),
        audio_streams=len(info.audio_streams),
        subtitle_streams=len(info.subtitle_streams),
    )


__all__ = ["MediaComparison", "MediaSummary", "compare_media", "compare_media_info"]
