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
from flowmpeg.model import MediaGraph, StreamKind
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
    "BinaryNotFoundError",
    "CompilationError",
    "ExecutionError",
    "FlowmpegError",
    "GraphError",
    "MediaGraph",
    "MediaInput",
    "OutputExistsError",
    "ProbeError",
    "StreamKind",
    "SubtitleStream",
    "VideoStream",
    "AudioStream",
    "__version__",
    "apply_filter",
    "input",
]
