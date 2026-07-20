"""Typed FFprobe inspection."""

from __future__ import annotations

import json
import math
import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import BinaryNotFoundError, BinaryUnusableError, ProbeError


@dataclass(frozen=True, slots=True)
class Rational:
    """An exact ratio reported by FFprobe."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.denominator == 0:
            raise ValueError("Rational denominators cannot be zero")

    def __float__(self) -> float:
        return self.numerator / self.denominator


@dataclass(frozen=True, slots=True)
class FormatInfo:
    """Container-level media information."""

    filename: str | None
    format_name: str | None
    format_long_name: str | None
    duration: float | None
    size: int | None
    bit_rate: int | None
    tags: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class StreamInfo:
    """Fields shared by every probed stream."""

    index: int
    codec_type: str
    codec_name: str | None
    codec_long_name: str | None
    duration: float | None
    time_base: Rational | None
    tags: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class VideoStreamInfo(StreamInfo):
    """Video-specific stream information."""

    width: int | None = None
    height: int | None = None
    pixel_format: str | None = None
    average_frame_rate: Rational | None = None
    sample_aspect_ratio: Rational | None = None


@dataclass(frozen=True, slots=True)
class AudioStreamInfo(StreamInfo):
    """Audio-specific stream information."""

    sample_rate: int | None = None
    channels: int | None = None
    channel_layout: str | None = None
    sample_format: str | None = None


@dataclass(frozen=True, slots=True)
class SubtitleStreamInfo(StreamInfo):
    """Subtitle-specific stream information."""


@dataclass(frozen=True, slots=True)
class MediaInfo:
    """Typed container and stream information from FFprobe."""

    format: FormatInfo | None
    streams: tuple[StreamInfo, ...]

    @property
    def video_streams(self) -> tuple[VideoStreamInfo, ...]:
        """Return only video streams."""

        return tuple(
            stream for stream in self.streams if isinstance(stream, VideoStreamInfo)
        )

    @property
    def audio_streams(self) -> tuple[AudioStreamInfo, ...]:
        """Return only audio streams."""

        return tuple(
            stream for stream in self.streams if isinstance(stream, AudioStreamInfo)
        )

    @property
    def subtitle_streams(self) -> tuple[SubtitleStreamInfo, ...]:
        """Return only subtitle streams."""

        return tuple(
            stream for stream in self.streams if isinstance(stream, SubtitleStreamInfo)
        )

    @property
    def duration(self) -> float | None:
        """Return the container duration when FFprobe reported one."""

        return None if self.format is None else self.format.duration


def probe(
    source: str | os.PathLike[str],
    *,
    ffprobe: str = "ffprobe",
    timeout: float | None = None,
) -> MediaInfo:
    """Inspect a media source with FFprobe and return typed information."""

    return parse_probe_data(probe_raw(source, ffprobe=ffprobe, timeout=timeout))


def probe_raw(
    source: str | os.PathLike[str],
    *,
    ffprobe: str = "ffprobe",
    timeout: float | None = None,
) -> dict[str, object]:
    """Inspect a media source and return the decoded FFprobe JSON object."""

    source_text = os.fspath(source)
    if not source_text:
        raise ProbeError("Probe sources cannot be empty")
    if source_text.startswith("-"):
        raise ProbeError("Probe sources cannot start with a dash")
    if not ffprobe:
        raise BinaryNotFoundError(
            "The FFprobe executable cannot be empty", tool="ffprobe"
        )
    if timeout is not None and not _positive_finite_number(timeout):
        raise ValueError("Probe timeout must be positive and finite")

    argv = (
        ffprobe,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        source_text,
    )
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise BinaryNotFoundError(
            f"FFprobe was not found: {ffprobe}", tool="ffprobe"
        ) from error
    except OSError as error:
        raise BinaryUnusableError(
            f"FFprobe could not be started: {ffprobe}", tool="ffprobe"
        ) from error
    except subprocess.TimeoutExpired as error:
        raise ProbeError(f"FFprobe timed out: {display_argv(argv)}") from error

    if completed.returncode != 0:
        stderr = redact_text(completed.stderr)[-8_000:].strip()
        message = f"FFprobe exited with code {completed.returncode}"
        raise ProbeError(
            message,
            returncode=completed.returncode,
            stderr=stderr,
            command=display_argv(argv),
        )

    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ProbeError("FFprobe returned invalid JSON") from error
    if not isinstance(value, dict):
        raise ProbeError("FFprobe returned a non-object JSON value")
    return cast(dict[str, object], value)


def parse_probe_data(data: Mapping[str, object]) -> MediaInfo:
    """Parse a decoded FFprobe JSON object into typed values."""

    format_data = _mapping(data.get("format"))
    format_info = _parse_format(format_data) if format_data is not None else None
    streams_value = data.get("streams", ())
    if not isinstance(streams_value, list | tuple):
        raise ProbeError("FFprobe streams must be a list")

    streams: list[StreamInfo] = []
    for item in streams_value:
        stream_data = _mapping(item)
        if stream_data is None:
            raise ProbeError("FFprobe stream entries must be objects")
        streams.append(_parse_stream(stream_data))
    return MediaInfo(format_info, tuple(streams))


def _parse_format(data: Mapping[str, object]) -> FormatInfo:
    return FormatInfo(
        filename=_string(data.get("filename")),
        format_name=_string(data.get("format_name")),
        format_long_name=_string(data.get("format_long_name")),
        duration=_float(data.get("duration")),
        size=_integer(data.get("size")),
        bit_rate=_integer(data.get("bit_rate")),
        tags=_tags(data.get("tags")),
    )


def _parse_stream(data: Mapping[str, object]) -> StreamInfo:
    index = _integer(data.get("index"))
    if index is None:
        raise ProbeError("FFprobe streams require an index")
    codec_type = _string(data.get("codec_type")) or "unknown"
    codec_name = _string(data.get("codec_name"))
    codec_long_name = _string(data.get("codec_long_name"))
    duration = _float(data.get("duration"))
    time_base = _rational(data.get("time_base"))
    tags = _tags(data.get("tags"))

    if codec_type == "video":
        return VideoStreamInfo(
            index,
            codec_type,
            codec_name,
            codec_long_name,
            duration,
            time_base,
            tags,
            width=_integer(data.get("width")),
            height=_integer(data.get("height")),
            pixel_format=_string(data.get("pix_fmt")),
            average_frame_rate=_rational(data.get("avg_frame_rate")),
            sample_aspect_ratio=_rational(
                data.get("sample_aspect_ratio"),
                separator=":",
            ),
        )
    if codec_type == "audio":
        return AudioStreamInfo(
            index,
            codec_type,
            codec_name,
            codec_long_name,
            duration,
            time_base,
            tags,
            sample_rate=_integer(data.get("sample_rate")),
            channels=_integer(data.get("channels")),
            channel_layout=_string(data.get("channel_layout")),
            sample_format=_string(data.get("sample_fmt")),
        )
    if codec_type == "subtitle":
        return SubtitleStreamInfo(
            index,
            codec_type,
            codec_name,
            codec_long_name,
            duration,
            time_base,
            tags,
        )
    return StreamInfo(
        index,
        codec_type,
        codec_name,
        codec_long_name,
        duration,
        time_base,
        tags,
    )


def _mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    if not all(isinstance(key, str) for key in value):
        return None
    return cast(Mapping[str, object], value)


def _positive_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    try:
        return math.isfinite(value) and value > 0
    except OverflowError:
        return False


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value != "N/A" else None


def _integer(value: object) -> int | None:
    if value is None or value == "N/A" or isinstance(value, bool):
        return None
    try:
        return int(cast(str | int | float, value))
    except (TypeError, ValueError):
        return None


def _float(value: object) -> float | None:
    if value is None or value == "N/A" or isinstance(value, bool):
        return None
    try:
        return float(cast(str | int | float, value))
    except (TypeError, ValueError):
        return None


def _rational(value: object, *, separator: str = "/") -> Rational | None:
    if not isinstance(value, str) or separator not in value:
        return None
    numerator_text, denominator_text = value.split(separator, 1)
    try:
        numerator = int(numerator_text)
        denominator = int(denominator_text)
    except ValueError:
        return None
    if denominator == 0:
        return None
    return Rational(numerator, denominator)


def _tags(value: object) -> tuple[tuple[str, str], ...]:
    mapping = _mapping(value)
    if mapping is None:
        return ()
    return tuple(
        sorted(
            (key, str(item))
            for key, item in mapping.items()
            if isinstance(item, str | int | float | bool)
        )
    )
