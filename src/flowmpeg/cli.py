"""Command-line shortcuts for common media jobs."""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from typing import TextIO, cast

from flowmpeg import __version__, shortcuts
from flowmpeg.diagnostics import redact_text
from flowmpeg.errors import (
    BinaryNotFoundError,
    CompilationError,
    ExecutionError,
    FlowmpegError,
    GraphError,
    JobTimeoutError,
    OutputExistsError,
    ProbeError,
)
from flowmpeg.plan import Plan
from flowmpeg.probe import (
    AudioStreamInfo,
    MediaInfo,
    SubtitleStreamInfo,
    VideoStreamInfo,
    probe,
    probe_raw,
)
from flowmpeg.progress import Progress

_Factory = Callable[..., Plan]
_Handler = Callable[[argparse.Namespace], int]

_CONTROL_NAMES = {
    "command",
    "dry_run",
    "expected_duration",
    "explain",
    "ffmpeg",
    "handler",
    "media_factory",
    "positionals",
    "progress",
    "timeout",
}

_EXAMPLES = (
    "flowmpeg cut input.mp4 --start 5 --duration 12 -o clip.mp4",
    "flowmpeg resize input.mp4 --width 1280 -o smaller.mp4",
    "flowmpeg mute input.mp4 -o silent.mp4",
    "flowmpeg audio input.mp4 -o track.mp3",
    "flowmpeg pip main.mp4 inset.mp4 -o result.mp4",
    "flowmpeg gif input.mp4 --start 3 --duration 4 -o preview.gif",
    "flowmpeg waveform song.mp3 -o waveform.png",
    "flowmpeg spectrum song.mp3 -o spectrum.png",
    "flowmpeg sheet input.mp4 --interval 8 -o sheet.jpg",
    "flowmpeg reverse input.mp4 --duration 6 -o reversed.mp4",
    "flowmpeg probe input.mp4",
    "flowmpeg doctor",
)

_DURATION_FACTORIES = (
    shortcuts.trim,
    shortcuts.make_gif,
    shortcuts.fade_edges,
    shortcuts.reverse_clip,
)

