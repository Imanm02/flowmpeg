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
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from typing import TextIO, cast

from flowmpeg import __version__, shortcuts
from flowmpeg.artifacts import SegmentWorkflow, dash_package, hls_package
from flowmpeg.audit import (
    AuditConstraints,
    AuditExpectation,
    AuditThreshold,
    MediaAudit,
    audit_media,
)
from flowmpeg.black import BlackReport, detect_black
from flowmpeg.catalog import CATEGORIES, COMMAND_CATALOG, TAGS, command_spec
from flowmpeg.comparison import MediaComparison, MediaSummary, compare_media
from flowmpeg.crop_detection import CropReport, detect_crop
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
from flowmpeg.loudness import LoudnessMeasurement, measure_loudness
from flowmpeg.plan import Plan
from flowmpeg.probe import (
    AudioStreamInfo,
    MediaInfo,
    SubtitleStreamInfo,
    VideoStreamInfo,
    probe,
    probe_raw,
)
from flowmpeg.processes import popen_group_options, stop_process_tree
from flowmpeg.progress import Progress
from flowmpeg.scenes import SceneReport, detect_scenes
from flowmpeg.shortcuts import AudioCodec
from flowmpeg.silence import SilenceReport, detect_silence
from flowmpeg.workflows import normalize_loudness_two_pass

_Factory = Callable[..., Plan]
_ArtifactFactory = Callable[..., SegmentWorkflow]
_Handler = Callable[[argparse.Namespace], int]
_JSON_SCHEMA_VERSION = 1

_CONTROL_NAMES = {
    "command",
    "dry_run",
    "expected_duration",
    "explain",
    "ffmpeg",
    "ffprobe",
    "handler",
    "media_factory",
    "positionals",
    "progress",
    "probe_timeout",
    "timeout",
}


@dataclass(frozen=True, slots=True)
class _Example:
    category: str
    command: str
    tags: tuple[str, ...] = ()


_BASE_EXAMPLES = (
    _Example("video", "flowmpeg convert recording.mov -o recording.mp4"),
    _Example("video", "flowmpeg webm recording.mov -o recording.webm"),
    _Example("video", "flowmpeg hevc recording.mov -o recording-hevc.mp4"),
    _Example("video", "flowmpeg av1 recording.mov -o recording-av1.webm"),
    _Example("video", "flowmpeg hls recording.mov -o hls-delivery"),
    _Example("video", "flowmpeg dash recording.mov -o dash-delivery"),
    _Example("video", "flowmpeg convert animation.mov --no-audio -o animation.mp4"),
    _Example("video", "flowmpeg cut input.mp4 --start 5 --duration 12 -o clip.mp4"),
    _Example("video", "flowmpeg loop logo-motion.mp4 --duration 30 -o background.mp4"),
    _Example("video", "flowmpeg resize input.mp4 --width 1280 -o smaller.mp4"),
    _Example("video", "flowmpeg rotate sideways.mp4 --degrees 90 -o upright.mp4"),
    _Example("video", "flowmpeg mute input.mp4 -o silent.mp4"),
    _Example(
        "video", "flowmpeg reframe screen.mp4 --width 720 --height 1280 -o short.mp4"
    ),
    _Example("video", "flowmpeg fps phone.mp4 --fps 30 -o constant.mp4"),
    _Example("video", "flowmpeg deinterlace tape.mpg --mode yadif -o progressive.mp4"),
    _Example("video", "flowmpeg mirror selfie.mp4 -o normal-view.mp4"),
    _Example(
        "video", "flowmpeg crop wide.mp4 --width 1080 --height 1080 -o square.mp4"
    ),
    _Example("video", "flowmpeg speed lesson.mp4 --factor 1.5 -o faster.mp4"),
    _Example("video", "flowmpeg freeze announcement.mp4 --seconds 3 -o held.mp4"),
    _Example(
        "video",
        "flowmpeg silence-section meeting.mp4 --start 73 --end 81 -o redacted.mp4",
    ),
    _Example("audio", "flowmpeg audio input.mp4 -o track.mp3"),
    _Example("audio", "flowmpeg swap-audio video.mp4 narration.wav -o narrated.mp4"),
    _Example("audio", "flowmpeg mix host.wav guest.wav -o conversation.wav"),
    _Example("audio", "flowmpeg normalize voice.wav --integrated -23 -o broadcast.wav"),
    _Example(
        "audio",
        "flowmpeg normalize-exact voice.wav --target-integrated -16 -o exact.wav",
    ),
    _Example("audio", "flowmpeg denoise room.wav --reduction 10 -o clean.wav"),
    _Example("audio", "flowmpeg dynamics uneven.wav --ratio 4 -o controlled.wav"),
    _Example(
        "audio",
        "flowmpeg desilence take.wav --duration 120 --threshold-db -45 -o tight.wav",
    ),
    _Example(
        "audio",
        "flowmpeg cut-audio interview.wav --start 30 --duration 12 -o answer.wav",
    ),
    _Example("audio", "flowmpeg mono interview.wav --codec mp3 -o interview.mp3"),
    _Example(
        "audio",
        "flowmpeg resample interview.wav --sample-rate 48000 --layout mono -o standard.wav",
    ),
    _Example("audio", "flowmpeg gain quiet.wav --gain-db 6 -o louder.wav"),
    _Example(
        "audio",
        "flowmpeg audio-fade music.wav --duration 120 --fade-in 2 --fade-out 4 -o faded.wav",
    ),
    _Example("audio", "flowmpeg sync-audio narration.wav --seconds 0.35 -o synced.wav"),
    _Example("audio", "flowmpeg tempo lesson.wav --factor 1.5 -o lesson-fast.wav"),
    _Example(
        "audio", "flowmpeg crossfade intro.wav main.wav --duration 2 -o program.wav"
    ),
    _Example("audio", "flowmpeg audio-join intro.wav body.wav outro.wav -o show.wav"),
    _Example("audio", "flowmpeg music talk.mp4 music.mp3 -o scored.mp4"),
    _Example("audio", "flowmpeg duck talk.mp4 music.mp3 -o ducked.mp4"),
    _Example("audio", 'flowmpeg tag episode.m4a --title "Episode 12" -o tagged.m4a'),
    _Example("composition", "flowmpeg pip main.mp4 inset.mp4 -o result.mp4"),
    _Example("composition", "flowmpeg mark video.mp4 logo.png -o branded.mp4"),
    _Example("composition", "flowmpeg join part-1.mp4 part-2.mp4 -o joined.mp4"),
    _Example(
        "composition",
        "flowmpeg join-any phone.mp4 camera.mp4 --width 1280 --height 720 -o joined.mp4",
    ),
    _Example("composition", "flowmpeg grid cam-1.mp4 cam-2.mp4 -o grid.mp4"),
    _Example("composition", "flowmpeg fit portrait.mp4 -o portrait-wide.mp4"),
    _Example(
        "composition",
        "flowmpeg blurred-background portrait.mp4 -o portrait-wide.mp4",
    ),
    _Example(
        "composition", "flowmpeg still-video cover.jpg episode.mp3 -o episode.mp4"
    ),
    _Example("images", "flowmpeg gif input.mp4 --start 3 --duration 4 -o preview.gif"),
    _Example("images", "flowmpeg thumb video.mp4 --at 12 -o moment.jpg"),
    _Example("images", "flowmpeg waveform song.mp3 -o waveform.png"),
    _Example("images", "flowmpeg spectrum song.mp3 -o spectrum.png"),
    _Example("images", "flowmpeg sheet input.mp4 --interval 8 -o sheet.jpg"),
    _Example("effects", "flowmpeg reverse input.mp4 --duration 6 -o reversed.mp4"),
    _Example("effects", "flowmpeg fade video.mp4 --duration 12 -o faded.mp4"),
    _Example("effects", "flowmpeg color flat.mp4 --contrast 1.12 -o graded.mp4"),
    _Example("effects", "flowmpeg sharpen soft.mp4 --amount 1.2 -o sharp.mp4"),
    _Example(
        "effects",
        "flowmpeg privacy-blur street.mp4 --x 20 --y 20 --width 200 --height 80 -o private.mp4",
    ),
    _Example("video", "flowmpeg bounce jump.mp4 --duration 2 -o jump-bounce.mp4"),
    _Example("video", "flowmpeg compress input.mov -o smaller.mp4"),
    _Example("video", "flowmpeg social input.mp4 --target vertical -o vertical.mp4"),
    _Example("audio", "flowmpeg voice recording.wav -o finished.wav"),
    _Example("subtitles", "flowmpeg captions movie.mp4 subtitles.srt -o captioned.mp4"),
    _Example(
        "subtitles",
        "flowmpeg burn-captions movie.mp4 subtitles.srt -o open-captioned.mp4",
    ),
    _Example("subtitles", "flowmpeg subtitles film.mkv -o captions.srt"),
    _Example("subtitles", "flowmpeg strip-subtitles film.mkv -o clean.mp4"),
    _Example("metadata", "flowmpeg clean-metadata camera.mkv -o share.mkv"),
    _Example("metadata", "flowmpeg remux camera.mp4 -o camera.mkv"),
    _Example(
        "metadata",
        'flowmpeg tag-media camera.mp4 --title "Camera master" -o tagged.mp4',
    ),
    _Example("images", "flowmpeg timelapse frames/frame-%04d.png -o timelapse.mp4"),
    _Example("composition", "flowmpeg audiogram episode.wav cover.jpg -o episode.mp4"),
    _Example("inspect", "flowmpeg probe input.mp4"),
    _Example("inspect", "flowmpeg audit input.mp4 --expect av"),
    _Example("inspect", "flowmpeg compare original.mp4 smaller.mp4"),
    _Example("inspect", "flowmpeg loudness episode.wav"),
    _Example("inspect", "flowmpeg find-silence interview.wav"),
    _Example("inspect", "flowmpeg find-black tape.mp4"),
    _Example("inspect", "flowmpeg scenes interview.mp4"),
    _Example("inspect", "flowmpeg crop-report letterboxed.mp4 --duration 30"),
    _Example("inspect", "flowmpeg doctor"),
    _Example("inspect", "flowmpeg setup"),
    _Example("help", "flowmpeg errors"),
    _Example("help", "flowmpeg explain-error FMG610"),
    _Example("help", "flowmpeg examples --category video"),
    _Example("help", "flowmpeg commands --category audio"),
)


