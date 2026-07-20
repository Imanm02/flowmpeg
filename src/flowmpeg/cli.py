"""Command-line shortcuts for common media jobs."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import TextIO, cast

from flowmpeg import __version__, shortcuts
from flowmpeg.diagnostics import display_argv, redact_text
from flowmpeg.errors import (
    BinaryNotFoundError,
    BinaryUnusableError,
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
    "flowmpeg compress input.mov -o smaller.mp4",
    "flowmpeg social input.mp4 --target vertical -o vertical.mp4",
    "flowmpeg voice recording.wav -o finished.wav",
    "flowmpeg captions movie.mp4 subtitles.srt -o captioned.mp4",
    "flowmpeg timelapse frames/frame-%04d.png -o timelapse.mp4",
    "flowmpeg audiogram episode.wav cover.jpg -o episode.mp4",
    "flowmpeg probe input.mp4",
    "flowmpeg doctor",
    "flowmpeg setup",
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
        "filter:acrossfade",
        "filter:adelay",
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
    "creator-video": (
        "filter:boxblur",
        "filter:bwdif",
        "filter:eq",
        "filter:fps",
        "filter:tpad",
        "filter:unsharp",
        "filter:yadif",
    ),
    "voice-cleanup": (
        "filter:acompressor",
        "filter:afftdn",
        "filter:aformat",
        "filter:areverse",
        "filter:highpass",
        "filter:lowpass",
        "filter:silenceremove",
    ),
    "subtitles": (
        "encoder:ass",
        "encoder:mov_text",
        "encoder:srt",
        "encoder:webvtt",
    ),
    "audiogram": (
        "filter:colorkey",
        "filter:showwaves",
    ),
}

_ERROR_GUIDE = {
    "FMG200": (
        "Invalid media plan",
        "A path, option, stream selection, or graph connection is invalid.",
        "Read the message, correct the command arguments, then use --dry-run.",
    ),
    "FMG300": (
        "FFmpeg missing",
        "Flowmpeg could not start the FFmpeg executable.",
        "Run flowmpeg setup, install FFmpeg, then open a new terminal.",
    ),
    "FMG301": (
        "FFprobe missing",
        "Flowmpeg could not start the FFprobe executable.",
        "Run flowmpeg setup and confirm FFprobe is on PATH.",
    ),
    "FMG302": (
        "Media tool unusable",
        "A media executable exists but could not be run.",
        "Check execute permission, antivirus rules, and the configured path.",
    ),
    "FMG303": (
        "Installer unavailable",
        "No supported package manager was found.",
        "Install FFmpeg from ffmpeg.org, then run flowmpeg doctor.",
    ),
    "FMG304": (
        "Install failed",
        "The selected package manager returned a failure.",
        "Read its output, fix permissions or network access, then try again.",
    ),
    "FMG400": (
        "Output exists",
        "The destination exists and replacement was not enabled.",
        "Choose another output or add --overwrite.",
    ),
    "FMG500": (
        "Probe failed",
        "FFprobe could not read the requested input.",
        "Check the path, file permissions, URL access, and file integrity.",
    ),
    "FMG600": (
        "FFmpeg failed",
        "FFmpeg stopped while processing the command.",
        "Read the reported reason and rerun with --dry-run to inspect the command.",
    ),
    "FMG610": (
        "Encoder missing",
        "This FFmpeg build does not contain the requested encoder.",
        "Run flowmpeg doctor and install a build with the listed encoder.",
    ),
    "FMG611": (
        "Decoder missing",
        "FFmpeg cannot decode one of the input streams.",
        "Install a build with the required decoder or convert the input elsewhere.",
    ),
    "FMG612": (
        "Filter missing",
        "This FFmpeg build does not contain the requested filter.",
        "Run flowmpeg doctor and install a build with the listed filter.",
    ),
    "FMG620": (
        "Permission denied",
        "FFmpeg could not read an input or write the output.",
        "Check file permissions and write access to the output folder.",
    ),
    "FMG621": (
        "Storage full",
        "The output device ran out of free space.",
        "Free space, remove the partial output, then run the command again.",
    ),
    "FMG630": (
        "Network input failed",
        "A remote input could not be opened or authorized.",
        "Check the URL, credentials, connection, and protocol support.",
    ),
    "FMG700": (
        "Job timed out",
        "The configured timeout ended FFmpeg before it finished.",
        "Increase --timeout or omit it for long media jobs.",
    ),
}


@dataclass(frozen=True, slots=True)
class _Installer:
    manager: str
    commands: tuple[tuple[str, ...], ...]
    note: str


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
    _add_compress_video(commands)
    _add_reframe(commands)
    _add_social_video(commands)
    _add_frame_rate(commands)
    _add_deinterlace(commands)
    _add_flip(commands)
    _add_adjust_colors(commands)
    _add_sharpen(commands)
    _add_freeze_end(commands)
    _add_mute_section(commands)
    _add_blur_region(commands)
    _add_boomerang(commands)
    _add_denoise_audio(commands)
    _add_compress_audio(commands)
    _add_podcast_voice(commands)
    _add_trim_silence(commands)
    _add_mono_audio(commands)
    _add_crossfade_audio(commands)
    _add_extract_subtitles(commands)
    _add_add_subtitles(commands)
    _add_remove_subtitles(commands)
    _add_image_sequence(commands)
    _add_podcast_audiogram(commands)
    _add_strip_metadata(commands)
    _add_tag_audio(commands)
    _add_probe(commands)
    _add_doctor(commands)
    _add_setup(commands)
    _add_errors(commands)
    _add_explain_error(commands)
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
        return _error(error, 2, "FMG200")
    except BinaryNotFoundError as error:
        error_id = "FMG301" if error.tool == "ffprobe" else "FMG300"
        return _error(error, 3, error_id)
    except BinaryUnusableError as error:
        return _error(error, 3, "FMG302")
    except OutputExistsError as error:
        _error(error, 4, "FMG400")
        print("flowmpeg: add --overwrite to replace it", file=sys.stderr)
        return 4
    except ProbeError as error:
        return _probe_error(error)
    except ExecutionError as error:
        return _execution_error(error)
    except JobTimeoutError as error:
        return _error(error, 7, "FMG700")
    except KeyboardInterrupt:
        print("flowmpeg: interrupted", file=sys.stderr)
        return 130
    except FlowmpegError as error:
        return _error(error, 1, "FMG600")


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


def _add_compress_video(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "compress-video",
        "Reduce an MP4 file size with H.264 quality controls.",
        shortcuts.compress_video,
        ("source",),
        aliases=("compress", "smaller"),
    )
    _source(parser)
    parser.add_argument("--crf", type=_nonnegative_int, default=28)
    parser.add_argument(
        "--encoder-preset",
        choices=(
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ),
        default="medium",
    )
    parser.add_argument("--max-width", type=_positive_int)
    parser.add_argument("--audio-bitrate", default="128k")
    _audio_toggle(parser)
    _output(parser)


def _add_reframe(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "reframe",
        "Fill a fixed frame with a centered crop.",
        shortcuts.reframe,
        ("source",),
        aliases=("fill-frame",),
    )
    _source(parser)
    parser.add_argument("--width", type=_positive_int, default=1080)
    parser.add_argument("--height", type=_positive_int, default=1920)
    _audio_toggle(parser)
    _output(parser)


def _add_social_video(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "social-video",
        "Prepare a video for a common social frame size.",
        shortcuts.social_video,
        ("source",),
        aliases=("social",),
    )
    _source(parser)
    parser.add_argument(
        "--target",
        choices=("vertical", "portrait", "square", "landscape"),
        default="vertical",
    )
    parser.add_argument("--fill", choices=("blur", "crop", "fit"), default="blur")
    parser.add_argument("--color", default="black")
    parser.add_argument("--blur", type=_positive_float, default=20.0)
    _audio_toggle(parser)
    _output(parser)


def _add_frame_rate(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "set-frame-rate",
        "Convert video to a constant frame rate.",
        shortcuts.set_frame_rate,
        ("source",),
        aliases=("fps",),
    )
    _source(parser)
    parser.add_argument("--fps", type=_positive_int, default=30)
    _audio_toggle(parser)
    _output(parser)


def _add_deinterlace(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "deinterlace",
        "Remove interlacing from video.",
        shortcuts.deinterlace,
        ("source",),
    )
    _source(parser)
    parser.add_argument("--mode", choices=("bwdif", "yadif"), default="bwdif")
    _audio_toggle(parser)
    _output(parser)


def _add_flip(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "flip-video",
        "Mirror video on one axis or both axes.",
        shortcuts.flip_video,
        ("source",),
        aliases=("flip", "mirror"),
    )
    _source(parser)
    parser.add_argument(
        "--direction",
        choices=("horizontal", "vertical", "both"),
        default="horizontal",
    )
    _audio_toggle(parser)
    _output(parser)


def _add_adjust_colors(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "adjust-colors",
        "Adjust video brightness and color levels.",
        shortcuts.adjust_colors,
        ("source",),
        aliases=("color",),
    )
    _source(parser)
    parser.add_argument("--brightness", type=_finite_float, default=0.0)
    parser.add_argument("--contrast", type=_nonnegative_float, default=1.0)
    parser.add_argument("--saturation", type=_nonnegative_float, default=1.0)
    parser.add_argument("--gamma", type=_positive_float, default=1.0)
    _audio_toggle(parser)
    _output(parser)


def _add_sharpen(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _command(
        commands,
        "sharpen",
        "Apply bounded luma sharpening.",
        shortcuts.sharpen,
        ("source",),
    )
    _source(parser)
    parser.add_argument("--amount", type=_nonnegative_float, default=1.0)
    parser.add_argument("--matrix-size", type=_positive_int, default=5)
    _audio_toggle(parser)
    _output(parser)


def _add_freeze_end(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "freeze-end",
        "Hold the final frame and pad audio with silence.",
        shortcuts.freeze_end,
        ("source",),
        aliases=("freeze",),
    )
    _source(parser)
    parser.add_argument("--seconds", type=_positive_float, default=2.0)
    _audio_toggle(parser)
    _output(parser)


def _add_mute_section(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "mute-section",
        "Mute one time range in a video.",
        shortcuts.mute_section,
        ("source",),
        aliases=("silence-section",),
    )
    _source(parser)
    parser.add_argument("--start", type=_nonnegative_float, required=True)
    parser.add_argument("--end", type=_positive_float, required=True)
    _output(parser)


def _add_blur_region(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "blur-region",
        "Blur one fixed rectangle in a video.",
        shortcuts.blur_region,
        ("source",),
        aliases=("privacy-blur",),
    )
    _source(parser)
    parser.add_argument("--x", type=_nonnegative_int, required=True)
    parser.add_argument("--y", type=_nonnegative_int, required=True)
    parser.add_argument("--width", type=_positive_int, required=True)
    parser.add_argument("--height", type=_positive_int, required=True)
    parser.add_argument("--radius", type=_positive_int, default=12)
    parser.add_argument("--power", type=_nonnegative_int, default=2)
    _audio_toggle(parser)
    _output(parser)


def _add_boomerang(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "boomerang",
        "Play a short clip forward and backward.",
        shortcuts.boomerang,
        ("source",),
        aliases=("bounce",),
    )
    _source(parser)
    parser.add_argument("--duration", type=_positive_float, required=True)
    parser.add_argument("--start", type=_nonnegative_float, default=0.0)
    _audio_toggle(parser)
    _output(parser)


def _audio_file_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument(
        "--codec",
        choices=("mp3", "aac", "wav", "flac"),
        default="wav",
    )
    parser.add_argument("--bitrate")


def _add_denoise_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "denoise-audio",
        "Reduce steady background noise.",
        shortcuts.denoise_audio,
        ("source",),
        aliases=("denoise",),
    )
    _source(parser)
    parser.add_argument("--reduction", type=_positive_float, default=12.0)
    parser.add_argument("--noise-floor", type=_finite_float, default=-50.0)
    _audio_file_options(parser)
    _output(parser)


def _add_compress_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "compress-audio",
        "Even out audio level changes.",
        shortcuts.compress_audio,
        ("source",),
        aliases=("dynamics",),
    )
    _source(parser)
    parser.add_argument("--threshold", type=_positive_float, default=0.125)
    parser.add_argument("--ratio", type=_positive_float, default=3.0)
    parser.add_argument("--attack", type=_positive_float, default=20.0)
    parser.add_argument("--release", type=_positive_float, default=250.0)
    parser.add_argument("--makeup", type=_positive_float, default=1.0)
    _audio_file_options(parser)
    _output(parser)


def _add_podcast_voice(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "podcast-voice",
        "Clean and level a spoken-word recording.",
        shortcuts.podcast_voice,
        ("source",),
        aliases=("voice",),
    )
    _source(parser)
    parser.add_argument("--highpass", type=_positive_int, default=80)
    parser.add_argument("--lowpass", type=_positive_int, default=12_000)
    parser.add_argument(
        "--denoise",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--compress",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--integrated", type=_finite_float, default=-16.0)
    _audio_file_options(parser)
    _output(parser)


def _add_trim_silence(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "trim-silence",
        "Remove silence from the start and end of audio.",
        shortcuts.trim_silence,
        ("source",),
        aliases=("desilence",),
    )
    _source(parser)
    parser.add_argument("--threshold-db", type=_finite_float, default=-45.0)
    parser.add_argument("--minimum", type=_positive_float, default=0.25)
    _audio_file_options(parser)
    _output(parser)


def _add_mono_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "mono-audio",
        "Downmix one audio track to mono.",
        shortcuts.mono_audio,
        ("source",),
        aliases=("mono",),
    )
    _source(parser)
    _audio_file_options(parser)
    _output(parser)


def _add_crossfade_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "crossfade-audio",
        "Join two audio files with a crossfade.",
        shortcuts.crossfade_audio,
        ("first", "second"),
        aliases=("crossfade",),
    )
    _source(parser, "first")
    _source(parser, "second")
    parser.add_argument("--duration", type=_positive_float, default=1.0)
    parser.add_argument("--curve", choices=("tri", "qsin", "exp"), default="tri")
    parser.add_argument(
        "--codec",
        choices=("mp3", "aac", "wav", "flac"),
        default="wav",
    )
    parser.add_argument("--bitrate")
    _output(parser)


def _add_extract_subtitles(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "extract-subtitles",
        "Extract one text subtitle track.",
        shortcuts.extract_subtitles,
        ("source",),
        aliases=("subtitles",),
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    _output(parser)


def _add_add_subtitles(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "add-subtitles",
        "Add a selectable text subtitle track to an MP4.",
        shortcuts.add_subtitles,
        ("source", "subtitle_source"),
        aliases=("captions",),
    )
    _source(parser)
    _source(parser, "subtitle_source")
    parser.add_argument("--language", default="eng")
    _audio_toggle(parser)
    _output(parser)


def _add_remove_subtitles(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "remove-subtitles",
        "Create an MP4 without subtitle tracks.",
        shortcuts.remove_subtitles,
        ("source",),
        aliases=("strip-subtitles",),
    )
    _source(parser)
    _audio_toggle(parser)
    _output(parser)


def _add_image_sequence(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "image-sequence-video",
        "Turn numbered images into an MP4.",
        shortcuts.image_sequence_video,
        ("pattern",),
        aliases=("timelapse", "image-sequence"),
    )
    _source(parser, "pattern")
    parser.add_argument("--fps", type=_positive_int, default=30)
    parser.add_argument("--start-number", type=_nonnegative_int, default=1)
    parser.add_argument("--width", type=_positive_int, default=1920)
    parser.add_argument("--height", type=_positive_int, default=1080)
    parser.add_argument("--color", default="black")
    _output(parser)


def _add_podcast_audiogram(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "podcast-audiogram",
        "Create a cover video with an animated waveform.",
        shortcuts.podcast_audiogram,
        ("audio_source", "cover_image"),
        aliases=("audiogram",),
    )
    _source(parser, "audio_source")
    _source(parser, "cover_image")
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--width", type=_positive_int, default=1920)
    parser.add_argument("--height", type=_positive_int, default=1080)
    parser.add_argument("--wave-width", type=_positive_int, default=1600)
    parser.add_argument("--wave-height", type=_positive_int, default=240)
    parser.add_argument("--wave-color", default="white")
    parser.add_argument("--frame-rate", type=_positive_int, default=25)
    _output(parser)


def _add_strip_metadata(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "strip-metadata",
        "Copy selected streams without metadata or chapters.",
        shortcuts.strip_metadata,
        ("source",),
        aliases=("clean-metadata",),
    )
    _source(parser)
    _audio_toggle(parser)
    parser.add_argument("--subtitles", dest="include_subtitles", action="store_true")
    _output(parser)


def _add_tag_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "tag-audio",
        "Copy one audio track and set metadata fields.",
        shortcuts.tag_audio,
        ("source",),
        aliases=("tag",),
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--title")
    parser.add_argument("--artist")
    parser.add_argument("--album")
    parser.add_argument("--date")
    parser.add_argument("--genre")
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


def _add_setup(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "setup",
        aliases=["install-tools"],
        help="Check or install FFmpeg and FFprobe.",
        description=(
            "Check FFmpeg and FFprobe. Installation only runs with --install "
            "and confirmation."
        ),
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Run the detected package manager after confirmation",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm installation without an interactive prompt",
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    parser.add_argument("--timeout", type=_positive_float, default=10.0)
    parser.add_argument(
        "--install-timeout",
        type=_positive_float,
        default=600.0,
        help="Maximum seconds for each package manager command",
    )
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=_run_setup)


def _add_errors(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "errors",
        help="List Flowmpeg error identifiers.",
        description="List Flowmpeg error identifiers.",
        allow_abbrev=False,
    )
    parser.set_defaults(handler=_run_errors)


def _add_explain_error(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "explain-error",
        help="Explain one Flowmpeg error identifier.",
        description="Explain one Flowmpeg error identifier.",
        allow_abbrev=False,
    )
    parser.add_argument("error_id", help="Identifier such as FMG610")
    parser.set_defaults(handler=_run_explain_error)


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
    destinations = ", ".join(redact_text(destination) for destination in result.outputs)
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


def _run_setup(args: argparse.Namespace) -> int:
    install = cast(bool, args.install)
    assume_yes = cast(bool, args.yes)
    as_json = cast(bool, args.json)
    timeout = cast(float, args.timeout)
    install_timeout = cast(float, args.install_timeout)
    ffmpeg_executable = cast(str, args.ffmpeg)
    ffprobe_executable = cast(str, args.ffprobe)
    if assume_yes and not install:
        return _error(
            GraphError("--yes requires --install"),
            2,
            "FMG200",
        )
    if as_json and install:
        return _error(
            GraphError("--json cannot be combined with --install"),
            2,
            "FMG200",
        )

    ffmpeg = _tool_report(ffmpeg_executable, timeout)
    ffprobe = _tool_report(ffprobe_executable, timeout)
    ready = ffmpeg.get("ok") is True and ffprobe.get("ok") is True
    installer = _detect_installer()
    report: dict[str, object] = {
        "ok": ready,
        "platform": platform.platform(),
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "installer": _installer_data(installer),
        "changed": False,
    }
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if ready else 3

    print(_format_setup(report))
    if ready:
        print("FFmpeg and FFprobe are ready. No changes were made.")
        return 0
    if not install:
        print("No changes were made. Add --install to run the suggested command.")
        return 3
    if installer is None:
        return _error(
            FlowmpegError("no supported package manager was found"),
            3,
            "FMG303",
        )
    if not assume_yes:
        if not sys.stdin.isatty():
            return _error(
                GraphError("non-interactive setup requires --yes"),
                2,
                "FMG200",
            )
        try:
            answer = input("Run these package manager commands? [y/N] ").strip().lower()
        except EOFError:
            print("Installation cancelled. No changes were made.")
            return 3
        if answer not in {"y", "yes"}:
            print("Installation cancelled. No changes were made.")
            return 3

    for command in installer.commands:
        try:
            completed = subprocess.run(
                command,
                check=False,
                shell=False,
                timeout=install_timeout,
            )
        except subprocess.TimeoutExpired:
            return _error(
                FlowmpegError(
                    f"{installer.manager} timed out after {install_timeout:g} seconds"
                ),
                8,
                "FMG304",
            )
        except OSError as error:
            return _error(error, 8, "FMG304")
        if completed.returncode != 0:
            return _error(
                FlowmpegError(
                    f"{installer.manager} exited with code {completed.returncode}"
                ),
                8,
                "FMG304",
            )

    ffmpeg = _tool_report(ffmpeg_executable, timeout)
    ffprobe = _tool_report(ffprobe_executable, timeout)
    if ffmpeg.get("ok") is True and ffprobe.get("ok") is True:
        print("FFmpeg and FFprobe are ready.")
        return 0
    print(
        "The installer finished, but this process cannot find both tools. "
        "Open a new terminal and run flowmpeg doctor."
    )
    return 3


def _run_errors(args: argparse.Namespace) -> int:
    del args
    for error_id, (title, _, _) in _ERROR_GUIDE.items():
        print(f"{error_id}  {title}")
    return 0


def _run_explain_error(args: argparse.Namespace) -> int:
    error_id = cast(str, args.error_id).upper()
    guide = _ERROR_GUIDE.get(error_id)
    if guide is None:
        return _error(
            GraphError(f"unknown error identifier: {error_id}"),
            2,
            "FMG200",
        )
    title, cause, action = guide
    print(f"{error_id}: {title}")
    print(f"Cause: {cause}")
    print(f"Try: {action}")
    return 0


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


def _detect_installer() -> _Installer | None:
    system = platform.system()
    if system == "Windows":
        if shutil.which("winget"):
            return _Installer(
                "winget",
                (
                    (
                        "winget",
                        "install",
                        "--id",
                        "Gyan.FFmpeg",
                        "-e",
                        "--source",
                        "winget",
                        "--accept-source-agreements",
                        "--accept-package-agreements",
                    ),
                ),
                "Installs the exact Gyan.FFmpeg package from the winget source.",
            )
        if shutil.which("choco"):
            return _Installer(
                "Chocolatey",
                (("choco", "install", "ffmpeg", "-y"),),
                "Installs the ffmpeg Chocolatey package.",
            )
        if shutil.which("scoop"):
            return _Installer(
                "Scoop",
                (("scoop", "install", "ffmpeg"),),
                "Installs the ffmpeg Scoop package.",
            )
        return None
    if system == "Darwin" and shutil.which("brew"):
        return _Installer(
            "Homebrew",
            (("brew", "install", "ffmpeg"),),
            "Installs the Homebrew ffmpeg formula.",
        )
    if system != "Linux":
        return None
    if shutil.which("apt-get"):
        return _Installer(
            "APT",
            (
                _admin_command(("apt-get", "update")),
                _admin_command(("apt-get", "install", "-y", "ffmpeg")),
            ),
            "Uses the configured Debian or Ubuntu package sources.",
        )
    if shutil.which("pacman"):
        return _Installer(
            "pacman",
            (_admin_command(("pacman", "-S", "--needed", "--noconfirm", "ffmpeg")),),
            "Uses the configured Arch package sources.",
        )
    if shutil.which("apk"):
        return _Installer(
            "apk",
            (_admin_command(("apk", "add", "ffmpeg")),),
            "Uses the configured Alpine package sources.",
        )
    if shutil.which("brew"):
        return _Installer(
            "Linuxbrew",
            (("brew", "install", "ffmpeg"),),
            "Installs the Homebrew ffmpeg formula.",
        )
    return None


def _admin_command(command: tuple[str, ...]) -> tuple[str, ...]:
    get_effective_user = getattr(os, "geteuid", None)
    if callable(get_effective_user) and get_effective_user() == 0:
        return command
    return ("sudo", *command) if shutil.which("sudo") else command


def _installer_data(installer: _Installer | None) -> dict[str, object] | None:
    if installer is None:
        return None
    return {
        "manager": installer.manager,
        "commands": [list(command) for command in installer.commands],
        "note": installer.note,
    }


def _format_setup(report: dict[str, object]) -> str:
    lines = [f"Platform: {report['platform']}"]
    for name in ("ffmpeg", "ffprobe"):
        item = cast(dict[str, object], report[name])
        status = item.get("status", "ready" if item.get("ok") else "missing")
        lines.append(f"{name}: {status}")
        if item.get("path"):
            lines.append(f"  path: {item['path']}")
        if item.get("version"):
            lines.append(f"  version: {item['version']}")
    installer = report.get("installer")
    if isinstance(installer, dict):
        lines.append(f"Package manager: {installer['manager']}")
        commands = cast(list[list[str]], installer["commands"])
        for command in commands:
            lines.append(f"  suggested: {display_argv(command, redact=False)}")
        lines.append(f"  note: {installer['note']}")
    else:
        lines.append("Package manager: no supported manager found")
        if platform.system() == "Linux" and (
            shutil.which("dnf") or shutil.which("zypper")
        ):
            lines.append(
                "  Flowmpeg will not add third-party codec repositories. "
                "Follow your distribution's FFmpeg instructions."
            )
        else:
            lines.append("  Install from https://ffmpeg.org/download.html")
    return "\n".join(lines)


def _tool_report(executable: str, timeout: float) -> dict[str, object]:
    path = shutil.which(executable)
    if path is None:
        return {
            "ok": False,
            "status": "missing",
            "path": None,
            "version": None,
            "returncode": None,
            "reason": None,
        }
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
    except PermissionError as error:
        return {
            "ok": False,
            "status": "permission-denied",
            "path": path,
            "version": None,
            "returncode": None,
            "reason": redact_text(str(error))[:400] or None,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "status": "timeout",
            "path": path,
            "version": None,
            "returncode": None,
            "reason": f"Version check timed out after {timeout:g} seconds",
        }
    except OSError as error:
        return {
            "ok": False,
            "status": "unusable",
            "path": path,
            "version": None,
            "returncode": None,
            "reason": redact_text(str(error))[:400] or None,
        }
    version_text = completed.stdout or completed.stderr
    first_line = version_text.splitlines()[0] if version_text else None
    reason = None
    if completed.returncode != 0:
        reason = _stderr_reason(completed.stderr or completed.stdout)
    return {
        "ok": completed.returncode == 0,
        "status": "ready" if completed.returncode == 0 else "failed",
        "path": path,
        "version": first_line,
        "returncode": completed.returncode,
        "reason": reason,
    }


def _capability_report(ffmpeg: str, timeout: float) -> dict[str, bool]:
    filters = _listing(ffmpeg, "-filters", timeout)
    encoders = _listing(ffmpeg, "-encoders", timeout)
    muxers = _listing(ffmpeg, "-muxers", timeout)
    names = (
        "acompressor",
        "acrossfade",
        "adelay",
        "afade",
        "afftdn",
        "aformat",
        "amix",
        "apad",
        "areverse",
        "aresample",
        "asetpts",
        "asplit",
        "atempo",
        "atrim",
        "boxblur",
        "bwdif",
        "colorkey",
        "colorchannelmixer",
        "concat",
        "crop",
        "eq",
        "fade",
        "format",
        "fps",
        "gblur",
        "hflip",
        "highpass",
        "lowpass",
        "loudnorm",
        "overlay",
        "pad",
        "palettegen",
        "paletteuse",
        "reverse",
        "scale",
        "setpts",
        "showwavespic",
        "showwaves",
        "showspectrumpic",
        "sidechaincompress",
        "silenceremove",
        "split",
        "setsar",
        "tile",
        "tpad",
        "transpose",
        "trim",
        "unsharp",
        "vflip",
        "volume",
        "xstack",
        "yadif",
    )
    report = {f"filter:{name}": _listing_has(filters, name) for name in names}
    for name in (
        "aac",
        "ass",
        "flac",
        "gif",
        "libmp3lame",
        "libwebp",
        "libx264",
        "mjpeg",
        "mov_text",
        "pcm_s16le",
        "png",
        "srt",
        "webvtt",
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
        raw_status = item.get("status")
        if isinstance(raw_status, str):
            status = raw_status
        else:
            status = "ready" if item.get("ok") else "missing or unusable"
        lines.append(f"{name}: {status}")
        if item.get("path"):
            lines.append(f"  path: {item['path']}")
        if item.get("version"):
            lines.append(f"  version: {item['version']}")
        if item.get("returncode") is not None:
            lines.append(f"  return code: {item['returncode']}")
        if item.get("reason"):
            lines.append(f"  reason: {item['reason']}")
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


def _execution_error(error: ExecutionError) -> int:
    error_id = _execution_error_id(error.stderr)
    reason = _stderr_reason(error.stderr, error_id=error_id)
    print(
        f"flowmpeg [{error_id}]: FFmpeg exited with code {error.returncode}",
        file=sys.stderr,
    )
    if reason:
        print(f"Reason: {reason}", file=sys.stderr)
    print(
        f"Try: flowmpeg explain-error {error_id}",
        file=sys.stderr,
    )
    print(
        "A partial output may remain. Inspect it before running with --overwrite.",
        file=sys.stderr,
    )
    return 6


def _probe_error(error: ProbeError) -> int:
    print(f"flowmpeg [FMG500]: {error}", file=sys.stderr)
    if error.stderr:
        reason = _stderr_reason(error.stderr)
        if reason:
            print(f"Reason: {reason}", file=sys.stderr)
    print("Try: flowmpeg explain-error FMG500", file=sys.stderr)
    return 5


def _execution_error_id(stderr: str) -> str:
    lowered = stderr.lower()
    if re.search(r"unknown encoder|encoder .* not found|error selecting an encoder", lowered):
        return "FMG610"
    if re.search(r"unknown decoder|decoder .* not found", lowered):
        return "FMG611"
    if "no such filter" in lowered or "filter not found" in lowered:
        return "FMG612"
    if "permission denied" in lowered or "access is denied" in lowered:
        return "FMG620"
    if "no space left on device" in lowered or "disk full" in lowered:
        return "FMG621"
    if re.search(
        r"http error|server returned|401 unauthorized|403 forbidden|connection refused",
        lowered,
    ):
        return "FMG630"
    return "FMG600"


def _stderr_reason(
    stderr: str,
    limit: int = 400,
    *,
    error_id: str | None = None,
) -> str | None:
    ignored = (
        "conversion failed",
        "terminating thread with return code",
        "task finished with error code",
    )
    preferred = {
        "FMG610": (r"unknown encoder", r"encoder .* not found"),
        "FMG611": (r"unknown decoder", r"decoder .* not found"),
        "FMG612": (r"no such filter", r"filter not found"),
        "FMG620": (r"permission denied", r"access is denied"),
        "FMG621": (r"no space left", r"disk full"),
        "FMG630": (r"http error", r"server returned", r"connection refused"),
    }.get(error_id or "", ())
    lines = stderr.splitlines()
    if preferred:
        causal = [
            line for line in lines if any(re.search(pattern, line, re.I) for pattern in preferred)
        ]
        lines = causal or lines
    for line in reversed(lines):
        reason = line.strip()
        lowered = reason.lower()
        if not reason or lowered.startswith("frame="):
            continue
        if any(text in lowered for text in ignored):
            continue
        if len(reason) > limit:
            return reason[: limit - 3] + "..."
        return reason
    return None


def _error(error: BaseException, code: int, error_id: str) -> int:
    print(f"flowmpeg [{error_id}]: {error}", file=sys.stderr)
    if error_id in _ERROR_GUIDE:
        print(f"Try: flowmpeg explain-error {error_id}", file=sys.stderr)
    return code


__all__ = ["build_parser", "main"]
