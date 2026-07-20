"""Path-to-path shortcuts that build inspectable media plans."""

from __future__ import annotations

import math
import os
import re
from collections.abc import Sequence
from typing import Literal, TypeAlias

from flowmpeg.clip import Clip, concat_clips, media
from flowmpeg.errors import GraphError
from flowmpeg.model import Expression, FilterValue, StreamKind, expr
from flowmpeg.pathing import same_destination
from flowmpeg.plan import Plan, output
from flowmpeg.recipes.audio import (
    MixDuration,
    change_audio_speed,
    fade_audio,
    mix_audio,
    volume,
)
from flowmpeg.recipes.audio import (
    delay_audio as delay_audio_stream,
)
from flowmpeg.recipes.audio import (
    normalize_loudness as normalize_audio_stream,
)
from flowmpeg.recipes.audio import (
    trim_audio as trim_audio_stream,
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
from flowmpeg.streams import AudioStream, Stream, VideoStream, apply_filter, input

Pathish: TypeAlias = str | os.PathLike[str]
VideoPreset = Literal["web"]
EncoderPreset = Literal[
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
]
FlipDirection = Literal["horizontal", "vertical", "both"]
DeinterlaceMode = Literal["bwdif", "yadif"]
SocialTarget = Literal["vertical", "portrait", "square", "landscape"]
SocialFill = Literal["blur", "crop", "fit"]
CrossfadeCurve = Literal["tri", "qsin", "exp"]
AudioCodec = Literal["mp3", "aac", "opus", "wav", "flac", "copy"]
AudioLayout = Literal["mono", "stereo"]
AudioReplacementCodec = Literal["aac", "copy"]
ReplacementDuration = Literal["video", "shortest"]
NamedPosition = Literal[
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
    "center",
]
WaveformScale = Literal["lin", "log", "sqrt", "cbrt"]
SpectrumMode = Literal["combined", "separate"]
SpectrumColor = Literal[
    "channel",
    "intensity",
    "rainbow",
    "moreland",
    "nebulae",
    "fire",
    "fiery",
    "fruit",
    "cool",
    "magma",
    "green",
    "viridis",
    "plasma",
    "cividis",
    "terrain",
]

_audio_suffixes: dict[AudioCodec, frozenset[str]] = {
    "mp3": frozenset({".mp3"}),
    "aac": frozenset({".aac", ".m4a"}),
    "opus": frozenset({".opus"}),
    "wav": frozenset({".wav"}),
    "flac": frozenset({".flac"}),
    "copy": frozenset(),
}

__all__ = [
    "AudioCodec",
    "AudioLayout",
    "AudioReplacementCodec",
    "CrossfadeCurve",
    "DeinterlaceMode",
    "EncoderPreset",
    "FlipDirection",
    "NamedPosition",
    "Pathish",
    "ReplacementDuration",
    "SocialFill",
    "SocialTarget",
    "SpectrumColor",
    "SpectrumMode",
    "VideoPreset",
    "WaveformScale",
    "add_music",
    "add_subtitles",
    "adjust_colors",
    "blurred_background",
    "blur_region",
    "boomerang",
    "burn_subtitles",
    "change_speed",
    "compress_audio",
    "compress_video",
    "contact_sheet",
    "crop",
    "duck_music",
    "deinterlace",
    "denoise_audio",
    "delay_audio_file",
    "extract_audio",
    "extract_subtitles",
    "fade_audio_edges",
    "fade_edges",
    "fit_canvas",
    "flip_video",
    "freeze_end",
    "grid",
    "join_audio_files",
    "join_normalized",
    "join_matching",
    "loop_video",
    "image_sequence_video",
    "make_gif",
    "mix_audio_files",
    "mono_audio",
    "mute_section",
    "normalize_loudness",
    "picture_in_picture",
    "podcast_audiogram",
    "podcast_voice",
    "reframe",
    "remove_audio",
    "remove_subtitles",
    "remux_media",
    "resample_audio",
    "replace_audio",
    "resize",
    "reverse_clip",
    "rotate",
    "set_frame_rate",
    "set_audio_volume",
    "sharpen",
    "social_video",
    "spectrum_image",
    "still_image_video",
    "thumbnail",
    "trim_audio_file",
    "trim_silence",
    "transcode",
    "transcode_av1",
    "transcode_hevc",
    "transcode_webm",
    "trim",
    "strip_metadata",
    "tag_audio",
    "tag_media",
    "watermark",
    "waveform_image",
    "crossfade_audio",
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

    clip = _media_with_optional_audio(source, include_audio)
    return _web_plan(clip, to, (source,), preset, overwrite)


def transcode_webm(
    source: Pathish,
    to: Pathish,
    *,
    crf: int = 32,
    cpu_used: int = 2,
    audio_bitrate: str = "128k",
    include_audio: bool = True,
    overwrite: bool = False,
) -> Plan:
    """Encode VP9 video and optional Opus audio in WebM."""

    if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 63:
        raise GraphError("VP9 CRF must be an integer between 0 and 63")
    if (
        isinstance(cpu_used, bool)
        or not isinstance(cpu_used, int)
        or not 0 <= cpu_used <= 8
    ):
        raise GraphError("VP9 CPU use must be an integer between 0 and 8")
    clip = _media_with_optional_audio(source, include_audio)
    if clip.audio is not None:
        _validate_bitrate(audio_bitrate)
    _require_suffix(to, frozenset({".webm"}), "WebM output")
    _validate_paths((source,), to)
    args: tuple[str, ...] = (
        "-c:v",
        "libvpx-vp9",
        "-crf",
        str(crf),
        "-b:v",
        "0",
        "-cpu-used",
        str(cpu_used),
        "-row-mt",
        "1",
        "-pix_fmt",
        "yuv420p",
    )
    if clip.audio is not None:
        args += ("-c:a", "libopus", "-b:a", audio_bitrate)
    plan = output(
        _require_video(clip),
        *(stream for stream in (clip.audio,) if stream is not None),
        to=to,
        args=args,
    )
    return _set_overwrite(plan, overwrite)


def transcode_hevc(
    source: Pathish,
    to: Pathish,
    *,
    crf: int = 28,
    encoder_preset: EncoderPreset = "medium",
    audio_bitrate: str = "160k",
    include_audio: bool = True,
    overwrite: bool = False,
) -> Plan:
    """Encode HEVC video and optional AAC audio in MP4."""

    if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 51:
        raise GraphError("HEVC CRF must be an integer between 0 and 51")
    _validate_encoder_preset(encoder_preset, codec="HEVC")
    clip = _media_with_optional_audio(source, include_audio)
    if clip.audio is not None:
        _validate_bitrate(audio_bitrate)
    _require_suffix(to, frozenset({".mp4"}), "HEVC output")
    _validate_paths((source,), to)
    args: tuple[str, ...] = (
        "-c:v",
        "libx265",
        "-crf",
        str(crf),
        "-preset",
        encoder_preset,
        "-pix_fmt",
        "yuv420p",
        "-tag:v",
        "hvc1",
        "-movflags",
        "+faststart",
    )
    if clip.audio is not None:
        args += ("-c:a", "aac", "-b:a", audio_bitrate)
    plan = output(
        _require_video(clip),
        *(stream for stream in (clip.audio,) if stream is not None),
        to=to,
        args=args,
    )
    return _set_overwrite(plan, overwrite)


def transcode_av1(
    source: Pathish,
    to: Pathish,
    *,
    crf: int = 35,
    speed: int = 8,
    audio_bitrate: str = "128k",
    include_audio: bool = True,
    overwrite: bool = False,
) -> Plan:
    """Encode AV1 video and optional Opus audio in WebM."""

    if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 63:
        raise GraphError("AV1 CRF must be an integer between 0 and 63")
    if isinstance(speed, bool) or not isinstance(speed, int) or not 0 <= speed <= 13:
        raise GraphError("AV1 speed must be an integer between 0 and 13")
    clip = _media_with_optional_audio(source, include_audio)
    if clip.audio is not None:
        _validate_bitrate(audio_bitrate)
    _require_suffix(to, frozenset({".webm"}), "AV1 WebM output")
    _validate_paths((source,), to)
    args: tuple[str, ...] = (
        "-c:v",
        "libsvtav1",
        "-crf",
        str(crf),
        "-preset",
        str(speed),
        "-pix_fmt",
        "yuv420p",
    )
    if clip.audio is not None:
        args += ("-c:a", "libopus", "-b:a", audio_bitrate)
    plan = output(
        _require_video(clip),
        *(stream for stream in (clip.audio,) if stream is not None),
        to=to,
        args=args,
    )
    return _set_overwrite(plan, overwrite)


def compress_video(
    source: Pathish,
    to: Pathish,
    *,
    crf: int = 28,
    encoder_preset: EncoderPreset = "medium",
    max_width: int | None = None,
    include_audio: bool = True,
    audio_bitrate: str = "128k",
    overwrite: bool = False,
) -> Plan:
    """Create a smaller H.264 MP4 with explicit quality controls."""

    if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 51:
        raise GraphError("CRF must be an integer between 0 and 51")
    _validate_encoder_preset(encoder_preset)
    clip = _media_with_optional_audio(source, include_audio)
    if clip.audio is not None:
        _validate_bitrate(audio_bitrate)
    video = _require_video(clip)
    if max_width is not None:
        _even_positive_integer("max_width", max_width)
        even_width = expr(f"trunc(min(iw,{max_width})/2)*2")
    else:
        even_width = expr("trunc(iw/2)*2")
    video = video.filter("scale", w=even_width, h=-2)
    _require_suffix(to, frozenset({".mp4"}), "Compressed video output")
    _validate_paths((source,), to)
    plan = output(
        video,
        *(stream for stream in (clip.audio,) if stream is not None),
        to=to,
        args=_web_args(
            has_audio=clip.audio is not None,
            crf=crf,
            encoder_preset=encoder_preset,
            audio_bitrate=audio_bitrate,
        ),
    )
    return _set_overwrite(plan, overwrite)


def reframe(
    source: Pathish,
    to: Pathish,
    *,
    width: int = 1080,
    height: int = 1920,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Fill a fixed frame by scaling and taking a centered crop."""

    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    clip = _media_with_optional_audio(source, include_audio)
    video = _require_video(clip).filter(
        "scale",
        w=width,
        h=height,
        force_original_aspect_ratio="increase",
    )
    video = crop_video(video, width=width, height=height).filter("setsar", 1)
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def social_video(
    source: Pathish,
    to: Pathish,
    *,
    target: SocialTarget = "vertical",
    fill: SocialFill = "blur",
    color: str = "black",
    blur: float = 20,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Prepare a video for one of four common social frame sizes."""

    sizes = {
        "vertical": (1080, 1920),
        "portrait": (1080, 1350),
        "square": (1080, 1080),
        "landscape": (1920, 1080),
    }
    try:
        width, height = sizes[target]
    except KeyError as error:
        raise GraphError(f"Unknown social target: {target}") from error
    if fill == "blur":
        return blurred_background(
            source,
            to,
            width=width,
            height=height,
            blur=blur,
            include_audio=include_audio,
            preset=preset,
            overwrite=overwrite,
        )
    if fill == "crop":
        return reframe(
            source,
            to,
            width=width,
            height=height,
            include_audio=include_audio,
            preset=preset,
            overwrite=overwrite,
        )
    if fill == "fit":
        return fit_canvas(
            source,
            to,
            width=width,
            height=height,
            color=color,
            include_audio=include_audio,
            preset=preset,
            overwrite=overwrite,
        )
    raise GraphError(f"Unknown social fill: {fill}")


def set_frame_rate(
    source: Pathish,
    to: Pathish,
    *,
    fps: int = 30,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Convert video to a constant output frame rate."""

    if isinstance(fps, bool) or not isinstance(fps, int) or not 1 <= fps <= 120:
        raise GraphError("Frame rate must be an integer between 1 and 120")
    clip = _media_with_optional_audio(source, include_audio)
    video = _require_video(clip).filter("fps", fps=fps)
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def deinterlace(
    source: Pathish,
    to: Pathish,
    *,
    mode: DeinterlaceMode = "bwdif",
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Deinterlace video with bwdif or yadif."""

    if mode not in {"bwdif", "yadif"}:
        raise GraphError(f"Unknown deinterlace mode: {mode}")
    clip = _media_with_optional_audio(source, include_audio)
    video = _require_video(clip).filter(mode, mode="send_frame", parity="auto")
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def flip_video(
    source: Pathish,
    to: Pathish,
    *,
    direction: FlipDirection = "horizontal",
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Mirror video on one axis or both axes."""

    clip = _media_with_optional_audio(source, include_audio)
    video = _require_video(clip)
    if direction in {"horizontal", "both"}:
        video = video.filter("hflip")
    if direction in {"vertical", "both"}:
        video = video.filter("vflip")
    if direction not in {"horizontal", "vertical", "both"}:
        raise GraphError(f"Unknown flip direction: {direction}")
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def adjust_colors(
    source: Pathish,
    to: Pathish,
    *,
    brightness: float = 0,
    contrast: float = 1,
    saturation: float = 1,
    gamma: float = 1,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Adjust brightness, contrast, saturation, and gamma together."""

    _bounded_number("brightness", brightness, -1, 1)
    _bounded_number("contrast", contrast, 0, 2)
    _bounded_number("saturation", saturation, 0, 3)
    _bounded_number("gamma", gamma, 0.1, 10)
    clip = _media_with_optional_audio(source, include_audio)
    video = _require_video(clip).filter(
        "eq",
        brightness=brightness,
        contrast=contrast,
        saturation=saturation,
        gamma=gamma,
    )
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def sharpen(
    source: Pathish,
    to: Pathish,
    *,
    amount: float = 1,
    matrix_size: int = 5,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Apply a bounded luma sharpening filter."""

    _bounded_number("amount", amount, 0, 5)
    if (
        isinstance(matrix_size, bool)
        or not isinstance(matrix_size, int)
        or not 3 <= matrix_size <= 23
        or matrix_size % 2 == 0
    ):
        raise GraphError("Sharpen matrix size must be odd and between 3 and 23")
    clip = _media_with_optional_audio(source, include_audio)
    video = _require_video(clip).filter(
        "unsharp",
        luma_msize_x=matrix_size,
        luma_msize_y=matrix_size,
        luma_amount=amount,
    )
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def freeze_end(
    source: Pathish,
    to: Pathish,
    *,
    seconds: float = 2,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Hold the final video frame and pad audio with silence."""

    _bounded_number("seconds", seconds, 0.01, 60)
    clip = media(source, audio=include_audio)
    video = _require_video(clip).filter(
        "tpad",
        stop_mode="clone",
        stop_duration=seconds,
    )
    audio = clip.audio
    if audio is not None:
        audio = audio.filter("apad", pad_dur=seconds)
    plan = _web_plan(Clip(video, audio), to, (source,), preset, overwrite)
    if not include_audio:
        return plan
    fallback = freeze_end(
        source,
        to,
        seconds=seconds,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, source)


def mute_section(
    source: Pathish,
    to: Pathish,
    *,
    start: float,
    end: float,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Mute one time range while leaving the rest of the audio intact."""

    _nonnegative_number("start", start)
    _positive_number("end", end)
    if end <= start:
        raise GraphError("Muted section end must be greater than start")
    clip = media(source)
    audio = _require_audio(clip).filter(
        "volume",
        volume=0,
        enable=expr(f"between(t,{start:g},{end:g})"),
    )
    return _web_plan(Clip(clip.video, audio), to, (source,), preset, overwrite)


def blur_region(
    source: Pathish,
    to: Pathish,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    radius: int = 12,
    power: int = 2,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Blur one fixed rectangle, such as a face or plate."""

    _nonnegative_integer("x", x)
    _nonnegative_integer("y", y)
    _positive_integer("width", width)
    _positive_integer("height", height)
    _bounded_integer("radius", radius, 1, 100)
    _bounded_integer("power", power, 0, 6)
    if radius > min(width, height) // 2:
        raise GraphError("Blur radius cannot exceed half the smaller region side")
    clip = _media_with_optional_audio(source, include_audio)
    base, region_source = _require_video(clip).split()
    region = crop_video(region_source, width=width, height=height, x=x, y=y)
    region = region.filter(
        "boxblur",
        luma_radius=radius,
        luma_power=power,
        chroma_radius=min(radius, max(1, min(width, height) // 4)),
        chroma_power=power,
    )
    video = overlay_video(base, region, x=x, y=y, shortest=True)
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def boomerang(
    source: Pathish,
    to: Pathish,
    *,
    duration: float,
    start: float = 0,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Play a bounded clip forward and then backward."""

    _positive_number("duration", duration)
    _nonnegative_number("start", start)
    if duration > 15:
        raise GraphError("Boomerang duration cannot exceed 15 seconds")
    clip = media(source, audio=include_audio).trim(
        start=start,
        end=start + duration,
    )
    forward_video, reverse_video = _require_video(clip).split()
    reverse_video = reverse_video.filter("reverse")
    if clip.audio is None:
        joined = concat_clips(Clip(forward_video), Clip(reverse_video))
    else:
        forward_audio, reverse_audio = clip.audio.split()
        reverse_audio = reverse_audio.filter("areverse")
        joined = concat_clips(
            Clip(forward_video, forward_audio),
            Clip(reverse_video, reverse_audio),
        )
    plan = _web_plan(joined, to, (source,), preset, overwrite)
    if not include_audio:
        return plan
    fallback = boomerang(
        source,
        to,
        duration=duration,
        start=start,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, source)


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
    plan = _web_plan(clip, to, (source,), preset, overwrite)
    if not include_audio:
        return plan
    fallback = trim(
        source,
        to,
        start=start,
        end=end,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, source)


def loop_video(
    source: Pathish,
    to: Pathish,
    *,
    duration: float,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Repeat a media input until an exact output duration."""

    _bounded_number("duration", duration, 0.01, 86_400)
    include_audio = _require_boolean("include_audio", include_audio)
    clip = media(
        source,
        "-stream_loop",
        "-1",
        audio=include_audio,
    ).trim(start=0, end=duration)
    plan = _web_plan(clip, to, (source,), preset, overwrite)
    if not include_audio:
        return plan
    fallback = loop_video(
        source,
        to,
        duration=duration,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, source)


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
        _even_positive_integer("width", width)
    if height is not None:
        _even_positive_integer("height", height)
    clip = _media_with_optional_audio(source, include_audio).scale(
        width=width, height=height
    )
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
    plan = output(_audio_track(source, track), to=to, args=args)
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
    audio = _audio_track(audio_source, track)
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

    base = _media_with_optional_audio(source, include_audio)
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
    plan = _web_plan(joined, to, source_values, preset, overwrite)
    if not include_audio:
        return plan
    fallback = join_matching(
        source_values,
        to,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, *source_values)


def join_normalized(
    sources: Sequence[Pathish],
    to: Pathish,
    *,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    sample_rate: int = 48_000,
    color: str = "black",
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Normalize clip formats before joining their timelines."""

    source_values = _source_sequence(sources)
    if len(source_values) < 2:
        raise GraphError("Joining requires at least two sources")
    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    if isinstance(fps, bool) or not isinstance(fps, int) or not 1 <= fps <= 120:
        raise GraphError("Frame rate must be an integer between 1 and 120")
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, int)
        or not 8_000 <= sample_rate <= 192_000
    ):
        raise GraphError("Sample rate must be between 8000 and 192000")
    _nonempty_text("color", color)
    clips: list[Clip] = []
    for source in source_values:
        clip = media(source, audio=include_audio)
        video = _fit_canvas_video(
            _require_video(clip),
            width=width,
            height=height,
            color=color,
        ).filter("fps", fps=fps)
        audio = clip.audio
        if audio is not None:
            audio = audio.filter("aresample", sample_rate)
            audio = audio.filter("aformat", channel_layouts="stereo")
        clips.append(Clip(video, audio))
    plan = _web_plan(
        concat_clips(*clips),
        to,
        source_values,
        preset,
        overwrite,
    )
    if not include_audio:
        return plan
    fallback = join_normalized(
        source_values,
        to,
        width=width,
        height=height,
        fps=fps,
        sample_rate=sample_rate,
        color=color,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, *source_values)


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
        stream = _audio_track(source)
        if volumes is not None:
            _nonnegative_number("volume", volumes[index])
            stream = _volume_if_needed(stream, volumes[index])
        streams.append(stream)
    mixed = mix_audio(*streams, duration=duration, normalize=normalize)
    _validate_paths(source_values, to)
    plan = output(mixed, to=to, args=_audio_args(to, codec, bitrate))
    return _set_overwrite(plan, overwrite)


def join_audio_files(
    sources: Sequence[Pathish],
    to: Pathish,
    *,
    sample_rate: int = 48_000,
    layout: AudioLayout = "stereo",
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Normalize and join audio files end to end."""

    source_values = _source_sequence(sources)
    if len(source_values) < 2:
        raise GraphError("Joining audio requires at least two sources")
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, int)
        or not 8_000 <= sample_rate <= 192_000
    ):
        raise GraphError("Sample rate must be an integer from 8000 through 192000")
    if layout not in {"mono", "stereo"}:
        raise GraphError(f"Unknown audio layout: {layout}")
    streams: list[AudioStream] = []
    for source in source_values:
        audio = _audio_track(source).filter("aresample", sample_rate)
        audio = audio.filter("aformat", channel_layouts=layout)
        streams.append(audio.filter("asetpts", expr("PTS-STARTPTS")))
    (joined,) = apply_filter(
        streams,
        "concat",
        output_kinds=(StreamKind.AUDIO,),
        options={"n": len(streams), "v": 0, "a": 1},
    )
    assert isinstance(joined, AudioStream)
    return _audio_plan(joined, to, source_values, codec, bitrate, overwrite)


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
    _even_positive_integer("cell_width", cell_width)
    _even_positive_integer("cell_height", cell_height)
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

    clip = _media_with_optional_audio(source, include_audio)
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

    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    clip = _media_with_optional_audio(source, include_audio)
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
    plan = _web_plan(Clip(video, audio), to, (source,), preset, overwrite)
    if not include_audio:
        return plan
    fallback = change_speed(
        source,
        to,
        factor=factor,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, source)


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
        _audio_track(source),
        integrated=integrated,
        loudness_range=loudness_range,
        true_peak=true_peak,
        sample_rate=sample_rate,
    )
    plan = output(audio, to=to, args=_audio_args(to, codec, bitrate))
    return _set_overwrite(plan, overwrite)


def fit_canvas(
    source: Pathish,
    to: Pathish,
    *,
    width: int = 1920,
    height: int = 1080,
    color: str = "black",
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Fit video inside a fixed canvas without stretching it."""

    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    _nonempty_text("color", color)
    clip = _media_with_optional_audio(source, include_audio)
    video = _fit_canvas_video(
        _require_video(clip),
        width=width,
        height=height,
        color=color,
    )
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def picture_in_picture(
    source: Pathish,
    inset_source: Pathish,
    to: Pathish,
    *,
    inset_width: int = 480,
    position: NamedPosition = "bottom-right",
    padding: int = 24,
    opacity: float = 1,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Overlay a video inset while keeping the main audio."""

    _positive_integer("inset_width", inset_width)
    base = _media_with_optional_audio(source, include_audio)
    main = _require_video(base).filter("setpts", expr("PTS-STARTPTS"))
    inset = input(inset_source).video().filter("setpts", expr("PTS-STARTPTS"))
    inset = scale(inset, width=inset_width)
    x, y = named_overlay_position(position, padding=padding)
    video = overlay_video(
        main,
        inset,
        x=x,
        y=y,
        opacity=opacity,
        eof_action="pass",
    )
    return _web_plan(
        Clip(video, base.audio),
        to,
        (source, inset_source),
        preset,
        overwrite,
    )


def waveform_image(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    width: int = 1200,
    height: int = 400,
    color: str = "DodgerBlue",
    split_channels: bool = False,
    scale_mode: WaveformScale = "lin",
    overwrite: bool = False,
) -> Plan:
    """Render one audio track as a waveform image."""

    _nonnegative_integer("track", track)
    _positive_integer("width", width)
    _positive_integer("height", height)
    _nonempty_text("color", color)
    if not isinstance(split_channels, bool):
        raise GraphError("split_channels must be a Boolean")
    if scale_mode not in {"lin", "log", "sqrt", "cbrt"}:
        raise GraphError(f"Unknown waveform scale: {scale_mode}")
    waveform_options: dict[str, FilterValue] = {
        "s": f"{width}x{height}",
        "colors": color,
        "split_channels": split_channels,
        "scale": scale_mode,
        "filter": "peak",
    }
    (waveform,) = apply_filter(
        (_audio_track(source, track),),
        "showwavespic",
        output_kinds=(StreamKind.VIDEO,),
        options=waveform_options,
    )
    assert isinstance(waveform, VideoStream)
    return _single_image_plan(waveform, to, (source,), overwrite)


def spectrum_image(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    width: int = 1600,
    height: int = 900,
    mode: SpectrumMode = "combined",
    color: SpectrumColor = "viridis",
    legend: bool = True,
    overwrite: bool = False,
) -> Plan:
    """Render one audio track as a frequency spectrum image."""

    _nonnegative_integer("track", track)
    _positive_integer("width", width)
    _positive_integer("height", height)
    if mode not in {"combined", "separate"}:
        raise GraphError(f"Unknown spectrum mode: {mode}")
    if color not in {
        "channel",
        "intensity",
        "rainbow",
        "moreland",
        "nebulae",
        "fire",
        "fiery",
        "fruit",
        "cool",
        "magma",
        "green",
        "viridis",
        "plasma",
        "cividis",
        "terrain",
    }:
        raise GraphError(f"Unknown spectrum color: {color}")
    if not isinstance(legend, bool):
        raise GraphError("legend must be a Boolean")
    spectrum_options: dict[str, FilterValue] = {
        "s": f"{width}x{height}",
        "mode": mode,
        "color": color,
        "scale": "log",
        "legend": legend,
    }
    (spectrum,) = apply_filter(
        (_audio_track(source, track),),
        "showspectrumpic",
        output_kinds=(StreamKind.VIDEO,),
        options=spectrum_options,
    )
    assert isinstance(spectrum, VideoStream)
    spectrum = spectrum.filter("scale", width, height)
    return _single_image_plan(spectrum, to, (source,), overwrite)


def still_image_video(
    image: Pathish,
    audio_source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    width: int = 1920,
    height: int = 1080,
    color: str = "black",
    frame_rate: int = 25,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Create a video from one image and an audio track."""

    _nonnegative_integer("track", track)
    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    _positive_integer("frame_rate", frame_rate)
    _nonempty_text("color", color)
    picture = input(
        image,
        "-loop",
        "1",
        "-framerate",
        str(frame_rate),
    ).video()
    picture = _fit_canvas_video(
        picture,
        width=width,
        height=height,
        color=color,
    )
    audio = _audio_track(audio_source, track)
    return _web_plan(
        Clip(picture, audio),
        to,
        (image, audio_source),
        preset,
        overwrite,
        ("-shortest", "-tune", "stillimage"),
    )


def contact_sheet(
    source: Pathish,
    to: Pathish,
    *,
    columns: int = 4,
    rows: int = 4,
    interval: float = 5,
    cell_width: int = 320,
    cell_height: int = 180,
    padding: int = 4,
    margin: int = 8,
    color: str = "black",
    overwrite: bool = False,
) -> Plan:
    """Sample a video into one fixed-size contact sheet."""

    _positive_integer("columns", columns)
    _positive_integer("rows", rows)
    _positive_number("interval", interval)
    _positive_integer("cell_width", cell_width)
    _positive_integer("cell_height", cell_height)
    _nonnegative_integer("padding", padding)
    _nonnegative_integer("margin", margin)
    _nonempty_text("color", color)
    count = columns * rows
    video = input(source).video().filter("fps", fps=1 / interval)
    video = _fit_canvas_video(
        video,
        width=cell_width,
        height=cell_height,
        color=color,
    )
    video = video.filter(
        "tile",
        layout=f"{columns}x{rows}",
        nb_frames=count,
        padding=padding,
        margin=margin,
        color=color,
    )
    return _single_image_plan(video, to, (source,), overwrite)


def duck_music(
    source: Pathish,
    music: Pathish,
    to: Pathish,
    *,
    music_volume: float = 0.3,
    loop_music: bool = True,
    threshold: float = 0.125,
    ratio: float = 8,
    attack: float = 20,
    release: float = 250,
    normalize: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Lower background music while source speech is active."""

    _nonnegative_number("music_volume", music_volume)
    _bounded_number("threshold", threshold, 0.000_975_63, 1)
    _bounded_number("ratio", ratio, 1, 20)
    _bounded_number("attack", attack, 0.01, 2_000)
    _bounded_number("release", release, 0.01, 9_000)
    if not isinstance(loop_music, bool):
        raise GraphError("loop_music must be a Boolean")
    source_clip = media(source)
    speech_control, speech_mix = _require_audio(source_clip).split()
    music_args = ("-stream_loop", "-1") if loop_music else ()
    music_audio = input(music, *music_args).audio()
    music_audio = _volume_if_needed(music_audio, music_volume)
    (ducked_music,) = apply_filter(
        (music_audio, speech_control),
        "sidechaincompress",
        output_kinds=(StreamKind.AUDIO,),
        options={
            "threshold": threshold,
            "ratio": ratio,
            "attack": attack,
            "release": release,
        },
    )
    assert isinstance(ducked_music, AudioStream)
    mixed = mix_audio(
        speech_mix,
        ducked_music,
        duration="first",
        dropout_transition=0,
        normalize=normalize,
    )
    return _web_plan(
        Clip(source_clip.video, mixed),
        to,
        (source, music),
        preset,
        overwrite,
    )


def fade_edges(
    source: Pathish,
    to: Pathish,
    *,
    duration: float,
    start: float = 0,
    fade_in: float = 1,
    fade_out: float = 1,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Trim a clip and apply matched fades at both edges."""

    _positive_number("duration", duration)
    _nonnegative_number("start", start)
    _nonnegative_number("fade_in", fade_in)
    _nonnegative_number("fade_out", fade_out)
    if fade_in + fade_out > duration:
        raise GraphError("Combined fades cannot exceed the clip duration")
    clip = media(source, audio=include_audio).trim(
        start=start,
        end=start + duration,
    )
    video = _require_video(clip)
    if fade_in > 0:
        video = video.filter("fade", t="in", st=0, d=fade_in)
    if fade_out > 0:
        video = video.filter(
            "fade",
            t="out",
            st=duration - fade_out,
            d=fade_out,
        )
    audio = clip.audio
    if audio is not None and fade_in > 0:
        audio = fade_audio(audio, fade_type="in", duration=fade_in)
    if audio is not None and fade_out > 0:
        audio = fade_audio(
            audio,
            fade_type="out",
            start=duration - fade_out,
            duration=fade_out,
        )
    plan = _web_plan(Clip(video, audio), to, (source,), preset, overwrite)
    if not include_audio:
        return plan
    fallback = fade_edges(
        source,
        to,
        duration=duration,
        start=start,
        fade_in=fade_in,
        fade_out=fade_out,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, source)


def blurred_background(
    source: Pathish,
    to: Pathish,
    *,
    width: int = 1920,
    height: int = 1080,
    blur: float = 20,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Place video over a blurred copy fitted to a canvas."""

    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    _positive_number("blur", blur)
    clip = _media_with_optional_audio(source, include_audio)
    background_input, foreground_input = _require_video(clip).split()
    background = background_input.filter(
        "scale",
        w=width,
        h=height,
        force_original_aspect_ratio="increase",
    )
    background = crop_video(background, width=width, height=height)
    background = background.filter("gblur", sigma=blur)
    foreground = foreground_input.filter(
        "scale",
        w=width,
        h=height,
        force_original_aspect_ratio="decrease",
        force_divisible_by=2,
    )
    video = overlay_video(
        background,
        foreground,
        x=expr("(W-w)/2"),
        y=expr("(H-h)/2"),
        shortest=True,
    )
    return _web_plan(Clip(video, clip.audio), to, (source,), preset, overwrite)


def reverse_clip(
    source: Pathish,
    to: Pathish,
    *,
    duration: float,
    start: float = 0,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Reverse a bounded clip of at most 60 seconds."""

    _positive_number("duration", duration)
    _nonnegative_number("start", start)
    if duration > 60:
        raise GraphError("Reverse clip duration cannot exceed 60 seconds")
    clip = media(source, audio=include_audio).trim(
        start=start,
        end=start + duration,
    )
    video = _require_video(clip).filter("reverse")
    video = video.filter("setpts", expr("PTS-STARTPTS"))
    audio = clip.audio
    if audio is not None:
        audio = audio.filter("areverse")
        audio = audio.filter("asetpts", expr("PTS-STARTPTS"))
    plan = _web_plan(Clip(video, audio), to, (source,), preset, overwrite)
    if not include_audio:
        return plan
    fallback = reverse_clip(
        source,
        to,
        duration=duration,
        start=start,
        include_audio=False,
        preset=preset,
        overwrite=overwrite,
    )
    return plan.with_missing_audio_fallback(fallback, source)


def denoise_audio(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    reduction: float = 12,
    noise_floor: float = -50,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Reduce steady background noise on one audio track."""

    _nonnegative_integer("track", track)
    _bounded_number("reduction", reduction, 0.01, 97)
    _bounded_number("noise_floor", noise_floor, -80, -20)
    audio = _audio_track(source, track).filter(
        "afftdn",
        nr=reduction,
        nf=noise_floor,
    )
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def compress_audio(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    threshold: float = 0.125,
    ratio: float = 3,
    attack: float = 20,
    release: float = 250,
    makeup: float = 1,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Even out level changes with an audio compressor."""

    _nonnegative_integer("track", track)
    _bounded_number("threshold", threshold, 0.000_975_63, 1)
    _bounded_number("ratio", ratio, 1, 20)
    _bounded_number("attack", attack, 0.01, 2_000)
    _bounded_number("release", release, 0.01, 9_000)
    _bounded_number("makeup", makeup, 1, 64)
    audio = _audio_track(source, track).filter(
        "acompressor",
        threshold=threshold,
        ratio=ratio,
        attack=attack,
        release=release,
        makeup=makeup,
    )
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def podcast_voice(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    highpass: int = 80,
    lowpass: int = 12_000,
    denoise: bool = True,
    compress: bool = True,
    integrated: float = -16,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Build a speech chain with filters that can be turned off."""

    _nonnegative_integer("track", track)
    _bounded_integer("highpass", highpass, 20, 2_000)
    _bounded_integer("lowpass", lowpass, 2_000, 22_000)
    if highpass >= lowpass:
        raise GraphError("Voice high-pass must be lower than low-pass")
    _require_boolean("denoise", denoise)
    _require_boolean("compress", compress)
    _bounded_number("integrated", integrated, -70, -5)
    audio = _audio_track(source, track).filter("highpass", f=highpass)
    audio = audio.filter("lowpass", f=lowpass)
    if denoise:
        audio = audio.filter("afftdn", nr=12, nf=-50)
    if compress:
        audio = audio.filter(
            "acompressor",
            threshold=0.125,
            ratio=3,
            attack=20,
            release=250,
        )
    audio = audio.filter("loudnorm", I=integrated, LRA=11, TP=-1.5)
    audio = audio.filter("aresample", 48_000)
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def trim_silence(
    source: Pathish,
    to: Pathish,
    *,
    duration: float,
    track: int = 0,
    threshold_db: float = -45,
    minimum: float = 0.25,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Remove edge silence within an explicit source-duration bound."""

    _bounded_number("duration", duration, 0.01, 600)
    _nonnegative_integer("track", track)
    _bounded_number("threshold_db", threshold_db, -90, 0)
    _bounded_number("minimum", minimum, 0.01, 10)
    options: dict[str, FilterValue] = {
        "start_periods": 1,
        "start_duration": minimum,
        "start_threshold": f"{threshold_db:g}dB",
    }
    audio = _audio_track(source, track).filter("atrim", end=duration)
    audio = audio.filter("asetpts", expr("PTS-STARTPTS"))
    audio = audio.filter("silenceremove", **options)
    audio = audio.filter("areverse")
    audio = audio.filter("silenceremove", **options)
    audio = audio.filter("areverse")
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def trim_audio_file(
    source: Pathish,
    to: Pathish,
    *,
    start: float | None = None,
    end: float | None = None,
    duration: float | None = None,
    track: int = 0,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Cut one audio track and reset its timeline."""

    _nonnegative_integer("track", track)
    if duration is not None:
        if end is not None:
            raise GraphError("Set audio trim end or duration, not both")
        _positive_number("duration", duration)
        start = 0 if start is None else start
        end = start + duration
    audio = trim_audio_stream(_audio_track(source, track), start=start, end=end)
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def mono_audio(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Downmix one selected audio track to mono."""

    _nonnegative_integer("track", track)
    audio = _audio_track(source, track).filter("aformat", channel_layouts="mono")
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def resample_audio(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    sample_rate: int = 48_000,
    layout: AudioLayout = "stereo",
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Set the sample rate and channel layout of one audio track."""

    _nonnegative_integer("track", track)
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, int)
        or not 8_000 <= sample_rate <= 192_000
    ):
        raise GraphError("Sample rate must be an integer from 8000 through 192000")
    if layout not in {"mono", "stereo"}:
        raise GraphError(f"Unknown audio layout: {layout}")
    audio = _audio_track(source, track).filter("aresample", sample_rate)
    audio = audio.filter("aformat", channel_layouts=layout)
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def set_audio_volume(
    source: Pathish,
    to: Pathish,
    *,
    gain_db: float = 0,
    track: int = 0,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Apply a fixed decibel gain to one audio track."""

    _nonnegative_integer("track", track)
    _bounded_number("gain_db", gain_db, -60, 30)
    audio = _audio_track(source, track).filter("volume", f"{gain_db:g}dB")
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def fade_audio_edges(
    source: Pathish,
    to: Pathish,
    *,
    duration: float,
    fade_in: float = 1,
    fade_out: float = 1,
    track: int = 0,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Apply optional fades at both edges of one audio track."""

    _positive_number("duration", duration)
    _nonnegative_number("fade_in", fade_in)
    _nonnegative_number("fade_out", fade_out)
    _nonnegative_integer("track", track)
    if fade_in + fade_out > duration:
        raise GraphError("Combined audio fades cannot exceed the source duration")
    audio = _audio_track(source, track)
    if fade_in > 0:
        audio = fade_audio(audio, fade_type="in", duration=fade_in)
    if fade_out > 0:
        audio = fade_audio(
            audio,
            fade_type="out",
            start=duration - fade_out,
            duration=fade_out,
        )
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def delay_audio_file(
    source: Pathish,
    to: Pathish,
    *,
    seconds: float,
    track: int = 0,
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Insert silence before one selected audio track."""

    _bounded_number("seconds", seconds, 0, 3_600)
    _nonnegative_integer("track", track)
    audio = delay_audio_stream(_audio_track(source, track), seconds)
    return _audio_plan(audio, to, (source,), codec, bitrate, overwrite)


def crossfade_audio(
    first: Pathish,
    second: Pathish,
    to: Pathish,
    *,
    duration: float = 1,
    curve: CrossfadeCurve = "tri",
    codec: AudioCodec = "wav",
    bitrate: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Join two audio files with a crossfade between them."""

    _positive_number("duration", duration)
    if curve not in {"tri", "qsin", "exp"}:
        raise GraphError(f"Unknown crossfade curve: {curve}")
    (audio,) = apply_filter(
        (_audio_track(first), _audio_track(second)),
        "acrossfade",
        output_kinds=(StreamKind.AUDIO,),
        options={"d": duration, "c1": curve, "c2": curve},
    )
    assert isinstance(audio, AudioStream)
    return _audio_plan(audio, to, (first, second), codec, bitrate, overwrite)


def extract_subtitles(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    overwrite: bool = False,
) -> Plan:
    """Extract one text subtitle track as SRT, WebVTT, or ASS."""

    _nonnegative_integer("track", track)
    suffix = _require_suffix(
        to,
        frozenset({".ass", ".srt", ".vtt"}),
        "Subtitle output",
    )
    codecs = {".ass": "ass", ".srt": "srt", ".vtt": "webvtt"}
    _validate_paths((source,), to)
    plan = output(
        input(source).subtitle(track),
        to=to,
        args=("-c:s", codecs[suffix]),
    )
    return _set_overwrite(plan, overwrite)


def add_subtitles(
    source: Pathish,
    subtitle_source: Pathish,
    to: Pathish,
    *,
    language: str = "eng",
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Add one selectable text subtitle track to an MP4."""

    if not re.fullmatch(r"[a-z]{3}", language):
        raise GraphError("Subtitle language must be a three-letter lowercase code")
    if preset != "web":
        raise GraphError(f"Unknown video preset: {preset}")
    _require_suffix(to, frozenset({".mp4"}), "Subtitled video output")
    _validate_paths((source, subtitle_source), to)
    source_input = input(source)
    streams: list[Stream] = [source_input.video()]
    if include_audio:
        streams.append(source_input.audio())
    streams.append(input(subtitle_source).subtitle())
    args = (*_web_args(has_audio=include_audio), "-c:s", "mov_text")
    args += ("-metadata:s:s:0", f"language={language}")
    return _set_overwrite(output(*streams, to=to, args=args), overwrite)


def burn_subtitles(
    source: Pathish,
    subtitle_source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    font_name: str | None = None,
    font_size: int | None = None,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Render one external subtitle track into every video frame."""

    _nonnegative_integer("track", track)
    if font_size is not None and (
        isinstance(font_size, bool)
        or not isinstance(font_size, int)
        or not 1 <= font_size <= 200
    ):
        raise GraphError("Subtitle font size must be between 1 and 200")
    style: list[str] = []
    if font_name is not None:
        _nonempty_text("font_name", font_name)
        if any(character in font_name for character in ",=\r\n"):
            raise GraphError("Subtitle font name contains unsupported punctuation")
        style.append(f"FontName={font_name}")
    if font_size is not None:
        style.append(f"FontSize={font_size}")
    subtitle_path = _subtitle_filter_path(subtitle_source)
    clip = _media_with_optional_audio(source, include_audio)
    options: dict[str, str | int] = {"filename": subtitle_path, "si": track}
    if style:
        options["force_style"] = ",".join(style)
    video = _require_video(clip).filter("subtitles", **options)
    return _web_plan(
        Clip(video, clip.audio),
        to,
        (source, subtitle_source),
        preset,
        overwrite,
    )


def remove_subtitles(
    source: Pathish,
    to: Pathish,
    *,
    include_audio: bool = True,
    preset: VideoPreset = "web",
    overwrite: bool = False,
) -> Plan:
    """Create an MP4 with only the first video and optional first audio."""

    clip = _media_with_optional_audio(source, include_audio)
    return _web_plan(clip, to, (source,), preset, overwrite)


def image_sequence_video(
    pattern: Pathish,
    to: Pathish,
    *,
    fps: int = 30,
    start_number: int = 1,
    width: int = 1920,
    height: int = 1080,
    color: str = "black",
    overwrite: bool = False,
) -> Plan:
    """Turn a numbered image pattern into a fixed-size MP4."""

    pattern_text = _path_text("Image pattern", pattern)
    if not re.search(r"%(?:0[1-9][0-9]*)?d", pattern_text):
        raise GraphError("Image pattern must contain %d or a form such as %04d")
    if isinstance(fps, bool) or not isinstance(fps, int) or not 1 <= fps <= 120:
        raise GraphError("Frame rate must be an integer between 1 and 120")
    _nonnegative_integer("start_number", start_number)
    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    _nonempty_text("color", color)
    source_input = input(
        pattern,
        "-framerate",
        str(fps),
        "-start_number",
        str(start_number),
    )
    video = _fit_canvas_video(
        source_input.video(),
        width=width,
        height=height,
        color=color,
    )
    _require_suffix(to, frozenset({".mp4"}), "Image sequence output")
    _validate_paths((pattern,), to)
    plan = output(video, to=to, args=_web_args(has_audio=False))
    return _set_overwrite(plan, overwrite)


def podcast_audiogram(
    audio_source: Pathish,
    cover_image: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    width: int = 1920,
    height: int = 1080,
    wave_width: int = 1600,
    wave_height: int = 240,
    wave_color: str = "white",
    frame_rate: int = 25,
    overwrite: bool = False,
) -> Plan:
    """Create a cover video with an animated audio waveform."""

    _nonnegative_integer("track", track)
    _even_positive_integer("width", width)
    _even_positive_integer("height", height)
    _positive_integer("wave_width", wave_width)
    _positive_integer("wave_height", wave_height)
    _positive_integer("frame_rate", frame_rate)
    _nonempty_text("wave_color", wave_color)
    if wave_width > width or wave_height > height:
        raise GraphError("Waveform dimensions must fit inside the video frame")
    picture = input(
        cover_image,
        "-loop",
        "1",
        "-framerate",
        str(frame_rate),
    ).video()
    picture = _fit_canvas_video(
        picture,
        width=width,
        height=height,
        color="black",
    )
    output_audio, visual_audio = _audio_track(audio_source, track).split()
    wave_options: dict[str, FilterValue] = {
        "s": f"{wave_width}x{wave_height}",
        "mode": "line",
        "colors": wave_color,
        "rate": frame_rate,
    }
    (wave,) = apply_filter(
        (visual_audio,),
        "showwaves",
        output_kinds=(StreamKind.VIDEO,),
        options=wave_options,
    )
    assert isinstance(wave, VideoStream)
    wave = wave.filter("colorkey", color="black", similarity=0.01, blend=0.1)
    video = overlay_video(
        picture,
        wave,
        x=expr("(W-w)/2"),
        y=expr("H-h-80"),
        shortest=True,
    )
    return _web_plan(
        Clip(video, output_audio),
        to,
        (audio_source, cover_image),
        "web",
        overwrite,
        ("-shortest", "-tune", "stillimage"),
    )


def strip_metadata(
    source: Pathish,
    to: Pathish,
    *,
    include_audio: bool = True,
    include_subtitles: bool = False,
    overwrite: bool = False,
) -> Plan:
    """Copy selected first streams without metadata or chapters."""

    _require_boolean("include_audio", include_audio)
    _require_boolean("include_subtitles", include_subtitles)
    _matching_suffix(source, to, "Metadata copy")
    _validate_paths((source,), to)
    source_input = input(source)
    streams: list[Stream] = [source_input.video()]
    if include_audio:
        streams.append(source_input.audio())
    if include_subtitles:
        streams.append(source_input.subtitle())
    plan = output(
        *streams,
        to=to,
        args=("-map_metadata", "-1", "-map_chapters", "-1", "-c", "copy"),
    )
    return _set_overwrite(plan, overwrite)


def remux_media(
    source: Pathish,
    to: Pathish,
    *,
    video_track: int = 0,
    audio_track: int = 0,
    subtitle_track: int = 0,
    include_audio: bool = True,
    include_subtitles: bool = False,
    overwrite: bool = False,
) -> Plan:
    """Copy selected streams into another media container."""

    _nonnegative_integer("video_track", video_track)
    _nonnegative_integer("audio_track", audio_track)
    _nonnegative_integer("subtitle_track", subtitle_track)
    include_audio = _require_boolean("include_audio", include_audio)
    include_subtitles = _require_boolean("include_subtitles", include_subtitles)
    _require_suffix(
        to,
        frozenset({".mkv", ".mov", ".mp4", ".webm"}),
        "Remux output",
    )
    _validate_paths((source,), to)
    source_input = input(source)
    streams: list[Stream] = [source_input.video(video_track)]
    if include_audio:
        streams.append(source_input.audio(audio_track, optional=True))
    if include_subtitles:
        streams.append(source_input.subtitle(subtitle_track))
    plan = output(*streams, to=to, args=("-c", "copy"))
    return _set_overwrite(plan, overwrite)


def tag_audio(
    source: Pathish,
    to: Pathish,
    *,
    track: int = 0,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    date: str | None = None,
    genre: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Copy one audio track and set supplied metadata fields."""

    _nonnegative_integer("track", track)
    _matching_suffix(source, to, "Tagged audio copy")
    _validate_paths((source,), to)
    fields = {
        "title": title,
        "artist": artist,
        "album": album,
        "date": date,
        "genre": genre,
    }
    selected = [(name, value) for name, value in fields.items() if value is not None]
    if not selected:
        raise GraphError("Set at least one audio metadata field")
    args: list[str] = ["-c:a", "copy"]
    for name, value in selected:
        assert value is not None
        _metadata_value(name, value)
        args.extend(("-metadata", f"{name}={value}"))
    plan = output(_audio_track(source, track), to=to, args=args)
    return _set_overwrite(plan, overwrite)


def tag_media(
    source: Pathish,
    to: Pathish,
    *,
    video_track: int = 0,
    audio_track: int = 0,
    subtitle_track: int = 0,
    include_audio: bool = True,
    include_subtitles: bool = False,
    title: str | None = None,
    artist: str | None = None,
    comment: str | None = None,
    date: str | None = None,
    copyright: str | None = None,
    overwrite: bool = False,
) -> Plan:
    """Copy selected media streams and set container metadata."""

    _nonnegative_integer("video_track", video_track)
    _nonnegative_integer("audio_track", audio_track)
    _nonnegative_integer("subtitle_track", subtitle_track)
    include_audio = _require_boolean("include_audio", include_audio)
    include_subtitles = _require_boolean("include_subtitles", include_subtitles)
    _matching_suffix(source, to, "Tagged media copy")
    _validate_paths((source,), to)
    fields = {
        "title": title,
        "artist": artist,
        "comment": comment,
        "date": date,
        "copyright": copyright,
    }
    selected = [(name, value) for name, value in fields.items() if value is not None]
    if not selected:
        raise GraphError("Set at least one media metadata field")
    source_input = input(source)
    streams: list[Stream] = [source_input.video(video_track)]
    if include_audio:
        streams.append(source_input.audio(audio_track, optional=True))
    if include_subtitles:
        streams.append(source_input.subtitle(subtitle_track))
    args: list[str] = ["-c", "copy"]
    for name, value in selected:
        assert value is not None
        _metadata_value(name, value)
        args.extend(("-metadata", f"{name}={value}"))
    plan = output(*streams, to=to, args=args)
    return _set_overwrite(plan, overwrite)


def _fit_canvas_video(
    video: VideoStream,
    *,
    width: int,
    height: int,
    color: str,
) -> VideoStream:
    fitted = video.filter(
        "scale",
        w=width,
        h=height,
        force_original_aspect_ratio="decrease",
        force_divisible_by=2,
    )
    fitted = fitted.filter(
        "pad",
        w=width,
        h=height,
        x=expr("(ow-iw)/2"),
        y=expr("(oh-ih)/2"),
        color=color,
    )
    return fitted.filter("setsar", 1)


def _single_image_plan(
    video: VideoStream,
    to: Pathish,
    sources: Sequence[Pathish],
    overwrite: bool,
) -> Plan:
    suffix = _require_suffix(
        to,
        frozenset({".jpg", ".jpeg", ".png", ".webp"}),
        "Image output",
    )
    args: tuple[str, ...] = ("-frames:v", "1")
    if suffix in {".jpg", ".jpeg"}:
        args += ("-q:v", "2")
    _validate_paths(sources, to)
    return _set_overwrite(output(video, to=to, args=args), overwrite)


def _audio_plan(
    audio: AudioStream,
    to: Pathish,
    sources: Sequence[Pathish],
    codec: AudioCodec,
    bitrate: str | None,
    overwrite: bool,
) -> Plan:
    if codec == "copy":
        raise GraphError("Filtered audio must be encoded")
    _validate_paths(sources, to)
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


def _web_args(
    *,
    has_audio: bool,
    crf: int = 20,
    encoder_preset: EncoderPreset = "medium",
    audio_bitrate: str = "192k",
) -> tuple[str, ...]:
    args = (
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        encoder_preset,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    )
    if has_audio:
        return (*args, "-c:a", "aac", "-b:a", audio_bitrate)
    return args


def _validate_encoder_preset(
    value: EncoderPreset,
    *,
    codec: str = "H.264",
) -> None:
    if value not in {
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
    }:
        raise GraphError(f"Unknown {codec} encoder preset: {value}")


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
    if codec == "opus":
        value = "128k" if bitrate is None else bitrate
        _validate_bitrate(value)
        return ("-c:a", "libopus", "-b:a", value)
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
    if not isinstance(value, str):
        raise GraphError("Audio bitrate must be text such as 128k")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)[kKmMgG]?", value)
    if match is None or float(match.group(1)) <= 0:
        raise GraphError("Audio bitrate must be a positive value such as 128k")


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


def _matching_suffix(source: Pathish, to: Pathish, label: str) -> None:
    source_suffix = os.path.splitext(_path_text("Input", source))[1].lower()
    output_suffix = os.path.splitext(_path_text("Output", to))[1].lower()
    if not source_suffix or source_suffix != output_suffix:
        raise GraphError(f"{label} input and output must use the same extension")


def _metadata_value(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GraphError(f"{name} metadata cannot be empty")
    if "\x00" in value:
        raise GraphError(f"{name} metadata cannot contain a null character")


def _validate_paths(sources: Sequence[Pathish], to: Pathish) -> None:
    destination = _path_text("Output", to)
    for source in sources:
        source_text = _path_text("Input", source)
        if same_destination(source_text, destination):
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


def _subtitle_filter_path(value: Pathish) -> str:
    text = _path_text("Subtitle", value)
    if os.name == "nt" or re.match(r"^[A-Za-z]:[\\/]", text) or text.startswith("\\\\"):
        text = text.replace("\\", "/")
    escaped: list[str] = []
    for character in text:
        if character in "\\':,;[]":
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


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


def _audio_track(source: Pathish, track: int = 0) -> AudioStream:
    return input(source).audio(track)


def _media_with_optional_audio(source: Pathish, include_audio: bool) -> Clip:
    return media(
        source,
        audio=include_audio,
        optional_audio=include_audio,
    )


def _require_audio(clip: Clip) -> AudioStream:
    if clip.audio is None:
        raise GraphError("Shortcut requires an audio stream")
    return clip.audio


def _volume_if_needed(stream: AudioStream, factor: float) -> AudioStream:
    return stream if factor == 1 else volume(stream, factor=factor)


def _positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GraphError(f"{name} must be a positive integer")


def _bounded_integer(name: str, value: int, minimum: int, maximum: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise GraphError(f"{name} must be between {minimum} and {maximum}")


def _even_positive_integer(name: str, value: int) -> None:
    _positive_integer(name, value)
    if value % 2 != 0:
        raise GraphError(f"{name} must be even for web video")


def _nonnegative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphError(f"{name} must be a nonnegative integer")


def _positive_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise GraphError(f"{name} must be a positive finite number")


def _nonnegative_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise GraphError(f"{name} must be a nonnegative finite number")


def _bounded_number(name: str, value: float, minimum: float, maximum: float) -> None:
    if (
        isinstance(value, bool)
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise GraphError(f"{name} must be between {minimum:g} and {maximum:g}")


def _nonempty_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise GraphError(f"{name} cannot be empty")