def _tag_example(example: _Example) -> _Example:
    command = example.command.split(maxsplit=2)[1]
    spec = command_spec(command)
    if spec is None:
        return example
    return replace(example, tags=spec.tags)


_EXAMPLES = tuple(_tag_example(example) for example in _BASE_EXAMPLES)

_DURATION_FACTORIES = (
    shortcuts.trim,
    shortcuts.boomerang,
    shortcuts.make_gif,
    shortcuts.fade_edges,
    shortcuts.reverse_clip,
)

_EXAMPLE_CATEGORIES = tuple(dict.fromkeys(example.category for example in _EXAMPLES))

_AUDIO_CODEC_CHOICES = ("mp3", "aac", "opus", "wav", "flac")

_FEATURE_REQUIREMENTS = {
    "web-video": (
        "encoder:aac",
        "encoder:libx264",
        "muxer:mp4",
    ),
    "webm-video": (
        "encoder:libopus",
        "encoder:libvpx-vp9",
        "muxer:webm",
    ),
    "hevc-video": (
        "encoder:aac",
        "encoder:libx265",
        "muxer:mp4",
    ),
    "av1-video": (
        "encoder:libopus",
        "encoder:libsvtav1",
        "muxer:webm",
    ),
    "segmented-video": (
        "encoder:aac",
        "encoder:libx264",
        "muxer:dash",
        "muxer:hls",
    ),
    "audio-files": (
        "encoder:aac",
        "encoder:flac",
        "encoder:libmp3lame",
        "encoder:libopus",
        "encoder:pcm_s16le",
        "muxer:flac",
        "muxer:ipod",
        "muxer:mp3",
        "muxer:opus",
        "muxer:wav",
    ),
    "composition": (
        "filter:aformat",
        "filter:aresample",
        "encoder:aac",
        "encoder:libx264",
        "filter:concat",
        "filter:crop",
        "filter:fps",
        "filter:gblur",
        "filter:overlay",
        "filter:pad",
        "filter:scale",
        "filter:setpts",
        "filter:setsar",
        "filter:split",
        "filter:xstack",
        "muxer:mp4",
    ),
    "video-effects": (
        "encoder:aac",
        "encoder:libx264",
        "filter:colorchannelmixer",
        "filter:fade",
        "filter:format",
        "filter:gblur",
        "filter:hflip",
        "filter:transpose",
        "filter:vflip",
        "muxer:mp4",
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
        "filter:fps",
        "filter:pad",
        "filter:scale",
        "filter:setsar",
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
        "encoder:aac",
        "encoder:libx264",
        "filter:areverse",
        "filter:asetpts",
        "filter:reverse",
        "filter:setpts",
        "muxer:mp4",
    ),
    "creator-video": (
        "encoder:aac",
        "encoder:libx264",
        "filter:boxblur",
        "filter:bwdif",
        "filter:eq",
        "filter:fps",
        "filter:tpad",
        "filter:unsharp",
        "filter:yadif",
        "muxer:mp4",
    ),
    "voice-cleanup": (
        "filter:acompressor",
        "filter:afftdn",
        "filter:aformat",
        "filter:areverse",
        "filter:highpass",
        "filter:lowpass",
        "filter:loudnorm",
        "filter:aresample",
        "filter:silenceremove",
        "encoder:pcm_s16le",
        "muxer:wav",
    ),
    "subtitles": (
        "encoder:aac",
        "encoder:ass",
        "encoder:libx264",
        "encoder:mov_text",
        "encoder:srt",
        "encoder:webvtt",
        "filter:subtitles",
        "muxer:mp4",
    ),
    "audiogram": (
        "encoder:aac",
        "encoder:libx264",
        "filter:asplit",
        "filter:colorkey",
        "filter:overlay",
        "filter:pad",
        "filter:scale",
        "filter:setsar",
        "filter:showwaves",
        "muxer:mp4",
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
    _add_transcode_webm(commands)
    _add_transcode_hevc(commands)
    _add_transcode_av1(commands)
    _add_hls(commands)
    _add_dash(commands)
    _add_trim(commands)
    _add_loop_video(commands)
    _add_resize(commands)
    _add_remove_audio(commands)
    _add_extract_audio(commands)
    _add_replace_audio(commands)
    _add_watermark(commands)
    _add_add_music(commands)
    _add_join(commands)
    _add_join_normalized(commands)
    _add_mix_audio(commands)
    _add_grid(commands)
    _add_thumbnail(commands)
    _add_gif(commands)
    _add_rotate(commands)
    _add_crop(commands)
    _add_speed(commands)
    _add_normalize(commands)
    _add_two_pass_normalize(commands)
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
    _add_trim_audio(commands)
    _add_mono_audio(commands)
    _add_resample_audio(commands)
    _add_volume_audio(commands)
    _add_fade_audio(commands)
    _add_delay_audio(commands)
    _add_speed_audio(commands)
    _add_crossfade_audio(commands)
    _add_join_audio(commands)
    _add_extract_subtitles(commands)
    _add_add_subtitles(commands)
    _add_burn_subtitles(commands)
    _add_remove_subtitles(commands)
    _add_image_sequence(commands)
    _add_podcast_audiogram(commands)
    _add_strip_metadata(commands)
    _add_remux(commands)
    _add_tag_media(commands)
    _add_tag_audio(commands)
    _add_probe(commands)
    _add_audit(commands)
    _add_compare(commands)
    _add_loudness(commands)
    _add_silence_detection(commands)
    _add_black_detection(commands)
    _add_scene_detection(commands)
    _add_crop_detection(commands)
    _add_doctor(commands)
    _add_setup(commands)
    _add_errors(commands)
    _add_explain_error(commands)
    _add_examples(commands)
    _add_commands(commands)
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
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    parser.add_argument(
        "--probe-timeout",
        type=_positive_float,
        default=10.0,
        help="Maximum seconds for automatic stream inspection",
    )
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


def _add_transcode_webm(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "transcode-webm",
        "Encode VP9 video and Opus audio in WebM.",
        shortcuts.transcode_webm,
        ("source",),
        aliases=("webm", "vp9"),
    )
    _source(parser)
    parser.add_argument("--crf", type=_nonnegative_int, default=32)
    parser.add_argument("--cpu-used", type=_nonnegative_int, default=2)
    parser.add_argument("--audio-bitrate", default="128k")
    _audio_toggle(parser)
    _output(parser)


def _add_transcode_hevc(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "transcode-hevc",
        "Encode HEVC video and AAC audio in MP4.",
        shortcuts.transcode_hevc,
        ("source",),
        aliases=("hevc", "h265"),
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
    parser.add_argument("--audio-bitrate", default="160k")
    _audio_toggle(parser)
    _output(parser)


def _add_transcode_av1(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "transcode-av1",
        "Encode AV1 video and Opus audio in WebM.",
        shortcuts.transcode_av1,
        ("source",),
        aliases=("av1", "svt-av1"),
    )
    _source(parser)
    parser.add_argument("--crf", type=_nonnegative_int, default=35)
    parser.add_argument("--speed", type=_nonnegative_int, default=8)
    parser.add_argument("--audio-bitrate", default="128k")
    _audio_toggle(parser)
    _output(parser)


def _add_hls(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    _add_artifact_command(
        commands,
        "package-hls",
        ("hls", "hls-vod"),
        "Create an owned HLS video-on-demand package.",
        hls_package,
        6.0,
    )


def _add_dash(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    _add_artifact_command(
        commands,
        "package-dash",
        ("dash", "mpeg-dash"),
        "Create an owned MPEG-DASH package.",
        dash_package,
        4.0,
    )


def _add_artifact_command(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    aliases: tuple[str, ...],
    help_text: str,
    factory: _ArtifactFactory,
    segment_duration: float,
) -> None:
    parser = commands.add_parser(
        name,
        aliases=list(aliases),
        help=help_text,
        description=help_text,
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Dedicated artifact directory",
    )
    parser.add_argument(
        "--segment-duration",
        type=_positive_float,
        default=segment_duration,
    )
    parser.add_argument("--crf", type=_nonnegative_int, default=23)
    parser.add_argument("--audio-bitrate", default="128k")
    _audio_toggle(parser)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace a matching Flowmpeg-owned artifact set",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--expected-duration", type=_positive_float)
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--explain", action="store_true")
    parser.set_defaults(handler=_run_artifact_workflow, artifact_factory=factory)


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


def _add_loop_video(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "loop-video",
        "Repeat a media input until an exact duration.",
        shortcuts.loop_video,
        ("source",),
        aliases=("loop", "repeat-video"),
    )
    _source(parser)
    parser.add_argument("--duration", type=_positive_float, required=True)
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
        choices=(*_AUDIO_CODEC_CHOICES, "copy"),
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


def _add_join_normalized(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "join-normalized",
        "Normalize different clips before joining them.",
        shortcuts.join_normalized,
        ("sources",),
        aliases=("join-any", "normalize-join"),
    )
    parser.add_argument("sources", nargs="+", help="Input media paths")
    parser.add_argument("--width", type=_positive_int, default=1920)
    parser.add_argument("--height", type=_positive_int, default=1080)
    parser.add_argument("--fps", type=_positive_int, default=30)
    parser.add_argument("--sample-rate", type=_positive_int, default=48_000)
    parser.add_argument("--color", default="black")
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
        choices=_AUDIO_CODEC_CHOICES,
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
        choices=_AUDIO_CODEC_CHOICES,
        default="wav",
    )
    parser.add_argument("--bitrate")
    _output(parser)


def _add_two_pass_normalize(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "normalize-loudness-two-pass",
        aliases=["normalize-exact", "loudnorm-two-pass"],
        help="Measure then normalize one audio track.",
        description="Run EBU R128 measurement before the encoding pass.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--target-integrated", type=_finite_float, default=-16.0)
    parser.add_argument("--target-peak", type=_finite_float, default=-1.5)
    parser.add_argument("--target-range", type=_positive_float, default=11.0)
    parser.add_argument("--sample-rate", type=_positive_int, default=48_000)
    parser.add_argument(
        "--codec",
        choices=_AUDIO_CODEC_CHOICES,
        default="wav",
    )
    parser.add_argument("--bitrate")
    parser.add_argument(
        "--measurement-timeout",
        type=_positive_float,
        help="Maximum seconds for the first pass",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Measure and print the second-pass plan without encoding",
    )
    _output(parser)
    parser.set_defaults(handler=_run_two_pass_loudness)


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
        choices=_AUDIO_CODEC_CHOICES,
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
    parser.add_argument(
        "--duration",
        type=_positive_float,
        required=True,
        help="Maximum source duration to inspect, up to 600 seconds",
    )
    parser.add_argument("--threshold-db", type=_finite_float, default=-45.0)
    parser.add_argument("--minimum", type=_positive_float, default=0.25)
    _audio_file_options(parser)
    _output(parser)


def _add_trim_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "trim-audio",
        "Cut one audio track and reset its timeline.",
        shortcuts.trim_audio_file,
        ("source",),
        aliases=("cut-audio", "audio-clip"),
    )
    _source(parser)
    parser.add_argument("--start", type=_nonnegative_float)
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument("--end", type=_positive_float)
    timing.add_argument("--duration", type=_positive_float)
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


def _add_resample_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "resample-audio",
        "Set one audio track's sample rate and channel layout.",
        shortcuts.resample_audio,
        ("source",),
        aliases=("resample", "audio-standard"),
    )
    _source(parser)
    parser.add_argument("--sample-rate", type=_positive_int, default=48_000)
    parser.add_argument("--layout", choices=("mono", "stereo"), default="stereo")
    _audio_file_options(parser)
    _output(parser)


def _add_volume_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "volume-audio",
        "Apply a fixed decibel gain to one audio track.",
        shortcuts.set_audio_volume,
        ("source",),
        aliases=("gain", "volume"),
    )
    _source(parser)
    parser.add_argument("--gain-db", type=_finite_float, required=True)
    _audio_file_options(parser)
    _output(parser)


