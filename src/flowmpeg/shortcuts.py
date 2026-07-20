"""Path-to-path shortcuts that build inspectable media plans."""

from __future__ import annotations

import math
import os
import re
from collections.abc import Sequence
from typing import Literal, TypeAlias

from flowmpeg.clip import Clip, concat_clips, media
from flowmpeg.errors import GraphError
from flowmpeg.model import Expression, StreamKind, expr
from flowmpeg.plan import Plan, output
from flowmpeg.recipes.audio import (
    MixDuration,
    change_audio_speed,
    mix_audio,
    volume,
)
from flowmpeg.recipes.audio import (
    normalize_loudness as normalize_audio_stream,
)
from flowmpeg.recipes.video import (
    Rotation,
    change_video_speed,
    crop_video,
    named_overlay_position,
    overlay_video,
    rotate_video,
    scale,
    stack_video,
    trim_video,
)
from flowmpeg.streams import AudioStream, VideoStream, apply_filter, input

Pathish: TypeAlias = str | os.PathLike[str]
VideoPreset = Literal["web"]
AudioCodec = Literal["mp3", "aac", "wav", "flac", "copy"]
AudioReplacementCodec = Literal["aac", "copy"]
ReplacementDuration = Literal["video", "shortest"]
NamedPosition = Literal[
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
    "center",
]

_protocol = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")
_audio_suffixes: dict[AudioCodec, frozenset[str]] = {
    "mp3": frozenset({".mp3"}),
    "aac": frozenset({".aac", ".m4a"}),
    "wav": frozenset({".wav"}),
    "flac": frozenset({".flac"}),
    "copy": frozenset(),
}

__all__ = [
    "AudioCodec",
    "AudioReplacementCodec",
    "NamedPosition",
    "Pathish",
    "ReplacementDuration",
    "VideoPreset",
    "add_music",
    "change_speed",
    "crop",
    "extract_audio",
    "grid",
    "join_matching",
    "make_gif",
    "mix_audio_files",
    "normalize_loudness",
    "remove_audio",
    "replace_audio",
    "resize",
    "rotate",
    "thumbnail",
    "transcode",
    "trim",
    "watermark",
]


