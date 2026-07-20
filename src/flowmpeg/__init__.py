"""Build inspectable FFmpeg media jobs."""

from flowmpeg import shortcuts
from flowmpeg.audit import (
    AUDIT_CODES,
    AuditFinding,
    AuditSummary,
    MediaAudit,
    audit_media,
)
from flowmpeg.black import BlackInterval, BlackReport, detect_black
from flowmpeg.clip import Clip, concat_clips, media, replace_audio
from flowmpeg.comparison import (
    MediaComparison,
    MediaSummary,
    compare_media,
    compare_media_info,
)
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
from flowmpeg.silence import SilenceInterval, SilenceReport, detect_silence
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
    "AUDIT_CODES",
    "AuditFinding",
    "AuditSummary",
    "BinaryNotFoundError",
    "BinaryUnusableError",
    "BlackInterval",
    "BlackReport",
    "Clip",
    "CompilationError",
    "ExecutionError",
    "Expression",
    "FlowmpegError",
    "FormatInfo",
    "GraphError",
    "JobTimeoutError",
    "LoudnessMeasurement",
    "MediaGraph",
    "MediaInput",
    "MediaInfo",
    "MediaAudit",
    "MediaComparison",
    "MediaSummary",
    "OutputExistsError",
    "OutputSpec",
    "Plan",
    "ProbeError",
    "Progress",
    "Rational",
    "RunResult",
    "SilenceInterval",
    "SilenceReport",
    "StreamKind",
    "StreamInfo",
    "SubtitleStream",
    "SubtitleStreamInfo",
    "VideoStream",
    "VideoStreamInfo",
    "__version__",
    "apply_filter",
    "audit_media",
    "change_audio_speed",
    "change_video_speed",
    "compare_media",
    "compare_media_info",
    "concat_clips",
    "crop_video",
    "delay_audio",
    "detect_black",
    "detect_silence",
    "duck_audio",
    "expr",
    "fade_audio",
    "input",
    "media",
    "measure_loudness",
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