def _add_fade_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "fade-audio",
        "Apply fades at both edges of one audio track.",
        shortcuts.fade_audio_edges,
        ("source",),
        aliases=("audio-fade",),
    )
    _source(parser)
    parser.add_argument("--duration", type=_positive_float, required=True)
    parser.add_argument("--fade-in", type=_nonnegative_float, default=1.0)
    parser.add_argument("--fade-out", type=_nonnegative_float, default=1.0)
    _audio_file_options(parser)
    _output(parser)


def _add_delay_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "delay-audio",
        "Insert silence before one selected audio track.",
        shortcuts.delay_audio_file,
        ("source",),
        aliases=("audio-delay", "sync-audio"),
    )
    _source(parser)
    parser.add_argument("--seconds", type=_nonnegative_float, required=True)
    _audio_file_options(parser)
    _output(parser)


def _add_speed_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "speed-audio",
        "Change one audio track's tempo without changing pitch.",
        shortcuts.change_audio_speed_file,
        ("source",),
        aliases=("audio-speed", "tempo"),
    )
    _source(parser)
    parser.add_argument("--factor", type=_positive_float, required=True)
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
        choices=_AUDIO_CODEC_CHOICES,
        default="wav",
    )
    parser.add_argument("--bitrate")
    _output(parser)


