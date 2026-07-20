"""Video filtering and composition recipes."""

from __future__ import annotations

import math
from typing import Literal, TypeAlias

from flowmpeg.errors import GraphError
from flowmpeg.model import Expression, FilterValue, StreamKind, expr
from flowmpeg.streams import VideoStream, apply_filter

OverlayPosition: TypeAlias = int | Expression
OverlayEofAction = Literal["repeat", "endall", "pass"]


def scale(
    stream: VideoStream,
    *,
    width: int | None = None,
    height: int | None = None,
) -> VideoStream:
    """Scale video while preserving aspect ratio when one side is omitted."""

    if width is None and height is None:
        raise GraphError("Video scale requires width or height")
    if width is not None and width <= 0:
        raise GraphError("Video width must be positive")
    if height is not None and height <= 0:
        raise GraphError("Video height must be positive")
    return stream.filter(
        "scale",
        width if width is not None else -2,
        height if height is not None else -2,
    )


def trim_video(
    stream: VideoStream,
    *,
    start: float | None = None,
    end: float | None = None,
) -> VideoStream:
    """Trim video and reset its timestamps to zero."""

    if start is None and end is None:
        raise GraphError("Video trim requires start or end")
    if start is not None:
        _nonnegative("start", start)
    if end is not None:
        _positive("end", end)
    if start is not None and end is not None and end <= start:
        raise GraphError("Video trim end must be greater than start")

    options: dict[str, FilterValue] = {}
    if start is not None:
        options["start"] = start
    if end is not None:
        options["end"] = end
    trimmed = stream.filter("trim", **options)
    return trimmed.filter("setpts", expr("PTS-STARTPTS"))


def overlay_video(
    background: VideoStream,
    foreground: VideoStream,
    *,
    x: OverlayPosition = 0,
    y: OverlayPosition = 0,
    opacity: float = 1,
    shortest: bool = False,
    eof_action: OverlayEofAction = "repeat",
) -> VideoStream:
    """Place one video stream over another."""

    if not 0 <= opacity <= 1 or not math.isfinite(opacity):
        raise GraphError("Overlay opacity must be between 0 and 1")
    if eof_action not in {"repeat", "endall", "pass"}:
        raise GraphError("Invalid overlay end behavior")

    if opacity < 1:
        foreground = foreground.filter("format", pix_fmts="rgba")
        foreground = foreground.filter("colorchannelmixer", aa=opacity)

    options: dict[str, FilterValue] = {
        "x": x,
        "y": y,
        "shortest": shortest,
        "eof_action": eof_action,
    }
    (result,) = apply_filter(
        (background, foreground),
        "overlay",
        output_kinds=(StreamKind.VIDEO,),
        options=options,
    )
    assert isinstance(result, VideoStream)
    return result


def stack_video(
    *streams: VideoStream,
    columns: int = 2,
    fill: str = "black",
) -> VideoStream:
    """Arrange video streams in a grid with an FFmpeg xstack filter."""

    if len(streams) < 2:
        raise GraphError("Video stacking requires at least two streams")
    if columns <= 0:
        raise GraphError("Video stack columns must be positive")
    if not fill:
        raise GraphError("Video stack fill cannot be empty")

    layout: list[str] = []
    for index in range(len(streams)):
        row, column = divmod(index, columns)
        row_start = row * columns
        x = (
            "0"
            if column == 0
            else "+".join(f"w{item}" for item in range(row_start, index))
        )
        y = "0" if row == 0 else "+".join(f"h{item * columns}" for item in range(row))
        layout.append(f"{x}_{y}")

    options: dict[str, FilterValue] = {
        "inputs": len(streams),
        "layout": "|".join(layout),
        "fill": fill,
    }
    (result,) = apply_filter(
        streams,
        "xstack",
        output_kinds=(StreamKind.VIDEO,),
        options=options,
    )
    assert isinstance(result, VideoStream)
    return result


def named_overlay_position(
    position: str,
    *,
    padding: int = 24,
) -> tuple[OverlayPosition, OverlayPosition]:
    """Convert a named overlay position into FFmpeg coordinates."""

    if padding < 0:
        raise GraphError("Overlay padding cannot be negative")
    positions: dict[str, tuple[OverlayPosition, OverlayPosition]] = {
        "top-left": (padding, padding),
        "top-right": (expr(f"W-w-{padding}"), padding),
        "bottom-left": (padding, expr(f"H-h-{padding}")),
        "bottom-right": (
            expr(f"W-w-{padding}"),
            expr(f"H-h-{padding}"),
        ),
        "center": (expr("(W-w)/2"), expr("(H-h)/2")),
    }
    try:
        return positions[position]
    except KeyError as error:
        raise GraphError(f"Unknown overlay position: {position}") from error


def _finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise GraphError(f"{name} must be finite")


def _positive(name: str, value: float) -> None:
    _finite(name, value)
    if value <= 0:
        raise GraphError(f"{name} must be positive")


def _nonnegative(name: str, value: float) -> None:
    _finite(name, value)
    if value < 0:
        raise GraphError(f"{name} cannot be negative")
