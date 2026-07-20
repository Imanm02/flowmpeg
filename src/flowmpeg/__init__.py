"""Build inspectable FFmpeg media jobs."""

from flowmpeg import shortcuts
from flowmpeg.clip import Clip, concat_clips, media, replace_audio
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
from flowmpeg.model import Expression, MediaGraph, StreamKind, expr
from flowmpeg.plan import OutputSpec, Plan, output
from flowmpeg.probe import (
    AudioStreamInfo,
    FormatInfo,
    MediaInfo,
    Rational,
    StreamInfo,
    SubtitleStreamInfo,
    VideoStreamInfo,
    probe,
    probe_raw,
)
from flowmpeg.progress import Progress
from flowmpeg.recipes.audio import (
    change_audio_speed,
    delay_audio,
    duck_audio,
    fade_audio,
    mix_audio,
    normalize_loudness,
    trim_audio,
    volume,
)
from flowmpeg.recipes.video import (
    change_video_speed,
    crop_video,
    overlay_video,
    rotate_video,
    scale,
    stack_video,
    trim_video,
)
from flowmpeg.runner import RunResult, run
from flowmpeg.streams import (
    AudioStream,
    MediaInput,
    SubtitleStream,
    VideoStream,
    apply_filter,
    input,
)

__version__ = "0.1.0"

__all__ = [
    "AudioStream",
    "AudioStreamInfo",
    "BinaryNotFoundError",
    "BinaryUnusableError",
    "Clip",
    "CompilationError",
    "ExecutionError",
    "Expression",
    "FlowmpegError",
    "FormatInfo",
    "GraphError",
    "JobTimeoutError",
    "MediaGraph",
    "MediaInput",
    "MediaInfo",
    "OutputExistsError",
    "OutputSpec",
    "Plan",
    "ProbeError",
    "Progress",
    "Rational",
    "RunResult",
    "StreamKind",
    "StreamInfo",
    "SubtitleStream",
    "SubtitleStreamInfo",
    "VideoStream",
    "VideoStreamInfo",
    "__version__",
    "apply_filter",
    "change_audio_speed",
    "change_video_speed",
    "concat_clips",
    "crop_video",
    "delay_audio",
    "duck_audio",
    "expr",
    "fade_audio",
    "input",
    "media",
    "mix_audio",
    "normalize_loudness",
    "overlay_video",
    "output",
    "probe",
    "probe_raw",
    "replace_audio",
    "rotate_video",
    "run",
    "scale",
    "stack_video",
    "shortcuts",
    "trim_audio",
    "trim_video",
    "volume",
]