def transcode(
    source: Pathish,
    to: Pathish,
    *,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a web video transcode plan."""

    clip = media(source, audio=include_audio)
    return _web_plan(clip, to, (source,), preset, overwrite)


def trim(
    source: Pathish,
    to: Pathish,
    *,
    start: float | None = None,
    end: float | None = None,
    duration: float | None = None,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build an accurate paired video and audio trim plan."""

    if duration is not None:
        if end is not None:
            raise GraphError("Set end or duration, not both")
        _positive_number("duration", duration)
        start = 0 if start is None else start
        end = start + duration
    clip = media(source, audio=include_audio).trim(start=start, end=end)
    return _web_plan(clip, to, (source,), preset, overwrite)


def resize(
    source: Pathish,
    to: Pathish,
    *,
    width: int | None = None,
    height: int | None = None,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build an aspect-preserving resize plan."""

    if (width is None) == (height is None):
        raise GraphError("Set exactly one of width or height")
    if width is not None:
        _positive_integer("width", width)
    if height is not None:
        _positive_integer("height", height)
    clip = media(source, audio=include_audio).scale(width=width, height=height)
    return _web_plan(clip, to, (source,), preset, overwrite)


def remove_audio(
    source: Pathish,
    to: Pathish,
    *,
    overwrite: bool = False,
) -> Plan:
    """Build a plan that copies video and drops every other stream."""

    _validate_paths((source,), to)
    plan = output(input(source).video(), to=to, args=("-c:v", "copy"))
    return _set_overwrite(plan, overwrite)


def extract_audio(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    codec: AudioCodec = "mp3",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Build a plan that maps one audio track to a new file."""

    _nonnegative_integer("track", track)
    _validate_paths((source,), to)
    args = _audio_args(to, codec, bitrate)
    plan = output(input(source).audio(track), to=to, args=args)
    return _set_overwrite(plan, overwrite)


def replace_audio(
    video_source: Pathish,
    audio_source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    duration: ReplacementDuration = "video",
    audio_codec: AudioReplacementCodec = "aac",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Build a plan that replaces a video's original audio track."""

    _nonnegative_integer("track", track)
    _validate_paths((video_source, audio_source), to)
    _require_suffix(to, frozenset({".mp4"}), "Replacement output")
    if duration not in {"video", "shortest"}:
        raise GraphError("Replacement duration must be 'video' or 'shortest'")
    if duration == "video" and audio_codec == "copy":
        raise GraphError("Video-length audio padding requires AAC encoding")

    video = input(video_source).video()
    audio = input(audio_source).audio(track)
    if duration == "video":
        audio = audio.filter("apad")

    args: tuple[str, ...]
    if audio_codec == "aac":
        bitrate_value = "192k" if bitrate is None else bitrate
        _validate_bitrate(bitrate_value)
        args = (
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            bitrate_value,
            "-shortest",
        )
    elif audio_codec == "copy":
        if bitrate is not None:
            raise GraphError("Copied replacement audio does not accept bitrate")
        args = ("-c:v", "copy", "-c:a", "copy", "-shortest")
    else:
        raise GraphError(f"Unknown replacement audio codec: {audio_codec}")
    return _set_overwrite(output(video, audio, to=to, args=args), overwrite)


def watermark(
    source: Pathish,
    image: Pathish,
    to: Pathish,
    *,
    position: NamedPosition = "top-right",
    padding: int = 24,
    width: int | None = None,
    opacity: float = 1,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a plan that places a still image over a video."""

    base = media(source, audio=include_audio)
    base_video = _require_video(base)
    mark = input(image).video()
    if width is not None:
        _positive_integer("width", width)
        mark = scale(mark, width=width)
    x, y = named_overlay_position(position, padding=padding)
    video = overlay_video(base_video, mark, x=x, y=y, opacity=opacity)
    return _web_plan(Clip(video, base.audio), to, (source, image), preset, overwrite)


def add_music(
    source: Pathish,
    music: Pathish,
    to: Pathish,
    *,
    music_volume: float = 0.15,
    source_volume: float = 1,
    source_has_audio: bool = True,
    loop_music: bool = False,
    normalize: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a plan that mixes background music under source audio."""

    _nonnegative_number("music_volume", music_volume)
    _nonnegative_number("source_volume", source_volume)
    if not isinstance(source_has_audio, bool):
        raise GraphError("source_has_audio must be a Boolean")
    base = media(source, audio=source_has_audio)
    music_args = ("-stream_loop", "-1") if loop_music else ()
    music_audio = input(music, *music_args).audio()
    music_audio = _volume_if_needed(music_audio, music_volume)
    output_args: tuple[str, ...] = ()
    if source_has_audio:
        source_audio = _volume_if_needed(_require_audio(base), source_volume)
        result_audio = mix_audio(
            source_audio,
            music_audio,
            duration="first",
            normalize=normalize,
        )
    else:
        if source_volume != 1:
            raise GraphError("source_volume requires source audio")
        result_audio = music_audio.filter("apad")
        output_args = ("-shortest",)
    return _web_plan(
        Clip(base.video, result_audio),
        to,
        (source, music),
        preset,
        overwrite,
        output_args,
    )


def join_matching(
    sources: Sequence[Pathish],
    to: Pathish,
    *,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a concat plan for files with matching decoded formats."""

    source_values = _source_sequence(sources)
    if len(source_values) < 2:
        raise GraphError("Joining requires at least two sources")
    clips = tuple(media(source, audio=include_audio) for source in source_values)
    joined = concat_clips(*clips)
    return _web_plan(joined, to, source_values, preset, overwrite)


def mix_audio_files(
    sources: Sequence[Pathish],
    to: Pathish,
    *,
    volumes: Sequence[float] | None = None,
    duration: MixDuration = "longest",
    normalize: bool = True,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Build a plan that mixes the first track from several audio files."""

    source_values = _source_sequence(sources)
    if len(source_values) < 2:
        raise GraphError("Mixing files requires at least two sources")
    if codec == "copy":
        raise GraphError("Mixed audio must be encoded")
    if volumes is not None and len(volumes) != len(source_values):
        raise GraphError("Volumes must match the source count")

    streams: list[AudioStream] = []
    for index, source in enumerate(source_values):
        stream = input(source).audio()
        if volumes is not None:
            _nonnegative_number("volume", volumes[index])
            stream = _volume_if_needed(stream, volumes[index])
        streams.append(stream)
    mixed = mix_audio(*streams, duration=duration, normalize=normalize)
    _validate_paths(source_values, to)
    plan = output(mixed, to=to, args=_audio_args(to, codec, bitrate))
    return _set_overwrite(plan, overwrite)


def grid(
    sources: Sequence[Pathish],
    to: Pathish,
    *,
    columns: int = 2,
    cell_width: int = 640,
    cell_height: int = 360,
    fill: str = "black",
    shortest: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a fixed-cell video grid without audio."""

    source_values = _source_sequence(sources)
    if len(source_values) < 2:
        raise GraphError("Video grids require at least two sources")
    _positive_integer("columns", columns)
    _positive_integer("cell_width", cell_width)
    _positive_integer("cell_height", cell_height)
    videos = tuple(
        scale(input(source).video(), width=cell_width, height=cell_height)
        for source in source_values
    )
    video = stack_video(
        *videos,
        columns=columns,
        fill=fill,
        shortest=shortest,
    )
    return _web_plan(Clip(video, None), to, source_values, preset, overwrite)


def thumbnail(
    source: Pathish,
    to: Pathish,
    *,
    at: float = 0,
    width: int | None = None,
    quality: int = 2,
    overwrite: bool = False,
) -> Plan:
    """Build a plan that writes one image from a video timestamp."""

    _nonnegative_number("at", at)
    suffix = _require_suffix(
        to,
        frozenset({".jpg", ".jpeg", ".png", ".webp"}),
        "Thumbnail output",
    )
    source_input = input(source, "-ss", f"{at:g}")
    video = source_input.video()
    if width is not None:
        _positive_integer("width", width)
        video = scale(video, width=width)

    args: tuple[str, ...] = ("-frames:v", "1")
    if suffix in {".jpg", ".jpeg"}:
        if isinstance(quality, bool) or not 1 <= quality <= 31:
            raise GraphError("JPEG quality must be between 1 and 31")
        args += ("-q:v", str(quality))
    _validate_paths((source,), to)
    return _set_overwrite(output(video, to=to, args=args), overwrite)


def make_gif(
    source: Pathish,
    to: Pathish,
    *,
    start: float = 0,
    duration: float | None = 5,
    width: int | None = 480,
    fps: int = 12,
    loop: int = 0,
    overwrite: bool = False,
) -> Plan:
    """Build a palette-based animated GIF plan."""

    _nonnegative_number("start", start)
    if duration is not None:
        _positive_number("duration", duration)
    if isinstance(fps, bool) or not 1 <= fps <= 100:
        raise GraphError("GIF frame rate must be between 1 and 100")
    if isinstance(loop, bool) or not isinstance(loop, int) or loop < -1:
        raise GraphError("GIF loop count must be -1 or greater")
    _require_suffix(to, frozenset({".gif"}), "GIF output")
    _validate_paths((source,), to)

    video = input(source).video()
    if start > 0 or duration is not None:
        end = None if duration is None else start + duration
        video = trim_video(video, start=start, end=end)
    else:
        video = video.filter("setpts", expr("PTS-STARTPTS"))
    video = video.filter("fps", fps=fps)
    if width is not None:
        _positive_integer("width", width)
        video = video.filter("scale", width, -2, flags="lanczos")

    palette_input, gif_input = video.split()
    palette = palette_input.filter("palettegen", stats_mode="diff")
    (gif_video,) = apply_filter(
        (gif_input, palette),
        "paletteuse",
        output_kinds=(StreamKind.VIDEO,),
        options={"dither": "sierra2_4a"},
    )
    plan = output(gif_video, to=to, args=("-loop", str(loop)))
    return _set_overwrite(plan, overwrite)


def rotate(
    source: Pathish,
    to: Pathish,
    *,
    degrees: Rotation = 90,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a plan that rotates displayed video by a quarter turn."""

    clip = media(source, audio=include_audio)
    video = rotate_video(_require_video(clip), degrees)
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def crop(
    source: Pathish,
    to: Pathish,
    *,
    width: int,
    height: int,
    x: int | Expression | None = None,
    y: int | Expression | None = None,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a fixed-size video crop plan."""

    clip = media(source, audio=include_audio)
    video = crop_video(
        _require_video(clip),
        width=width,
        height=height,
        x=x,
        y=y,
    )
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def change_speed(
    source: Pathish,
    to: Pathish,
    *,
    factor: float,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Build a plan that changes paired video and audio speed."""

    _positive_number("factor", factor)
    clip = media(source, audio=include_audio)
    video = change_video_speed(_require_video(clip), factor)
    audio = change_audio_speed(clip.audio, factor) if clip.audio is not None else None
    return _web_plan(Clip(video, audio), to, (source,), preset, overwrite)


def normalize_loudness(
    source: Pathish,
    to: Pathish,
    *,
    integrated: float = -16,
    loudness_range: float = 11,
    true_peak: float = -1.5,
    sample_rate: int = 48_000,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Build a one-pass EBU R128 audio normalization plan."""

    if codec == "copy":
        raise GraphError("Normalized audio must be encoded")
    _validate_paths((source,), to)
    audio = normalize_audio_stream(
        input(source).audio(),
        integrated=integrated,
        loudness_range=loudness_range,
        true_peak=true_peak,
        sample_rate=sample_rate,
    )
    plan = output(audio, to=to, args=_audio_args(to, codec, bitrate))
    return _set_overwrite(plan, overwrite)


def _web_plan(
    clip: Clip,
    to: Pathish,
    sources: Sequence[Pathish],
    preset: VideoPreset,
    overwrite: bool,
    output_args: tuple[str, ...] = (),
) -> Plan:
    if preset != "web":
        raise GraphError(f"Unknown video preset: {preset}")
    _require_suffix(to, frozenset({".mp4"}), "Web video output")
    _validate_paths(sources, to)
    return clip.output(
        to,
        preset=preset,
        args=output_args,
        overwrite=_require_boolean("overwrite", overwrite),
    )


def _audio_args(
    to: Pathish,
    codec: AudioCodec,
    bitrate: str | None,
) -> tuple[str, ...]:
    if codec not in _audio_suffixes:
        raise GraphError(f"Unknown audio codec: {codec}")
    allowed_suffixes = _audio_suffixes[codec]
    if allowed_suffixes:
        _require_suffix(to, allowed_suffixes, f"{codec.upper()} output")

    if codec == "mp3":
        value = "192k" if bitrate is None else bitrate
        _validate_bitrate(value)
        return ("-c:a", "libmp3lame", "-b:a", value)
    if codec == "aac":
        value = "192k" if bitrate is None else bitrate
        _validate_bitrate(value)
        return ("-c:a", "aac", "-b:a", value)
    if codec == "wav":
        _reject_bitrate(codec, bitrate)
        return ("-c:a", "pcm_s16le")
    if codec == "flac":
        _reject_bitrate(codec, bitrate)
        return ("-c:a", "flac")
    _reject_bitrate(codec, bitrate)
    return ("-c:a", "copy")


def _reject_bitrate(codec: AudioCodec, bitrate: str | None) -> None:
    if bitrate is not None:
        raise GraphError(f"{codec.upper()} output does not accept bitrate")


def _validate_bitrate(value: str) -> None:
    if not value or value.startswith("-"):
        raise GraphError("Audio bitrate cannot be empty or start with a dash")


def _require_suffix(
    path: Pathish,
    allowed: frozenset[str],
    label: str,
) -> str:
    suffix = os.path.splitext(os.fspath(path))[1].lower()
    if suffix not in allowed:
        choices = ", ".join(sorted(allowed))
        raise GraphError(f"{label} must use one of: {choices}")
    return suffix


def _validate_paths(sources: Sequence[Pathish], to: Pathish) -> None:
    destination = _path_text("Output", to)
    destination_id = _local_path_id(destination)
    for source in sources:
        source_text = _path_text("Input", source)
        if destination_id is not None and _local_path_id(source_text) == destination_id:
            raise GraphError("Output path must differ from every input path")


def _source_sequence(sources: Sequence[Pathish]) -> tuple[Pathish, ...]:
    if isinstance(sources, (str, os.PathLike)):
        raise GraphError("Sources must be a sequence of paths, not one path")
    return tuple(sources)


def _path_text(label: str, value: Pathish) -> str:
    text = os.fspath(value)
    if not text:
        raise GraphError(f"{label} path cannot be empty")
    if text.startswith("-"):
        raise GraphError(f"{label} path cannot start with a dash")
    return text


def _local_path_id(value: str) -> str | None:
    if value == "-" or value.upper() == "NUL" or value == "/dev/null":
        return None
    drive, _ = os.path.splitdrive(value)
    if not drive and _protocol.match(value):
        return None
    return os.path.normcase(os.path.abspath(value))


def _set_overwrite(plan: Plan, overwrite: bool) -> Plan:
    return plan.overwrite() if _require_boolean("overwrite", overwrite) else plan


def _require_boolean(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise GraphError(f"{name} must be a Boolean")
    return value


def _require_video(clip: Clip) -> VideoStream:
    if clip.video is None:
        raise GraphError("Shortcut requires a video stream")
    return clip.video


def _require_audio(clip: Clip) -> AudioStream:
    if clip.audio is None:
        raise GraphError("Shortcut requires an audio stream")
    return clip.audio


def _volume_if_needed(stream: AudioStream, factor: float) -> AudioStream:
    return stream if factor == 1 else volume(stream, factor=factor)


def _positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GraphError(f"{name} must be a positive integer")


def _nonnegative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphError(f"{name} must be a nonnegative integer")


def _positive_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise GraphError(f"{name} must be a positive finite number")


def _nonnegative_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise GraphError(f"{name} must be a nonnegative finite number")
