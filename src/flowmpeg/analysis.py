"""Shared process handling for FFmpeg media analysis."""

from __future__ import annotations

import subprocess

from flowmpeg.errors import (
    BinaryNotFoundError,
    BinaryUnusableError,
    JobTimeoutError,
)
from flowmpeg.processes import popen_group_options, stop_process_tree


def run_ffmpeg_analysis(
    argv: tuple[str, ...],
    *,
    timeout: float | None,
    activity: str,
) -> tuple[str, int]:
    """Run one bounded FFmpeg analysis and collect its diagnostic output."""

    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            **popen_group_options(),
        )
    except FileNotFoundError as error:
        raise BinaryNotFoundError(
            f"FFmpeg was not found: {argv[0]}",
            tool="ffmpeg",
        ) from error
    except OSError as error:
        raise BinaryUnusableError(
            f"FFmpeg could not be started: {argv[0]}",
            tool="ffmpeg",
        ) from error
    try:
        _, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        stop_process_tree(process, 2.0)
        raise JobTimeoutError(f"FFmpeg {activity} timed out") from error
    if process.returncode is None:
        raise BinaryUnusableError(
            "FFmpeg ended without a return code",
            tool="ffmpeg",
        )
    return stderr, process.returncode


__all__ = ["run_ffmpeg_analysis"]
