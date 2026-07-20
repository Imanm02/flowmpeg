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
    "BinaryNotFoundError",
    "CompilationError",
    "ExecutionError",
    "Expression",
    "FlowmpegError",
    "GraphError",
    "MediaGraph",
    "MediaInput",
    "OutputExistsError",
    "OutputSpec",
    "Plan",
    "ProbeError",
    "StreamKind",
    "SubtitleStream",
    "VideoStream",
    "__version__",
    "apply_filter",
    "expr",
    "input",
    "output",
]
