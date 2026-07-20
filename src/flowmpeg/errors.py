"""Exceptions raised by Flowmpeg."""


class FlowmpegError(Exception):
    """Base class for Flowmpeg errors."""


class BinaryNotFoundError(FlowmpegError):
    """Raised when FFmpeg or FFprobe cannot be found."""


class GraphError(FlowmpegError):
    """Raised when a media graph is invalid."""


class CompilationError(FlowmpegError):
    """Raised when a media graph cannot be compiled."""


class ProbeError(FlowmpegError):
    """Raised when FFprobe cannot inspect an input."""


class ExecutionError(FlowmpegError):
    """Raised when FFmpeg exits with an error."""

    def __init__(
        self,
        message: str,
        *,
        returncode: int,
        stderr: str,
        command: str,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr
        self.command = command


class JobTimeoutError(FlowmpegError):
    """Raised when an FFmpeg process exceeds its timeout."""


class OutputExistsError(FlowmpegError):
    """Raised when an output exists and overwrite is disabled."""
