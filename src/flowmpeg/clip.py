"""Paired audio and video operations."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from flowmpeg.errors import GraphError
from flowmpeg.model import FilterValue, StreamKind, expr
from flowmpeg.plan import Plan
from flowmpeg.plan import output as create_output
from flowmpeg.recipes.audio import mix_audio, trim_audio, volume
from flowmpeg.recipes.video import (
    named_overlay_position,
    overlay_video,
    scale,
    trim_video,
)
from flowmpeg.streams import (
    AudioStream,
    Stream,
    VideoStream,
    apply_filter,
    input,
)

OutputPreset = Literal["web"]


@dataclass(frozen=True, slots=True)
class Clip:
    """Video and audio streams that belong to one logical clip."""

    video: VideoStream | None = None
    audio: AudioStream | None = None

    def __post_init__(self) -> None:
        if self.video is None and self.audio is None:
            raise GraphError("Clips require video or audio")

    def trim(self, *, start: float | None = None, end: float | None = None) -> Clip:
        """Trim every present stream to the same time range."""

        video = (
            trim_video(self.video, start=start, end=end)
            if self.video is not None
            else None
        )
        audio = (
            trim_audio(self.audio, start=start, end=end)
            if self.audio is not None
            else None
        )
        return Clip(video, audio)

    def scale(self, *, width: int | None = None, height: int | None = None) -> Clip:
        """Scale video without changing the clip's audio stream."""

        if self.video is None:
            raise GraphError("Cannot scale a clip without video")
        return Clip(scale(self.video, width=width, height=height), self.audio)

    def overlay(
        self,
        foreground: Clip | VideoStream,
        *,
        position: str = "top-right",
        padding: int = 24,
        opacity: float = 1,
    ) -> Clip:
        """Overlay video while preserving this clip's audio stream."""

        if self.video is None:
            raise GraphError("Cannot overlay a clip without video")
        foreground_video = (
            foreground.video if isinstance(foreground, Clip) else foreground
        )
        if foreground_video is None:
            raise GraphError("Overlay clips require video")
        x, y = named_overlay_position(position, padding=padding)
        return Clip(
            overlay_video(
                self.video,
                foreground_video,
                x=x,
                y=y,
                opacity=opacity,
            ),
            self.audio,
        )

    def mix_audio(
        self,
        addition: Clip | AudioStream,
        *,
        addition_volume: float = 1,
        duration: Literal["first", "longest", "shortest"] = "first",
    ) -> Clip:
        """Mix another audio stream into this clip."""

        if self.audio is None:
            raise GraphError("Cannot mix a clip without existing audio")
        addition_audio = addition.audio if isinstance(addition, Clip) else addition
        if addition_audio is None:
            raise GraphError("Audio mix clips require audio")
        adjusted = volume(addition_audio, factor=addition_volume)
        return Clip(
            self.video,
            mix_audio(self.audio, adjusted, duration=duration),
        )

    def output(
        self,
        destination: str | os.PathLike[str],
        *,
        preset: OutputPreset | None = None,
        args: Iterable[str] = (),
        overwrite: bool = False,
    ) -> Plan:
        """Create an output plan for this clip."""

        output_args = _preset_args(self, preset) + tuple(args)
        streams = tuple(
            stream for stream in (self.video, self.audio) if stream is not None
        )
        plan = create_output(*streams, to=destination, args=output_args)
        return plan.overwrite() if overwrite else plan


def media(
    source: str | os.PathLike[str],
    *args: str,
    video: bool = True,
    audio: bool = True,
) -> Clip:
    """Create a paired clip from selected streams of one input."""

    if not video and not audio:
        raise GraphError("Media inputs require video or audio")
    source_input = input(source, *args)
    return Clip(
        source_input.video() if video else None,
        source_input.audio() if audio else None,
    )


def concat_clips(*clips: Clip) -> Clip:
    """Join clips whose stream formats already match."""

    if len(clips) < 2:
        raise GraphError("Clip concatenation requires at least two clips")
    has_video = {clip.video is not None for clip in clips}
    has_audio = {clip.audio is not None for clip in clips}
    if len(has_video) != 1 or len(has_audio) != 1:
        raise GraphError("Concatenated clips must have matching stream kinds")

    video_present = True in has_video
    audio_present = True in has_audio
    inputs: list[Stream] = []
    for clip in clips:
        if clip.video is not None:
            inputs.append(clip.video.filter("setpts", expr("PTS-STARTPTS")))
        if clip.audio is not None:
            inputs.append(clip.audio.filter("asetpts", expr("PTS-STARTPTS")))

    output_kinds: list[StreamKind] = []
    if video_present:
        output_kinds.append(StreamKind.VIDEO)
    if audio_present:
        output_kinds.append(StreamKind.AUDIO)
    options: dict[str, FilterValue] = {
        "n": len(clips),
        "v": video_present,
        "a": audio_present,
    }
    results = apply_filter(
        inputs,
        "concat",
        output_kinds=output_kinds,
        options=options,
    )
    result_video = next(
        (stream for stream in results if isinstance(stream, VideoStream)),
        None,
    )
    result_audio = next(
        (stream for stream in results if isinstance(stream, AudioStream)),
        None,
    )
    return Clip(result_video, result_audio)


def replace_audio(clip: Clip, audio: AudioStream) -> Clip:
    """Return a clip with the supplied audio stream."""

    return Clip(clip.video, audio)


def _preset_args(clip: Clip, preset: OutputPreset | None) -> tuple[str, ...]:
    if preset is None:
        return ()
    if preset != "web":
        raise GraphError(f"Unknown output preset: {preset}")

    args: list[str] = []
    if clip.video is not None:
        args.extend(
            (
                "-c:v",
                "libx264",
                "-crf",
                "20",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
            )
        )
    if clip.audio is not None:
        args.extend(("-c:a", "aac", "-b:a", "192k"))
    return tuple(args)
