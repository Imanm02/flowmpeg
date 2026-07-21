"""Exceptions raised by Flowmpeg."""


class FlowmpegError(Exception):
    """Base class for Flowmpeg errors."""


class BinaryNotFoundError(FlowmpegError):
    """Raised when FFmpeg or FFprobe cannot be found."""

    def __init__(self, message: str, *, tool: str | None = None) -> None:
        super().__init__(message)
        self.tool = tool


class BinaryUnusableError(FlowmpegError):
    """Raised when FFmpeg or FFprobe exists but cannot be started."""

    def __init__(self, message: str, *, tool: str | None = None) -> None:
        super().__init__(message)
        self.tool = tool


class GraphError(FlowmpegError):
    """Raised when a media graph is invalid."""


class CompilationError(FlowmpegError):
    """Raised when a media graph cannot be compiled."""


class ProbeError(FlowmpegError):
    """Raised when FFprobe cannot inspect an input."""

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None = None,
        stderr: str = "",
        command: str = "",
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr
        self.command = command


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


class JobCancelledError(FlowmpegError):
    """Raised when an FFmpeg process is cancelled."""


class OutputExistsError(FlowmpegError):
    """Raised when an output exists and overwrite is disabled."""
