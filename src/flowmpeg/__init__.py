"""Build inspectable FFmpeg media jobs."""

from flowmpeg.errors import (
    BinaryNotFoundError,
    CompilationError,
    ExecutionError,
    FlowmpegError,
    GraphError,
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
    "CompilationError",
    "ExecutionError",
    "Expression",
    "FlowmpegError",
    "FormatInfo",
    "GraphError",
    "MediaGraph",
    "MediaInput",
    "MediaInfo",
    "OutputExistsError",
    "OutputSpec",
    "Plan",
    "ProbeError",
    "Rational",
    "StreamKind",
    "StreamInfo",
    "SubtitleStream",
    "SubtitleStreamInfo",
    "VideoStream",
    "VideoStreamInfo",
    "__version__",
    "apply_filter",
    "expr",
    "input",
    "output",
    "probe",
    "probe_raw",
]
