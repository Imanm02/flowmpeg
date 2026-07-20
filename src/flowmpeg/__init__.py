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

__version__ = "0.1.0"

__all__ = [
    "BinaryNotFoundError",
    "CompilationError",
    "ExecutionError",
    "FlowmpegError",
    "GraphError",
    "OutputExistsError",
    "ProbeError",
    "__version__",
]