def _add_join_audio(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "join-audio",
        "Normalize and join audio files end to end.",
        shortcuts.join_audio_files,
        ("sources",),
        aliases=("concat-audio", "audio-join"),
    )
    parser.add_argument("sources", nargs="+", help="Input audio paths")
    parser.add_argument("--sample-rate", type=_positive_int, default=48_000)
    parser.add_argument("--layout", choices=("mono", "stereo"), default="stereo")
    parser.add_argument("--codec", choices=_AUDIO_CODEC_CHOICES, default="wav")
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


def _add_burn_subtitles(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "burn-subtitles",
        "Render subtitles into every video frame.",
        shortcuts.burn_subtitles,
        ("source", "subtitle_source"),
        aliases=("burn-captions", "hardcode-subtitles"),
    )
    _source(parser)
    _source(parser, "subtitle_source")
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--font-name")
    parser.add_argument("--font-size", type=_positive_int)
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


def _add_remux(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "remux",
        "Copy selected streams into another container.",
        shortcuts.remux_media,
        ("source",),
        aliases=("rewrap", "copy-container"),
    )
    _source(parser)
    parser.add_argument("--video-track", type=_nonnegative_int, default=0)
    parser.add_argument("--audio-track", type=_nonnegative_int, default=0)
    parser.add_argument("--subtitle-track", type=_nonnegative_int, default=0)
    _audio_toggle(parser)
    parser.add_argument(
        "--subtitles",
        dest="include_subtitles",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Copy one subtitle track",
    )
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


