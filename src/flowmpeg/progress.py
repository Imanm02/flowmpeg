"""Parsing for FFmpeg's machine-readable progress protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class Progress:
    """One complete progress record emitted by FFmpeg."""

    frame: int | None
    fps: float | None
    output_time: timedelta | None
    total_size: int | None
    speed: float | None
    percent: float | None
    state: str
    raw: tuple[tuple[str, str], ...]


class ProgressParser:
    """Collect protocol lines until FFmpeg completes a record."""

    def __init__(self, expected_duration: float | None = None) -> None:
        self._expected_duration = expected_duration
        self._values: dict[str, str] = {}

    def feed_line(self, line: str) -> Progress | None:
        """Consume one line and return a completed progress record."""

        text = line.strip()
        if not text or "=" not in text:
            return None
        key, value = text.split("=", 1)
        self._values[key] = value
        if key != "progress":
            return None

        values = self._values
        self._values = {}
        return _build_progress(values, self._expected_duration)


def _build_progress(
    values: dict[str, str], expected_duration: float | None
) -> Progress:
    output_time = _output_time(values)
    percent = None
    if (
        output_time is not None
        and expected_duration is not None
        and expected_duration > 0
    ):
        percent = min(
            100.0,
            max(0.0, output_time.total_seconds() / expected_duration * 100),
        )

    return Progress(
        frame=_integer(values.get("frame")),
        fps=_number(values.get("fps")),
        output_time=output_time,
        total_size=_integer(values.get("total_size")),
        speed=_speed(values.get("speed")),
        percent=percent,
        state=values["progress"],
        raw=tuple(values.items()),
    )


def _output_time(values: dict[str, str]) -> timedelta | None:
    microseconds = _integer(values.get("out_time_us"))
    if microseconds is not None:
        return timedelta(microseconds=microseconds)

    text = values.get("out_time")
    if text is None:
        return None
    pieces = text.split(":")
    if len(pieces) != 3:
        return None
    try:
        hours = int(pieces[0])
        minutes = int(pieces[1])
        seconds = float(pieces[2])
    except ValueError:
        return None
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _integer(value: str | None) -> int | None:
    if value is None or value == "N/A":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _number(value: str | None) -> float | None:
    if value is None or value == "N/A":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _speed(value: str | None) -> float | None:
    if value is None:
        return None
    return _number(value.removesuffix("x"))