_FEATURE_REQUIREMENTS = {
    "web-video": (
        "encoder:aac",
        "encoder:libx264",
        "muxer:mp4",
    ),
    "audio-files": (
        "encoder:aac",
        "encoder:flac",
        "encoder:libmp3lame",
        "encoder:pcm_s16le",
        "muxer:flac",
        "muxer:mp3",
        "muxer:wav",
    ),
    "composition": (
        "filter:concat",
        "filter:crop",
        "filter:overlay",
        "filter:pad",
        "filter:scale",
        "filter:xstack",
    ),
    "video-effects": (
        "filter:colorchannelmixer",
        "filter:fade",
        "filter:format",
        "filter:gblur",
        "filter:hflip",
        "filter:transpose",
        "filter:vflip",
    ),
    "animated-gif": (
        "encoder:gif",
        "filter:fps",
        "filter:palettegen",
        "filter:paletteuse",
        "filter:scale",
        "filter:split",
        "muxer:gif",
    ),
    "analysis-images": (
        "encoder:libwebp",
        "encoder:mjpeg",
        "encoder:png",
        "filter:showspectrumpic",
        "filter:showwavespic",
        "filter:tile",
        "muxer:image2",
    ),
    "audio-processing": (
        "filter:afade",
        "filter:amix",
        "filter:apad",
        "filter:aresample",
        "filter:asplit",
        "filter:atempo",
        "filter:loudnorm",
        "filter:sidechaincompress",
        "filter:volume",
    ),
    "reverse": (
        "filter:areverse",
        "filter:asetpts",
        "filter:reverse",
        "filter:setpts",
    ),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the public command parser."""

    parser = argparse.ArgumentParser(
        prog="flowmpeg",
        description=(
            "Run common FFmpeg jobs with readable one-line commands. "
            "Editing commands run immediately. Use --dry-run on a command to "
            "preview it, and --overwrite to replace an existing output. "
            "FFmpeg and FFprobe must be installed separately."
        ),
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"flowmpeg {__version__}",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    _add_transcode(commands)
    _add_trim(commands)
    _add_resize(commands)
    _add_remove_audio(commands)
    _add_extract_audio(commands)
    _add_replace_audio(commands)
    _add_watermark(commands)
    _add_add_music(commands)
    _add_join(commands)
    _add_mix_audio(commands)
    _add_grid(commands)
    _add_thumbnail(commands)
    _add_gif(commands)
    _add_rotate(commands)
    _add_crop(commands)
    _add_speed(commands)
    _add_normalize(commands)
    _add_fit_canvas(commands)
    _add_picture_in_picture(commands)
    _add_waveform(commands)
    _add_spectrum(commands)
    _add_still_image_video(commands)
    _add_contact_sheet(commands)
    _add_duck_music(commands)
    _add_fade_edges(commands)
    _add_blurred_background(commands)
    _add_reverse(commands)
    _add_probe(commands)
    _add_doctor(commands)
    _add_examples(commands)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    values = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not values:
        parser.print_help()
        return 0

    args = parser.parse_args(values)
    handler_value = getattr(args, "handler", None)
    if handler_value is None:
        parser.print_help()
        return 0
    handler = cast(_Handler, handler_value)

    try:
        return handler(args)
    except (GraphError, CompilationError) as error:
        return _error(error, 2)
    except BinaryNotFoundError as error:
        return _error(error, 3)
    except OutputExistsError as error:
        _error(error, 4)
        print("flowmpeg: add --overwrite to replace it", file=sys.stderr)
        return 4
    except ProbeError as error:
        return _error(error, 5)
    except ExecutionError as error:
        return _error(error, 6)
    except JobTimeoutError as error:
        return _error(error, 7)
    except KeyboardInterrupt:
        print("flowmpeg: interrupted", file=sys.stderr)
        return 130
    except FlowmpegError as error:
        return _error(error, 1)


def _command(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
    factory: _Factory,
    positionals: tuple[str, ...],
    *,
    aliases: Sequence[str] = (),
) -> argparse.ArgumentParser:
    parser = commands.add_parser(
        name,
        aliases=list(aliases),
        help=help_text,
        description=help_text,
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(
        handler=_run_media,
        media_factory=factory,
        positionals=positionals,
    )
    return parser


def _source(parser: argparse.ArgumentParser, name: str = "source") -> None:
    parser.add_argument(name, help="Input media path or URL")


def _output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the FFmpeg command without running it",
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        help="Maximum run time in seconds",
    )
    parser.add_argument(
        "--expected-duration",
        type=_positive_float,
        help="Expected output duration for percent progress",
    )
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show progress while FFmpeg runs",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Describe the plan before running it",
    )


def _audio_toggle(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--audio",
        dest="include_audio",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep the first audio track",
    )


def _normalize_toggle(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--normalize",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Normalize the mixed audio weights",
    )


def _add_transcode(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "transcode",
        "Convert a video to a web MP4.",
        shortcuts.transcode,
        ("source",),
        aliases=("convert",),
    )
    _source(parser)
    _audio_toggle(parser)
    _output(parser)


def _add_trim(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "trim",
        "Cut a section from a video.",
        shortcuts.trim,
        ("source",),
        aliases=("cut",),
    )
    _source(parser)
    parser.add_argument("--start", type=_nonnegative_float)
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument("--end", type=_positive_float)
    timing.add_argument("--duration", type=_positive_float)
    _audio_toggle(parser)
    _output(parser)


def _add_resize(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "resize",
        "Resize a video while keeping its aspect ratio.",
        shortcuts.resize,
        ("source",),
        aliases=("scale",),
    )
    _source(parser)
    size = parser.add_mutually_exclusive_group(required=True)
    size.add_argument("--width", type=_positive_int)
    size.add_argument("--height", type=_positive_int)
    _audio_toggle(parser)
    _output(parser)


def _add_remove_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "remove-audio",
        "Copy video without audio.",
        shortcuts.remove_audio,
        ("source",),
        aliases=("mute", "strip-audio"),
    )
    _source(parser)
    _output(parser)


def _add_extract_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "extract-audio",
        "Save one audio track to a new file.",
        shortcuts.extract_audio,
        ("source",),
        aliases=("audio",),
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument(
        "--codec",
        choices=("mp3", "aac", "wav", "flac", "copy"),
        default="mp3",
    )
    parser.add_argument("--bitrate")
    _output(parser)


def _add_replace_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "replace-audio",
        "Replace a video's audio track.",
        shortcuts.replace_audio,
        ("video_source", "audio_source"),
        aliases=("swap-audio",),
    )
    _source(parser, "video_source")
    _source(parser, "audio_source")
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--duration", choices=("video", "shortest"), default="video")
    parser.add_argument("--audio-codec", choices=("aac", "copy"), default="aac")
    parser.add_argument("--bitrate")
    _output(parser)


def _add_watermark(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "watermark",
        "Place an image over a video.",
        shortcuts.watermark,
        ("source", "image"),
        aliases=("mark",),
    )
    _source(parser)
    _source(parser, "image")
    parser.add_argument(
        "--position",
        choices=("top-left", "top-right", "bottom-left", "bottom-right", "center"),
        default="top-right",
    )
    parser.add_argument("--padding", type=_nonnegative_int, default=24)
    parser.add_argument("--width", type=_positive_int)
    parser.add_argument("--opacity", type=_finite_float, default=1.0)
    _audio_toggle(parser)
    _output(parser)


def _add_add_music(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "add-music",
        "Mix background music under a video.",
        shortcuts.add_music,
        ("source", "music"),
        aliases=("music",),
    )
    _source(parser)
    _source(parser, "music")
    parser.add_argument("--music-volume", type=_nonnegative_float, default=0.15)
    parser.add_argument("--source-volume", type=_nonnegative_float, default=1.0)
    parser.add_argument(
        "--source-audio",
        dest="source_has_audio",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--silent-source",
        action="store_false",
        dest="source_has_audio",
        help="Treat the source video as having no audio track",
    )
    parser.add_argument(
        "--loop-music",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    _normalize_toggle(parser)
    _output(parser)


def _add_join(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "join-matching",
        "Join videos with matching decoded formats.",
        shortcuts.join_matching,
        ("sources",),
        aliases=("join",),
    )
    parser.add_argument("sources", nargs="+", help="Input video paths")
    _audio_toggle(parser)
    _output(parser)


def _add_mix_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "mix-audio",
        "Mix two or more audio files.",
        shortcuts.mix_audio_files,
        ("sources",),
        aliases=("mix", "mix-audio-files"),
    )
    parser.add_argument("sources", nargs="+", help="Input audio paths")
    parser.add_argument("--volumes", nargs="+", type=_nonnegative_float)
    parser.add_argument(
        "--duration",
        choices=("longest", "shortest", "first"),
        default="longest",
    )
    _normalize_toggle(parser)
    parser.add_argument(
        "--codec",
        choices=("mp3", "aac", "wav", "flac"),
        default="wav",
    )
    parser.add_argument("--bitrate")
    _output(parser)


def _add_grid(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "grid",
        "Arrange videos in a fixed grid.",
        shortcuts.grid,
        ("sources",),
    )
    parser.add_argument("sources", nargs="+", help="Input video paths")
    parser.add_argument("--columns", type=_positive_int, default=2)
    parser.add_argument("--cell-width", type=_positive_int, default=640)
    parser.add_argument("--cell-height", type=_positive_int, default=360)
    parser.add_argument("--fill", default="black")
    parser.add_argument(
        "--shortest",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--keep-longest",
        action="store_false",
        dest="shortest",
        help="Keep the grid running until the longest input ends",
    )
    _output(parser)


def _add_thumbnail(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "thumbnail",
        "Save one video frame as an image.",
        shortcuts.thumbnail,
        ("source",),
        aliases=("thumb",),
    )
    _source(parser)
    parser.add_argument("--at", type=_nonnegative_float, default=0.0)
    parser.add_argument("--width", type=_positive_int)
    parser.add_argument("--quality", type=_positive_int, default=2)
    _output(parser)


def _add_gif(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "make-gif",
        "Create a palette-based animated GIF.",
        shortcuts.make_gif,
        ("source",),
        aliases=("gif",),
    )
    _source(parser)
    parser.add_argument("--start", type=_nonnegative_float, default=0.0)
    length = parser.add_mutually_exclusive_group()
    length.add_argument("--duration", type=_positive_float, default=5.0)
    length.add_argument(
        "--full",
        "--full-length",
        action="store_const",
        dest="duration",
        const=None,
    )
    sizing = parser.add_mutually_exclusive_group()
    sizing.add_argument("--width", type=_positive_int, default=480)
    sizing.add_argument(
        "--original-width",
        action="store_const",
        dest="width",
        const=None,
        help="Keep the source width",
    )
    parser.add_argument("--fps", type=_positive_int, default=12)
    parser.add_argument("--loop", type=int, default=0)
    _output(parser)


def _add_rotate(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "rotate",
        "Rotate a video by a quarter turn or half turn.",
        shortcuts.rotate,
        ("source",),
    )
    _source(parser)
    parser.add_argument("--degrees", type=int, choices=(90, 180, 270), default=90)
    _audio_toggle(parser)
    _output(parser)


def _add_crop(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "crop",
        "Crop a fixed rectangle from a video.",
        shortcuts.crop,
        ("source",),
    )
    _source(parser)
    parser.add_argument("--width", type=_positive_int, required=True)
    parser.add_argument("--height", type=_positive_int, required=True)
    parser.add_argument("--x", type=_nonnegative_int)
    parser.add_argument("--y", type=_nonnegative_int)
    _audio_toggle(parser)
    _output(parser)


def _add_speed(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "change-speed",
        "Change video and audio playback speed.",
        shortcuts.change_speed,
        ("source",),
        aliases=("speed",),
    )
    _source(parser)
    parser.add_argument("--factor", type=_positive_float, required=True)
    _audio_toggle(parser)
    _output(parser)


def _add_normalize(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "normalize-loudness",
        "Normalize one audio track with EBU R128.",
        shortcuts.normalize_loudness,
        ("source",),
        aliases=("normalize",),
    )
    _source(parser)
    parser.add_argument("--integrated", type=_finite_float, default=-16.0)
    parser.add_argument("--loudness-range", type=_positive_float, default=11.0)
    parser.add_argument("--true-peak", type=_finite_float, default=-1.5)
    parser.add_argument("--sample-rate", type=_positive_int, default=48_000)
    parser.add_argument(
        "--codec",
        choices=("mp3", "aac", "wav", "flac"),
        default="wav",
    )
    parser.add_argument("--bitrate")
    _output(parser)


def _add_fit_canvas(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "fit-canvas",
        "Fit video inside a fixed canvas without stretching.",
        shortcuts.fit_canvas,
        ("source",),
        aliases=("fit",),
    )
    _source(parser)
    parser.add_argument("--width", type=_positive_int, default=1920)
    parser.add_argument("--height", type=_positive_int, default=1080)
    parser.add_argument("--color", default="black")
    _audio_toggle(parser)
    _output(parser)


def _add_picture_in_picture(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "picture-in-picture",
        "Place a second video inside the main video.",
        shortcuts.picture_in_picture,
        ("source", "inset_source"),
        aliases=("pip",),
    )
    _source(parser)
    _source(parser, "inset_source")
    parser.add_argument("--inset-width", type=_positive_int, default=480)
    parser.add_argument(
        "--position",
        choices=("top-left", "top-right", "bottom-left", "bottom-right", "center"),
        default="bottom-right",
    )
    parser.add_argument("--padding", type=_nonnegative_int, default=24)
    parser.add_argument("--opacity", type=_finite_float, default=1.0)
    _audio_toggle(parser)
    _output(parser)


def _add_waveform(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "waveform-image",
        "Render an audio waveform image.",
        shortcuts.waveform_image,
        ("source",),
        aliases=("waveform",),
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--width", type=_positive_int, default=1200)
    parser.add_argument("--height", type=_positive_int, default=400)
    parser.add_argument("--color", default="DodgerBlue")
    parser.add_argument("--split-channels", action="store_true")
    parser.add_argument(
        "--scale-mode",
        choices=("lin", "log", "sqrt", "cbrt"),
        default="lin",
    )
    _output(parser)


def _add_spectrum(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "spectrum-image",
        "Render an audio frequency spectrum image.",
        shortcuts.spectrum_image,
        ("source",),
        aliases=("spectrum",),
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--width", type=_positive_int, default=1600)
    parser.add_argument("--height", type=_positive_int, default=900)
    parser.add_argument("--mode", choices=("combined", "separate"), default="combined")
    parser.add_argument(
        "--color",
        choices=(
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
        ),
        default="viridis",
    )
    parser.add_argument(
        "--legend",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    _output(parser)


def _add_still_image_video(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "still-image-video",
        "Create a video from one image and an audio track.",
        shortcuts.still_image_video,
        ("image", "audio_source"),
        aliases=("still-video",),
    )
    _source(parser, "image")
    _source(parser, "audio_source")
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--width", type=_positive_int, default=1920)
    parser.add_argument("--height", type=_positive_int, default=1080)
    parser.add_argument("--color", default="black")
    parser.add_argument("--frame-rate", type=_positive_int, default=25)
    _output(parser)


def _add_contact_sheet(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "contact-sheet",
        "Sample a video into one contact sheet image.",
        shortcuts.contact_sheet,
        ("source",),
        aliases=("sheet",),
    )
    _source(parser)
    parser.add_argument("--columns", type=_positive_int, default=4)
    parser.add_argument("--rows", type=_positive_int, default=4)
    parser.add_argument("--interval", type=_positive_float, default=5.0)
    parser.add_argument("--cell-width", type=_positive_int, default=320)
    parser.add_argument("--cell-height", type=_positive_int, default=180)
    parser.add_argument("--padding", type=_nonnegative_int, default=4)
    parser.add_argument("--margin", type=_nonnegative_int, default=8)
    parser.add_argument("--color", default="black")
    _output(parser)


def _add_duck_music(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "duck-music",
        "Lower music while source speech is active.",
        shortcuts.duck_music,
        ("source", "music"),
        aliases=("duck",),
    )
    _source(parser)
    _source(parser, "music")
    parser.add_argument("--music-volume", type=_nonnegative_float, default=0.3)
    parser.add_argument(
        "--loop-music",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--threshold", type=_positive_float, default=0.125)
    parser.add_argument("--ratio", type=_positive_float, default=8.0)
    parser.add_argument("--attack", type=_positive_float, default=20.0)
    parser.add_argument("--release", type=_positive_float, default=250.0)
    _normalize_toggle(parser)
    _output(parser)


def _add_fade_edges(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "fade-edges",
        "Trim a clip and fade both edges.",
        shortcuts.fade_edges,
        ("source",),
        aliases=("fade",),
    )
    _source(parser)
    parser.add_argument("--duration", type=_positive_float, required=True)
    parser.add_argument("--start", type=_nonnegative_float, default=0.0)
    parser.add_argument("--fade-in", type=_nonnegative_float, default=1.0)
    parser.add_argument("--fade-out", type=_nonnegative_float, default=1.0)
    _audio_toggle(parser)
    _output(parser)


def _add_blurred_background(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "blurred-background",
        "Fill a canvas with a blurred copy of the video.",
        shortcuts.blurred_background,
        ("source",),
        aliases=("blur-bg",),
    )
    _source(parser)
    parser.add_argument("--width", type=_positive_int, default=1920)
    parser.add_argument("--height", type=_positive_int, default=1080)
    parser.add_argument("--blur", type=_positive_float, default=20.0)
    _audio_toggle(parser)
    _output(parser)


def _add_reverse(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "reverse-clip",
        "Reverse a clip of up to 60 seconds.",
        shortcuts.reverse_clip,
        ("source",),
        aliases=("reverse",),
    )
    _source(parser)
    parser.add_argument("--duration", type=_positive_float, required=True)
    parser.add_argument("--start", type=_nonnegative_float, default=0.0)
    _audio_toggle(parser)
    _output(parser)


def _add_probe(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "probe",
        help="Inspect streams and container details.",
        description="Inspect streams and container details.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--json", action="store_true", help="Print typed JSON")
    display.add_argument("--raw", action="store_true", help="Print raw FFprobe JSON")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.set_defaults(handler=_run_probe)


def _add_doctor(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "doctor",
        help="Check FFmpeg, FFprobe, filters, and encoders.",
        description="Check FFmpeg, FFprobe, filters, and encoders.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    parser.add_argument("--timeout", type=_positive_float, default=10.0)
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=_run_doctor)


def _add_examples(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "examples",
        help="Print ready-to-edit command examples.",
        description="Print ready-to-edit command examples.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(handler=_run_examples)


def _run_media(args: argparse.Namespace) -> int:
    values = vars(args).copy()
    factory = cast(_Factory, values["media_factory"])
    positionals = cast(tuple[str, ...], values["positionals"])
    positional_values = [values.pop(name) for name in positionals]
    output_path = values.pop("output")

    dry_run = cast(bool, values["dry_run"])
    explain = cast(bool, values["explain"])
    ffmpeg = cast(str, values["ffmpeg"])
    timeout = cast(float | None, values["timeout"])
    expected_duration = cast(float | None, values["expected_duration"])
    show_progress = cast(bool, values["progress"])
    if expected_duration is None and factory in _DURATION_FACTORIES:
        known_duration = values.get("duration")
        if isinstance(known_duration, float):
            expected_duration = known_duration
    for name in _CONTROL_NAMES:
        values.pop(name, None)

    plan = factory(*positional_values, output_path, **values)
    if explain:
        print(plan.explain())
    if dry_run:
        print(plan.command(ffmpeg))
        return 0

    progress_printer = _ProgressPrinter(sys.stderr) if show_progress else None
    try:
        result = plan.run(
            ffmpeg=ffmpeg,
            on_progress=progress_printer,
            expected_duration=expected_duration,
            timeout=timeout,
        )
    finally:
        if progress_printer is not None:
            progress_printer.close()
    destinations = ", ".join(result.outputs)
    print(f"Finished in {result.elapsed:.2f}s: {destinations}")
    return 0


def _run_probe(args: argparse.Namespace) -> int:
    source = cast(str, args.source)
    ffprobe = cast(str, args.ffprobe)
    timeout = cast(float | None, args.timeout)
    if cast(bool, args.raw):
        data = probe_raw(source, ffprobe=ffprobe, timeout=timeout)
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
        return 0

    info = probe(source, ffprobe=ffprobe, timeout=timeout)
    if cast(bool, args.json):
        print(json.dumps(_redact_json(asdict(info)), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_media_info(info)))
    return 0


def _run_doctor(args: argparse.Namespace) -> int:
    timeout = cast(float, args.timeout)
    ffmpeg = _tool_report(cast(str, args.ffmpeg), timeout)
    ffprobe = _tool_report(cast(str, args.ffprobe), timeout)
    capabilities: dict[str, bool] = {}
    ffmpeg_path = ffmpeg.get("path")
    if ffmpeg.get("ok") is True and isinstance(ffmpeg_path, str):
        capabilities = _capability_report(ffmpeg_path, timeout)
    features = _feature_report(capabilities)
    okay = bool(ffmpeg.get("ok")) and bool(ffprobe.get("ok"))
    report: dict[str, object] = {
        "ok": okay,
        "flowmpeg_version": __version__,
        "python_version": platform.python_version(),
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "capabilities": capabilities,
        "features": features,
    }
    if cast(bool, args.json):
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_format_doctor(report))
    return 0 if okay else 3


def _run_examples(args: argparse.Namespace) -> int:
    del args
    print("\n".join(_EXAMPLES))
    return 0


class _ProgressPrinter:
    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._open = False

    def __call__(self, progress: Progress) -> None:
        if progress.state != "end" and not self._stream.isatty():
            return
        pieces: list[str] = []
        if progress.percent is not None:
            pieces.append(f"{progress.percent:.1f}%")
        if progress.output_time is not None:
            pieces.append(f"time={progress.output_time}")
        if progress.speed is not None:
            pieces.append(f"speed={progress.speed:g}x")
        if progress.frame is not None:
            pieces.append(f"frame={progress.frame}")
        if not pieces:
            pieces.append(progress.state)
        ending = "\n" if progress.state == "end" else "\r"
        print(
            "Progress: " + " ".join(pieces),
            file=self._stream,
            end=ending,
            flush=True,
        )
        self._open = progress.state != "end"

    def close(self) -> None:
        if self._open:
            print(file=self._stream, flush=True)
            self._open = False


def _show_progress(progress: Progress) -> None:
    _ProgressPrinter(sys.stderr)(progress)


def _format_media_info(info: MediaInfo) -> str:
    lines: list[str] = []
    if info.format is None:
        lines.append("Container: unknown")
    else:
        container = info.format.format_long_name or info.format.format_name or "unknown"
        lines.append(f"File: {info.format.filename or 'unknown'}")
        lines.append(f"Container: {container}")
        lines.append(f"Duration: {_seconds(info.format.duration)}")
        lines.append(f"Size: {_bytes(info.format.size)}")
    lines.append(f"Streams: {len(info.streams)}")
    for stream in info.streams:
        codec = stream.codec_name or "unknown"
        if isinstance(stream, VideoStreamInfo):
            dimensions = f"{stream.width or '?'}x{stream.height or '?'}"
            lines.append(f"  video #{stream.index}: {codec}, {dimensions}")
        elif isinstance(stream, AudioStreamInfo):
            rate = f"{stream.sample_rate} Hz" if stream.sample_rate else "unknown rate"
            channels = (
                f"{stream.channels} channel(s)"
                if stream.channels
                else "unknown channels"
            )
            lines.append(f"  audio #{stream.index}: {codec}, {rate}, {channels}")
        elif isinstance(stream, SubtitleStreamInfo):
            lines.append(f"  subtitle #{stream.index}: {codec}")
        else:
            lines.append(f"  {stream.codec_type} #{stream.index}: {codec}")
    return "\n".join(lines)


def _tool_report(executable: str, timeout: float) -> dict[str, object]:
    path = shutil.which(executable)
    if path is None:
        return {"ok": False, "path": None, "version": None}
    try:
        completed = subprocess.run(
            (path, "-version"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"ok": False, "path": path, "version": None}
    first_line = completed.stdout.splitlines()[0] if completed.stdout else None
    return {
        "ok": completed.returncode == 0,
        "path": path,
        "version": first_line,
    }


def _capability_report(ffmpeg: str, timeout: float) -> dict[str, bool]:
    filters = _listing(ffmpeg, "-filters", timeout)
    encoders = _listing(ffmpeg, "-encoders", timeout)
    muxers = _listing(ffmpeg, "-muxers", timeout)
    names = (
        "afade",
        "amix",
        "apad",
        "areverse",
        "aresample",
        "asetpts",
        "asplit",
        "atempo",
        "atrim",
        "colorchannelmixer",
        "concat",
        "crop",
        "fade",
        "format",
        "fps",
        "gblur",
        "hflip",
        "loudnorm",
        "overlay",
        "pad",
        "palettegen",
        "paletteuse",
        "reverse",
        "scale",
        "setpts",
        "showwavespic",
        "showspectrumpic",
        "sidechaincompress",
        "split",
        "setsar",
        "tile",
        "transpose",
        "trim",
        "vflip",
        "volume",
        "xstack",
    )
    report = {f"filter:{name}": _listing_has(filters, name) for name in names}
    for name in (
        "aac",
        "flac",
        "gif",
        "libmp3lame",
        "libwebp",
        "libx264",
        "mjpeg",
        "pcm_s16le",
        "png",
    ):
        report[f"encoder:{name}"] = _listing_has(encoders, name)
    for name in ("flac", "gif", "image2", "mp3", "mp4", "wav"):
        report[f"muxer:{name}"] = _listing_has(muxers, name)
    return report


def _feature_report(capabilities: dict[str, bool]) -> dict[str, bool]:
    return {
        feature: all(capabilities.get(name, False) for name in requirements)
        for feature, requirements in _FEATURE_REQUIREMENTS.items()
    }


def _listing(executable: str, option: str, timeout: float) -> str:
    try:
        completed = subprocess.run(
            (executable, "-hide_banner", option),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _listing_has(listing: str, name: str) -> bool:
    pattern = rf"(?m)^\s*\S+\s+{re.escape(name)}(?:\s|$)"
    return re.search(pattern, listing) is not None


def _format_doctor(report: dict[str, object]) -> str:
    lines = [
        f"Flowmpeg {report['flowmpeg_version']}",
        f"Python {report['python_version']}",
    ]
    for name in ("ffmpeg", "ffprobe"):
        item = cast(dict[str, object], report[name])
        status = "ok" if item.get("ok") else "missing or unusable"
        lines.append(f"{name}: {status}")
        if item.get("path"):
            lines.append(f"  path: {item['path']}")
        if item.get("version"):
            lines.append(f"  version: {item['version']}")
    capabilities = cast(dict[str, bool], report["capabilities"])
    if capabilities:
        available = sum(capabilities.values())
        lines.append(f"Capabilities: {available}/{len(capabilities)} available")
        missing = [name for name, present in capabilities.items() if not present]
        for name in missing:
            lines.append(f"  missing: {name}")
    features = cast(dict[str, bool], report["features"])
    if features:
        lines.append("Feature groups:")
        for name, present in features.items():
            lines.append(f"  {name}: {'ready' if present else 'limited'}")
    lines.append(f"Core ready: {'yes' if report['ok'] else 'no'}")
    return "\n".join(lines)


def _redact_json(value: object) -> object:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(key): _redact_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_redact_json(item) for item in value]
    return value


def _seconds(value: float | None) -> str:
    return "unknown" if value is None else f"{value:g} seconds"


def _bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    size = float(value)
    unit = units[0]
    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            break
        size /= 1024
    return f"{size:.2f} {unit}"


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def _nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("cannot be negative")
    return number


def _positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def _nonnegative_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("cannot be negative")
    return number


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("must be finite")
    return number


def _error(error: BaseException, code: int) -> int:
    print(f"flowmpeg: {error}", file=sys.stderr)
    return code


__all__ = ["build_parser", "main"]