def _add_tag_media(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = _command(
        commands,
        "tag-media",
        "Copy selected streams and set container metadata.",
        shortcuts.tag_media,
        ("source",),
        aliases=("label-media",),
    )
    _source(parser)
    parser.add_argument("--video-track", type=_nonnegative_int, default=0)
    parser.add_argument("--audio-track", type=_nonnegative_int, default=0)
    parser.add_argument("--subtitle-track", type=_nonnegative_int, default=0)
    _audio_toggle(parser)
    parser.add_argument(
        "--subtitles",
        dest="include_subtitles",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Copy one subtitle track",
    )
    parser.add_argument("--title")
    parser.add_argument("--artist")
    parser.add_argument("--comment")
    parser.add_argument("--date")
    parser.add_argument("--copyright")
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


def _add_audit(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "audit-media",
        aliases=["audit", "check-media"],
        help="Check media shape against an expected policy.",
        description="Check media shape against an expected policy.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument(
        "--expect",
        choices=("any", "video", "audio", "av"),
        default="any",
        help="Required stream shape",
    )
    parser.add_argument(
        "--fail-on",
        choices=("never", "error", "warning"),
        default="error",
        help="Finding severity that returns exit code 9",
    )
    parser.add_argument("--min-duration", type=_positive_float)
    parser.add_argument("--max-duration", type=_positive_float)
    parser.add_argument("--width", type=_positive_int)
    parser.add_argument("--height", type=_positive_int)
    parser.add_argument("--video-codec")
    parser.add_argument("--audio-codec")
    parser.add_argument("--sample-rate", type=_positive_int)
    parser.add_argument("--channels", type=_positive_int)
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--json", action="store_true", help="Print audit JSON")
    parser.set_defaults(handler=_run_audit)


def _add_compare(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "compare",
        help="Compare two media files.",
        description="Compare measured media values before and after a job.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("before", help="Original media path")
    parser.add_argument("after", help="Changed media path")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--json", action="store_true", help="Print comparison JSON")
    parser.set_defaults(handler=_run_compare)


def _add_loudness(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "analyze-loudness",
        aliases=["loudness", "measure-loudness"],
        help="Measure EBU R128 audio loudness.",
        description="Measure one audio track without writing a media file.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument("--target-integrated", type=_finite_float, default=-16.0)
    parser.add_argument("--target-peak", type=_finite_float, default=-1.5)
    parser.add_argument("--target-range", type=_finite_float, default=11.0)
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--json", action="store_true", help="Print loudness JSON")
    parser.set_defaults(handler=_run_loudness)


def _add_silence_detection(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "detect-silence",
        aliases=["silence-report", "find-silence"],
        help="Find silent ranges in an audio track.",
        description="Find silent ranges without writing a media file.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument(
        "--noise-db",
        type=_finite_float,
        default=-40.0,
        help="Maximum sound level treated as silence",
    )
    parser.add_argument(
        "--minimum-duration",
        "--minimum",
        type=_positive_float,
        default=0.5,
        help="Shortest silence to report in seconds",
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--json", action="store_true", help="Print silence JSON")
    parser.set_defaults(handler=_run_silence_detection)


def _add_black_detection(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "detect-black",
        aliases=["black-report", "find-black"],
        help="Find black ranges in a video track.",
        description="Find black ranges without writing a media file.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument(
        "--picture-ratio",
        type=_finite_float,
        default=0.98,
        help="Required fraction of black pixels",
    )
    parser.add_argument(
        "--pixel-threshold",
        type=_finite_float,
        default=0.1,
        help="Normalized pixel level treated as black",
    )
    parser.add_argument(
        "--minimum-duration",
        "--minimum",
        type=_positive_float,
        default=0.5,
        help="Shortest black range to report in seconds",
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--json", action="store_true", help="Print black-range JSON")
    parser.set_defaults(handler=_run_black_detection)


def _add_scene_detection(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "detect-scenes",
        aliases=["scenes", "scene-report", "find-scenes"],
        help="Find scene-change timecodes in a video track.",
        description="Find scene-change candidates without writing a media file.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument(
        "--threshold",
        type=_finite_float,
        default=0.35,
        help="Minimum normalized scene-change score",
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--json", action="store_true", help="Print scene JSON")
    parser.set_defaults(handler=_run_scene_detection)


def _add_crop_detection(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "suggest-crop",
        aliases=["crop-report", "detect-crop"],
        help="Rank crop rectangles from video borders.",
        description="Scan a bounded video range and rank crop rectangles.",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _source(parser)
    parser.add_argument("--track", type=_nonnegative_int, default=0)
    parser.add_argument(
        "--limit",
        type=_nonnegative_float,
        default=24.0,
        help="Pixel level treated as black",
    )
    parser.add_argument(
        "--round",
        dest="round_to",
        type=_positive_int,
        default=2,
        help="Width and height divisibility",
    )
    parser.add_argument(
        "--skip-frames",
        type=_nonnegative_int,
        default=2,
        help="Initial filter samples to skip",
    )
    parser.add_argument("--start", type=_nonnegative_float)
    parser.add_argument(
        "--duration",
        type=_positive_float,
        default=60.0,
        help="Seconds to scan",
    )
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")
    parser.add_argument("--timeout", type=_positive_float)
    parser.add_argument("--json", action="store_true", help="Print crop JSON")
    parser.set_defaults(handler=_run_crop_detection)


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
    required = parser.add_mutually_exclusive_group()
    required.add_argument(
        "--require",
        choices=tuple(_FEATURE_REQUIREMENTS),
        help="Fail unless one feature group is ready",
    )
    required.add_argument(
        "--command",
        dest="required_command",
        choices=tuple(
            name
            for spec in COMMAND_CATALOG
            if spec.requirements
            for name in (spec.name, *spec.aliases)
        ),
        help="Fail unless one command's default path is ready",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Encode and probe a generated video",
    )
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
    parser.add_argument(
        "--category",
        choices=_EXAMPLE_CATEGORIES,
        help="Show one category",
    )
    parser.add_argument("--search", help="Find text in example commands")
    parser.add_argument("--tag", choices=TAGS, help="Show one use case")
    parser.add_argument("--json", action="store_true", help="Print example JSON")
    parser.set_defaults(handler=_run_examples)


def _add_commands(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = commands.add_parser(
        "commands",
        help="List commands by task category.",
        description="List commands by task category.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--category",
        choices=CATEGORIES,
        help="Show one task category",
    )
    parser.add_argument("--tag", choices=TAGS, help="Show one use case")
    parser.add_argument("--json", action="store_true", help="Print catalog JSON")
    parser.set_defaults(handler=_run_commands)


def _run_media(args: argparse.Namespace) -> int:
    values = vars(args).copy()
    factory = cast(_Factory, values["media_factory"])
    positionals = cast(tuple[str, ...], values["positionals"])
    positional_values = [values.pop(name) for name in positionals]
    output_path = values.pop("output")

    dry_run = cast(bool, values["dry_run"])
    explain = cast(bool, values["explain"])
    ffmpeg = cast(str, values["ffmpeg"])
    ffprobe = cast(str, values["ffprobe"])
    probe_timeout = cast(float, values["probe_timeout"])
    timeout = cast(float | None, values["timeout"])
    expected_duration = cast(float | None, values["expected_duration"])
    show_progress = cast(bool, values["progress"])
    if expected_duration is None and factory in _DURATION_FACTORIES:
        known_duration = values.get("duration")
        if isinstance(known_duration, float):
            expected_duration = (
                known_duration * 2 if factory is shortcuts.boomerang else known_duration
            )
        elif factory is shortcuts.trim:
            start = values.get("start")
            end = values.get("end")
            start_value = start if isinstance(start, float) else 0.0
            if isinstance(end, float):
                expected_duration = end - start_value
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
            ffprobe=ffprobe,
            probe_timeout=probe_timeout,
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


def _run_artifact_workflow(args: argparse.Namespace) -> int:
    factory = cast(_ArtifactFactory, args.artifact_factory)
    workflow = factory(
        cast(str, args.source),
        cast(str, args.output),
        segment_duration=cast(float, args.segment_duration),
        crf=cast(int, args.crf),
        audio_bitrate=cast(str, args.audio_bitrate),
        include_audio=cast(bool, args.include_audio),
        overwrite=cast(bool, args.overwrite),
    )
    ffmpeg = cast(str, args.ffmpeg)
    if cast(bool, args.explain) or cast(bool, args.dry_run):
        print(workflow.explain(ffmpeg))
    if cast(bool, args.dry_run):
        return 0

    progress_printer = (
        _ProgressPrinter(sys.stderr) if cast(bool, args.progress) else None
    )
    try:
        result = workflow.run(
            ffmpeg=ffmpeg,
            on_progress=progress_printer,
            expected_duration=cast(float | None, args.expected_duration),
            timeout=cast(float | None, args.timeout),
        )
    finally:
        if progress_printer is not None:
            progress_printer.close()
    print(
        f"Created {len(result.files)} {result.kind.upper()} artifacts: "
        f"{redact_text(result.manifest)}"
    )
    return 0


def _run_two_pass_loudness(args: argparse.Namespace) -> int:
    workflow = normalize_loudness_two_pass(
        cast(str, args.source),
        cast(str, args.output),
        track=cast(int, args.track),
        target_integrated=cast(float, args.target_integrated),
        target_peak=cast(float, args.target_peak),
        target_range=cast(float, args.target_range),
        sample_rate=cast(int, args.sample_rate),
        codec=cast(AudioCodec, args.codec),
        bitrate=cast(str | None, args.bitrate),
        overwrite=cast(bool, args.overwrite),
    )
    ffmpeg = cast(str, args.ffmpeg)
    if cast(bool, args.dry_run):
        if cast(bool, args.analyze_only):
            raise GraphError("Choose either --dry-run or --analyze-only")
        print(workflow.explain(ffmpeg))
        print("Pass 2 command: available after the measurement pass")
        return 0

    measurement_timeout = cast(float | None, args.measurement_timeout)
    if cast(bool, args.analyze_only):
        measurement = workflow.measure(ffmpeg=ffmpeg, timeout=measurement_timeout)
        plan = workflow.plan(measurement)
        print(_format_loudness(measurement))
        if cast(bool, args.explain):
            print("")
            print(plan.explain())
        print("")
        print(f"Pass 2: {plan.command(ffmpeg)}")
        return 0

    if cast(bool, args.explain):
        print(workflow.explain(ffmpeg))
    progress_printer = (
        _ProgressPrinter(sys.stderr) if cast(bool, args.progress) else None
    )
    try:
        result = workflow.run(
            ffmpeg=ffmpeg,
            measurement_timeout=measurement_timeout,
            timeout=cast(float | None, args.timeout),
            on_progress=progress_printer,
            expected_duration=cast(float | None, args.expected_duration),
        )
    finally:
        if progress_printer is not None:
            progress_printer.close()
    destination = redact_text(result.encoding.outputs[0])
    integrated = result.measurement.integrated_lufs
    assert integrated is not None
    print(
        f"Measured {integrated:g} LUFS; "
        f"finished in {result.encoding.elapsed:.2f}s: {destination}"
    )
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
        data = asdict(info)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_media_info(info)))
    return 0


def _run_audit(args: argparse.Namespace) -> int:
    source = cast(str, args.source)
    info = probe(
        source,
        ffprobe=cast(str, args.ffprobe),
        timeout=cast(float | None, args.timeout),
    )
    expectation = cast(AuditExpectation, args.expect)
    fail_on = cast(AuditThreshold, args.fail_on)
    constraints = AuditConstraints(
        minimum_duration=cast(float | None, args.min_duration),
        maximum_duration=cast(float | None, args.max_duration),
        width=cast(int | None, args.width),
        height=cast(int | None, args.height),
        video_codec=cast(str | None, args.video_codec),
        audio_codec=cast(str | None, args.audio_codec),
        sample_rate=cast(int | None, args.sample_rate),
        channels=cast(int | None, args.channels),
    )
    try:
        result = audit_media(info, expect=expectation, constraints=constraints)
    except ValueError as error:
        raise GraphError(str(error)) from error
    passed = result.passes(fail_on)
    if cast(bool, args.json):
        data = asdict(result)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        data["source"] = source
        data["passed"] = passed
        data["fail_on"] = fail_on
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(_format_audit(result, source=source, fail_on=fail_on))
    return 0 if passed else 9


def _run_compare(args: argparse.Namespace) -> int:
    result = compare_media(
        cast(str, args.before),
        cast(str, args.after),
        ffprobe=cast(str, args.ffprobe),
        timeout=cast(float | None, args.timeout),
    )
    if cast(bool, args.json):
        data = asdict(result)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_comparison(result)))
    return 0


def _run_loudness(args: argparse.Namespace) -> int:
    result = measure_loudness(
        cast(str, args.source),
        track=cast(int, args.track),
        target_integrated=cast(float, args.target_integrated),
        target_peak=cast(float, args.target_peak),
        target_range=cast(float, args.target_range),
        ffmpeg=cast(str, args.ffmpeg),
        timeout=cast(float | None, args.timeout),
    )
    if cast(bool, args.json):
        data = asdict(result)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_loudness(result)))
    return 0


def _run_silence_detection(args: argparse.Namespace) -> int:
    result = detect_silence(
        cast(str, args.source),
        track=cast(int, args.track),
        noise_db=cast(float, args.noise_db),
        minimum_duration=cast(float, args.minimum_duration),
        ffmpeg=cast(str, args.ffmpeg),
        timeout=cast(float | None, args.timeout),
    )
    if cast(bool, args.json):
        data = asdict(result)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        data["total_silence"] = result.total_silence
        data["longest_silence"] = result.longest_silence
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_silence(result)))
    return 0


def _run_black_detection(args: argparse.Namespace) -> int:
    result = detect_black(
        cast(str, args.source),
        track=cast(int, args.track),
        picture_ratio=cast(float, args.picture_ratio),
        pixel_threshold=cast(float, args.pixel_threshold),
        minimum_duration=cast(float, args.minimum_duration),
        ffmpeg=cast(str, args.ffmpeg),
        timeout=cast(float | None, args.timeout),
    )
    if cast(bool, args.json):
        data = asdict(result)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        data["total_black"] = result.total_black
        data["longest_black"] = result.longest_black
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_black(result)))
    return 0


def _run_scene_detection(args: argparse.Namespace) -> int:
    result = detect_scenes(
        cast(str, args.source),
        track=cast(int, args.track),
        threshold=cast(float, args.threshold),
        ffmpeg=cast(str, args.ffmpeg),
        timeout=cast(float | None, args.timeout),
    )
    if cast(bool, args.json):
        data = asdict(result)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        data["strongest_change"] = (
            None if result.strongest_change is None else asdict(result.strongest_change)
        )
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_scenes(result)))
    return 0


def _run_crop_detection(args: argparse.Namespace) -> int:
    result = detect_crop(
        cast(str, args.source),
        track=cast(int, args.track),
        limit=cast(float, args.limit),
        round_to=cast(int, args.round_to),
        skip_frames=cast(int, args.skip_frames),
        start=cast(float | None, args.start),
        duration=cast(float, args.duration),
        ffmpeg=cast(str, args.ffmpeg),
        timeout=cast(float | None, args.timeout),
    )
    if cast(bool, args.json):
        data = asdict(result)
        data["schema_version"] = _JSON_SCHEMA_VERSION
        data["recommended"] = result.recommended_json()
        data["agreement"] = result.agreement
        print(json.dumps(_redact_json(data), indent=2, sort_keys=True))
    else:
        print(redact_text(_format_crop(result)))
    return 0


def _run_doctor(args: argparse.Namespace) -> int:
    timeout = cast(float, args.timeout)
    ffmpeg = _tool_report(cast(str, args.ffmpeg), timeout, "ffmpeg")
    ffprobe = _tool_report(cast(str, args.ffprobe), timeout, "ffprobe")
    capabilities: dict[str, bool | None] = {}
    ffmpeg_path = ffmpeg.get("path")
    if ffmpeg.get("ok") is True and isinstance(ffmpeg_path, str):
        capabilities = _capability_report(ffmpeg_path, timeout)
    features = _feature_report(capabilities)
    okay = bool(ffmpeg.get("ok")) and bool(ffprobe.get("ok"))
    required_group = cast(str | None, args.require)
    required_state = (
        features.get(required_group) if required_group is not None else None
    )
    required_ready = required_state if required_group is not None else None
    requested_command = cast(str | None, args.required_command)
    command_specification = (
        command_spec(requested_command) if requested_command is not None else None
    )
    required_command = (
        command_specification.name if command_specification is not None else None
    )
    command_requirements = (
        command_specification.requirements if command_specification is not None else ()
    )
    command_ready = (
        _requirements_state(capabilities, command_requirements)
        if command_specification is not None
        else None
    )
    smoke_requested = cast(bool, args.smoke_test)
    smoke_test: dict[str, object] | None = None
    ffprobe_path = ffprobe.get("path")
    if smoke_requested:
        if (
            ffmpeg.get("ok") is True
            and ffprobe.get("ok") is True
            and isinstance(ffmpeg_path, str)
            and isinstance(ffprobe_path, str)
        ):
            smoke_test = _smoke_report(ffmpeg_path, ffprobe_path, timeout)
        else:
            smoke_test = {
                "ok": False,
                "status": "skipped",
                "reason": "FFmpeg and FFprobe must both be ready",
                "video": None,
            }
    report: dict[str, object] = {
        "schema_version": _JSON_SCHEMA_VERSION,
        "ok": okay,
        "flowmpeg_version": __version__,
        "python_version": platform.python_version(),
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "capabilities": capabilities,
        "features": features,
        "required_group": required_group,
        "required_ready": required_ready,
        "required_command": required_command,
        "command_requirements": command_requirements,
        "command_ready": command_ready,
        "smoke_test": smoke_test,
    }
    if cast(bool, args.json):
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_format_doctor(report))
    requirement_ready = required_ready if required_group is not None else command_ready
    has_requirement = required_group is not None or required_command is not None
    smoke_ready = not smoke_requested or (
        smoke_test is not None and smoke_test.get("ok") is True
    )
    return (
        0
        if okay and (not has_requirement or requirement_ready is True) and smoke_ready
        else 3
    )


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
    if install and (ffmpeg_executable != "ffmpeg" or ffprobe_executable != "ffprobe"):
        return _error(
            GraphError("--install cannot be combined with custom tool paths"),
            2,
            "FMG200",
        )

    ffmpeg = _tool_report(ffmpeg_executable, timeout, "ffmpeg")
    ffprobe = _tool_report(ffprobe_executable, timeout, "ffprobe")
    ready = ffmpeg.get("ok") is True and ffprobe.get("ok") is True
    installer = _detect_installer()
    report: dict[str, object] = {
        "schema_version": _JSON_SCHEMA_VERSION,
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
            returncode = _run_installer_command(command, install_timeout)
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
        if returncode != 0:
            return _error(
                FlowmpegError(f"{installer.manager} exited with code {returncode}"),
                8,
                "FMG304",
            )

    ffmpeg = _tool_report(ffmpeg_executable, timeout, "ffmpeg")
    ffprobe = _tool_report(ffprobe_executable, timeout, "ffprobe")
    if ffmpeg.get("ok") is True and ffprobe.get("ok") is True:
        print("FFmpeg and FFprobe are ready.")
        return 0
    print(
        "The installer finished, but this process cannot find both tools. "
        "Open a new terminal and run flowmpeg doctor."
    )
    return 3


def _run_installer_command(command: tuple[str, ...], timeout: float) -> int:
    process = subprocess.Popen(
        command,
        shell=False,
        **popen_group_options(),
    )
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_process_tree(process, min(timeout, 2.0))
        raise


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
    category = cast(str | None, args.category)
    search = cast(str | None, args.search)
    selected_tag = cast(str | None, args.tag)
    examples = [
        example
        for example in _EXAMPLES
        if category is None or example.category == category
    ]
    if selected_tag is not None:
        examples = [example for example in examples if selected_tag in example.tags]
    if search is not None:
        lowered = search.casefold()
        examples = [
            example for example in examples if lowered in example.command.casefold()
        ]
    if not examples:
        return _error(GraphError("no examples matched"), 2, "FMG200")
    if cast(bool, args.json):
        report = {
            "schema_version": _JSON_SCHEMA_VERSION,
            "examples": [asdict(example) for example in examples],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    print("\n".join(example.command for example in examples))
    return 0


def _run_commands(args: argparse.Namespace) -> int:
    selected = cast(str | None, args.category)
    selected_tag = cast(str | None, args.tag)
    specs = [
        spec
        for spec in COMMAND_CATALOG
        if (selected is None or spec.category == selected)
        and (selected_tag is None or selected_tag in spec.tags)
    ]
    if not specs:
        return _error(GraphError("no commands matched"), 2, "FMG200")
    if cast(bool, args.json):
        report = {
            "schema_version": _JSON_SCHEMA_VERSION,
            "commands": [asdict(spec) for spec in specs],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    categories = (
        (selected,)
        if selected is not None
        else tuple(
            category
            for category in CATEGORIES
            if any(spec.category == category for spec in specs)
        )
    )
    for category in categories:
        category_specs = [spec for spec in specs if spec.category == category]
        print(f"{category.upper()} ({len(category_specs)})")
        for spec in category_specs:
            aliases = f" ({', '.join(spec.aliases)})" if spec.aliases else ""
            print(f"  {spec.name}{aliases}: {spec.summary}")
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


def _format_audit(
    result: MediaAudit,
    *,
    source: str,
    fail_on: AuditThreshold,
) -> str:
    summary = result.summary
    status = "pass" if result.passes(fail_on) else "fail"
    lines = [
        f"Media audit: {status}",
        f"Source: {redact_text(source)}",
        f"Expectation: {result.expectation}",
        f"Failure threshold: {fail_on}",
        f"Constraints: {_format_audit_constraints(result.constraints)}",
        f"Container: {summary.container or 'unknown'}",
        f"Duration: {_seconds(summary.duration)}",
        f"Size: {_bytes(summary.size)}",
        (
            "Streams: "
            f"{summary.video_streams} video, "
            f"{summary.audio_streams} audio, "
            f"{summary.subtitle_streams} subtitle"
        ),
    ]
    if summary.video_streams:
        dimensions = _dimensions(summary.width, summary.height)
        frame_rate = (
            "unknown" if summary.frame_rate is None else f"{summary.frame_rate:g} fps"
        )
        codec = summary.video_codec or "unknown codec"
        lines.append(f"Video: {dimensions}, {frame_rate}, {codec}")
    if summary.audio_streams:
        sample_rate = (
            "unknown" if summary.sample_rate is None else f"{summary.sample_rate} Hz"
        )
        channels = (
            "unknown" if summary.channels is None else f"{summary.channels} channel(s)"
        )
        codec = summary.audio_codec or "unknown codec"
        lines.append(f"Audio: {sample_rate}, {channels}, {codec}")
    lines.append("Findings:")
    if result.findings:
        lines.extend(
            f"  [{item.severity.upper()}] {item.code}: {item.message}"
            for item in result.findings
        )
    else:
        lines.append("  none")
    return "\n".join(lines)


def _format_audit_constraints(constraints: AuditConstraints) -> str:
    values: list[str] = []
    if constraints.minimum_duration is not None:
        values.append(f"duration >= {constraints.minimum_duration:g}s")
    if constraints.maximum_duration is not None:
        values.append(f"duration <= {constraints.maximum_duration:g}s")
    if constraints.width is not None:
        values.append(f"width = {constraints.width}")
    if constraints.height is not None:
        values.append(f"height = {constraints.height}")
    if constraints.video_codec is not None:
        values.append(f"video codec = {constraints.video_codec}")
    if constraints.audio_codec is not None:
        values.append(f"audio codec = {constraints.audio_codec}")
    if constraints.sample_rate is not None:
        values.append(f"sample rate = {constraints.sample_rate} Hz")
    if constraints.channels is not None:
        values.append(f"channels = {constraints.channels}")
    return ", ".join(values) if values else "none"


def _format_comparison(result: MediaComparison) -> str:
    before = result.before
    after = result.after
    size_change = "unknown"
    if result.size_delta is not None:
        size_change = _signed_bytes(result.size_delta)
    if result.size_change_percent is not None:
        size_change += f" ({result.size_change_percent:+.1f}%)"
    duration_change = (
        "unknown"
        if result.duration_delta is None
        else f"{result.duration_delta:+g} seconds"
    )
    rows = (
        ("Size", _bytes(before.size), _bytes(after.size), size_change),
        (
            "Duration",
            _seconds(before.duration),
            _seconds(after.duration),
            duration_change,
        ),
        ("Bit rate", _bit_rate(before.bit_rate), _bit_rate(after.bit_rate), ""),
        ("Video codec", before.video_codec or "none", after.video_codec or "none", ""),
        ("Audio codec", before.audio_codec or "none", after.audio_codec or "none", ""),
        (
            "Dimensions",
            _dimensions(before.width, before.height),
            _dimensions(after.width, after.height),
            "",
        ),
        (
            "Frame rate",
            _frame_rate(before.frame_rate),
            _frame_rate(after.frame_rate),
            "",
        ),
        ("Streams", _stream_counts(before), _stream_counts(after), ""),
    )
    lines = [
        f"Before: {before.source}",
        f"After: {after.source}",
        "",
        "Measure | Before | After | Change",
        "---|---:|---:|---:",
    ]
    lines.extend(" | ".join(row) for row in rows)
    return "\n".join(lines)


def _format_loudness(result: LoudnessMeasurement) -> str:
    def metric(value: float | None, unit: str) -> str:
        return "not measured" if value is None else f"{value:g} {unit}"

    return "\n".join(
        (
            f"Source: {result.source}",
            f"Audio track: {result.track}",
            f"Integrated: {metric(result.integrated_lufs, 'LUFS')}",
            f"True peak: {metric(result.true_peak_dbfs, 'dBFS')}",
            f"Loudness range: {metric(result.loudness_range_lu, 'LU')}",
            f"Threshold: {metric(result.threshold_lufs, 'LUFS')}",
            f"Target offset: {metric(result.target_offset_lu, 'LU')}",
            (
                "Target: "
                f"{result.target_integrated_lufs:g} LUFS, "
                f"{result.target_true_peak_dbfs:g} dBFS, "
                f"{result.target_loudness_range_lu:g} LU range"
            ),
        )
    )


def _format_silence(result: SilenceReport) -> str:
    count = len(result.intervals)
    noun = "interval" if count == 1 else "intervals"
    longest = (
        "none" if result.longest_silence is None else f"{result.longest_silence:.3f}s"
    )
    lines = [
        f"Silence report: {count} {noun}",
        f"Source: {result.source}",
        f"Audio track: {result.track}",
        f"Threshold: {result.noise_db:g} dB",
        f"Minimum duration: {result.minimum_duration:g}s",
        f"Total silence: {result.total_silence:.3f}s",
        f"Longest silence: {longest}",
    ]
    if result.intervals:
        lines.extend(("", "Intervals:"))
        lines.extend(
            f"  {index}. {item.start:.3f}s to {item.end:.3f}s ({item.duration:.3f}s)"
            for index, item in enumerate(result.intervals, start=1)
        )
    return "\n".join(lines)


def _format_black(result: BlackReport) -> str:
    count = len(result.intervals)
    noun = "interval" if count == 1 else "intervals"
    longest = "none" if result.longest_black is None else f"{result.longest_black:.3f}s"
    lines = [
        f"Black report: {count} {noun}",
        f"Source: {result.source}",
        f"Video track: {result.track}",
        f"Picture ratio: {result.picture_ratio:g}",
        f"Pixel threshold: {result.pixel_threshold:g}",
        f"Minimum duration: {result.minimum_duration:g}s",
        f"Total black: {result.total_black:.3f}s",
        f"Longest black: {longest}",
    ]
    if result.intervals:
        lines.extend(("", "Intervals:"))
        lines.extend(
            f"  {index}. {item.start:.3f}s to {item.end:.3f}s ({item.duration:.3f}s)"
            for index, item in enumerate(result.intervals, start=1)
        )
    return "\n".join(lines)


def _format_scenes(result: SceneReport) -> str:
    count = len(result.changes)
    noun = "change" if count == 1 else "changes"
    strongest = (
        "none"
        if result.strongest_change is None
        else (
            f"{result.strongest_change.time:.3f}s "
            f"(score {result.strongest_change.score:.3f})"
        )
    )
    lines = [
        f"Scene report: {count} {noun}",
        f"Source: {result.source}",
        f"Video track: {result.track}",
        f"Threshold: {result.threshold:g}",
        f"Strongest change: {strongest}",
    ]
    if result.changes:
        lines.extend(("", "Changes:"))
        lines.extend(
            f"  {index}. {item.time:.3f}s (score {item.score:.3f})"
            for index, item in enumerate(result.changes, start=1)
        )
    return "\n".join(lines)


def _format_crop(result: CropReport) -> str:
    count = len(result.candidates)
    noun = "candidate" if count == 1 else "candidates"
    agreement = "none" if result.agreement is None else f"{result.agreement:.1%}"
    recommended = (
        "none" if result.recommended is None else result.recommended.filter_value
    )
    lines = [
        f"Crop report: {result.sample_count} samples, {count} {noun}",
        f"Source: {result.source}",
        f"Video track: {result.track}",
        f"Scan: {_crop_scan_range(result)}",
        f"Limit: {result.limit:g}",
        f"Round to: {result.round_to}",
        f"Recommended: {recommended}",
        f"Agreement: {agreement}",
    ]
    if result.candidates:
        lines.extend(("", "Candidates:"))
        lines.extend(
            f"  {index}. {item.filter_value} ({item.samples} samples)"
            for index, item in enumerate(result.candidates[:10], start=1)
        )
        remaining = len(result.candidates) - 10
        if remaining > 0:
            lines.append(f"  ... {remaining} more candidates in JSON output")
    return "\n".join(lines)


def _crop_scan_range(result: CropReport) -> str:
    start = 0 if result.start is None else result.start
    if result.duration is None:
        return f"from {start:g}s to the end"
    return f"from {start:g}s for {result.duration:g}s"


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


def _tool_report(
    executable: str,
    timeout: float,
    expected_tool: str | None = None,
) -> dict[str, object]:
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
        reason = _stderr_reason(redact_text(completed.stderr or completed.stdout))
    identity_ok = expected_tool is None or (
        isinstance(first_line, str)
        and first_line.lower().startswith(f"{expected_tool} version ")
    )
    if completed.returncode == 0 and not identity_ok:
        reason = f"Expected {expected_tool} version output"
    okay = completed.returncode == 0 and identity_ok
    return {
        "ok": okay,
        "status": "ready" if okay else "wrong-tool" if not identity_ok else "failed",
        "path": path,
        "version": first_line,
        "returncode": completed.returncode,
        "reason": reason,
    }


def _capability_report(ffmpeg: str, timeout: float) -> dict[str, bool | None]:
    filters = _listing(ffmpeg, "-filters", timeout)
    encoders = _listing(ffmpeg, "-encoders", timeout)
    muxers = _listing(ffmpeg, "-muxers", timeout)
    all_requirements = {
        requirement
        for requirements in _FEATURE_REQUIREMENTS.values()
        for requirement in requirements
    }
    all_requirements.update(
        requirement for spec in COMMAND_CATALOG for requirement in spec.requirements
    )
    listings = {"filter": filters, "encoder": encoders, "muxer": muxers}
    return {
        requirement: _listing_has(
            listings[requirement.partition(":")[0]],
            requirement.partition(":")[2],
        )
        for requirement in sorted(all_requirements)
    }


def _smoke_report(
    ffmpeg: str,
    ffprobe: str,
    timeout: float,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="flowmpeg-doctor-") as directory:
        output = os.path.join(directory, "smoke.mkv")
        try:
            encoded = _run_captured_process(
                (
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=16x16:r=1",
                    "-frames:v",
                    "1",
                    "-c:v",
                    "mpeg4",
                    "-f",
                    "matroska",
                    output,
                ),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "status": "encode-timeout",
                "reason": f"Encode exceeded {timeout:g} seconds",
                "video": None,
            }
        except OSError as error:
            return {
                "ok": False,
                "status": "encode-error",
                "reason": redact_text(str(error))[:400] or None,
                "video": None,
            }
        if encoded.returncode != 0:
            return {
                "ok": False,
                "status": "encode-failed",
                "reason": _stderr_reason(redact_text(encoded.stderr)),
                "video": None,
            }

        try:
            inspected = _run_captured_process(
                (
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,width,height",
                    "-of",
                    "json",
                    output,
                ),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "status": "probe-timeout",
                "reason": f"Probe exceeded {timeout:g} seconds",
                "video": None,
            }
        except OSError as error:
            return {
                "ok": False,
                "status": "probe-error",
                "reason": redact_text(str(error))[:400] or None,
                "video": None,
            }
        if inspected.returncode != 0:
            return {
                "ok": False,
                "status": "probe-failed",
                "reason": _stderr_reason(redact_text(inspected.stderr)),
                "video": None,
            }

        try:
            payload = json.loads(inspected.stdout)
            streams = payload.get("streams")
            video = streams[0] if isinstance(streams, list) and streams else None
        except (json.JSONDecodeError, AttributeError):
            video = None
        expected = {"codec_name": "mpeg4", "width": 16, "height": 16}
        if video != expected:
            return {
                "ok": False,
                "status": "invalid-probe",
                "reason": "FFprobe did not report the expected video stream",
                "video": video,
            }
        return {
            "ok": True,
            "status": "ready",
            "reason": None,
            "video": video,
        }


def _run_captured_process(
    argv: tuple[str, ...],
    *,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        **popen_group_options(),
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_process_tree(process, min(timeout, 2.0))
        raise
    if process.returncode is None:
        raise OSError("Process ended without a return code")
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def _feature_report(
    capabilities: dict[str, bool | None],
) -> dict[str, bool | None]:
    return {
        feature: _requirements_state(capabilities, requirements)
        for feature, requirements in _FEATURE_REQUIREMENTS.items()
    }


def _requirements_state(
    capabilities: dict[str, bool | None],
    requirements: Sequence[str],
) -> bool | None:
    states = [capabilities.get(name) for name in requirements]
    if any(state is False for state in states):
        return False
    if states and all(state is True for state in states):
        return True
    return None


def _listing(executable: str, option: str, timeout: float) -> str | None:
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
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _listing_has(listing: str | None, name: str) -> bool | None:
    if listing is None:
        return None
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
    capabilities = cast(dict[str, bool | None], report["capabilities"])
    if capabilities:
        available = sum(value is True for value in capabilities.values())
        lines.append(f"Capabilities: {available}/{len(capabilities)} available")
        missing = [name for name, present in capabilities.items() if present is False]
        for name in missing:
            lines.append(f"  missing: {name}")
        unknown = [name for name, present in capabilities.items() if present is None]
        for name in unknown:
            lines.append(f"  unknown: {name}")
    features = cast(dict[str, bool | None], report["features"])
    if features:
        lines.append("Feature groups:")
        for name, present in features.items():
            state = "ready" if present is True else "limited"
            if present is None:
                state = "unknown"
            lines.append(f"  {name}: {state}")
    required_group = report.get("required_group")
    if isinstance(required_group, str):
        ready = report.get("required_ready")
        state = "ready" if ready is True else "limited"
        if ready is None:
            state = "unknown"
        lines.append(f"Required group: {required_group} ({state})")
    required_command = report.get("required_command")
    if isinstance(required_command, str):
        ready = report.get("command_ready")
        state = "ready" if ready is True else "limited"
        if ready is None:
            state = "unknown"
        lines.append(f"Required command: {required_command} ({state})")
        requirements = cast(Sequence[str], report["command_requirements"])
        for requirement in requirements:
            present = capabilities.get(requirement)
            requirement_state = "ready" if present is True else "missing"
            if present is None:
                requirement_state = "unknown"
            lines.append(f"  {requirement}: {requirement_state}")
    smoke_test = report.get("smoke_test")
    if isinstance(smoke_test, dict):
        lines.append(f"Smoke test: {smoke_test['status']}")
        video = smoke_test.get("video")
        if isinstance(video, dict):
            lines.append(
                f"  video: {video.get('codec_name')} "
                f"{video.get('width')}x{video.get('height')}"
            )
        if smoke_test.get("reason"):
            lines.append(f"  reason: {smoke_test['reason']}")
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


def _signed_bytes(value: int) -> str:
    prefix = "+" if value >= 0 else "-"
    return prefix + _bytes(abs(value))


def _bit_rate(value: int | None) -> str:
    return "unknown" if value is None else f"{value / 1000:g} kb/s"


def _dimensions(width: int | None, height: int | None) -> str:
    if width is None or height is None:
        return "unknown"
    return f"{width}x{height}"


def _frame_rate(value: float | None) -> str:
    return "unknown" if value is None else f"{value:g} fps"


def _stream_counts(summary: MediaSummary) -> str:
    return (
        f"{summary.video_streams} video, {summary.audio_streams} audio, "
        f"{summary.subtitle_streams} subtitle"
    )


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
    if re.search(
        r"unknown encoder|encoder .* not found|error selecting an encoder", lowered
    ):
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
            line
            for line in lines
            if any(re.search(pattern, line, re.I) for pattern in preferred)
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
