"""Video filtering and composition recipes."""

from __future__ import annotations

import math
from typing import Literal, TypeAlias

from flowmpeg.errors import GraphError
from flowmpeg.model import Expression, FilterValue, StreamKind, expr
from flowmpeg.streams import VideoStream, apply_filter

OverlayPosition: TypeAlias = int | Expression
OverlayEofAction = Literal["repeat", "endall", "pass"]
Rotation = Literal[90, 180, 270]


def scale(
    stream: VideoStream,
    *,
    width: int | None = None,
    height: int | None = None,
) -> VideoStream:
    """Scale video while preserving aspect ratio when one side is omitted."""

    if width is None and height is None:
        raise GraphError("Video scale requires width or height")
    if width is not None:
        _positive_integer("width", width)
    if height is not None:
        _positive_integer("height", height)
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

    _range("opacity", opacity, 0, 1)
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
    shortest: bool = False,
) -> VideoStream:
    """Arrange video streams in a grid with an FFmpeg xstack filter."""

    if len(streams) < 2:
        raise GraphError("Video stacking requires at least two streams")
    _positive_integer("columns", columns)
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
        "shortest": shortest,
    }
    (result,) = apply_filter(
        streams,
        "xstack",
        output_kinds=(StreamKind.VIDEO,),
        options=options,
    )
    assert isinstance(result, VideoStream)
    return result


def crop_video(
    stream: VideoStream,
    *,
    width: int,
    height: int,
    x: int | Expression | None = None,
    y: int | Expression | None = None,
) -> VideoStream:
    """Crop video to fixed dimensions with optional coordinates."""

    _positive_integer("width", width)
    _positive_integer("height", height)
    _nonnegative_position("x", x)
    _nonnegative_position("y", y)
    options: dict[str, FilterValue] = {"w": width, "h": height}
    if x is not None:
        options["x"] = x
    if y is not None:
        options["y"] = y
    return stream.filter("crop", **options)


def rotate_video(stream: VideoStream, degrees: Rotation) -> VideoStream:
    """Rotate displayed video by a clockwise quarter-turn amount."""

    if degrees == 90:
        return stream.filter("transpose", dir="clock")
    if degrees == 180:
        return stream.filter("hflip").filter("vflip")
    if degrees == 270:
        return stream.filter("transpose", dir="cclock")
    raise GraphError("Rotation must be 90, 180, or 270 degrees")


def change_video_speed(stream: VideoStream, factor: float) -> VideoStream:
    """Change video speed and reset its starting timestamp."""

    _positive("factor", factor)
    if factor == 1:
        return stream
    return stream.filter("setpts", expr(f"(PTS-STARTPTS)/{factor}"))


def named_overlay_position(
    position: str,
    *,
    padding: int = 24,
) -> tuple[OverlayPosition, OverlayPosition]:
    """Convert a named overlay position into FFmpeg coordinates."""

    _nonnegative_integer("padding", padding)
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
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphError(f"{name} must be finite")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise GraphError(f"{name} must be finite")


def _positive(name: str, value: float) -> None:
    _finite(name, value)
    if value <= 0:
        raise GraphError(f"{name} must be positive")


def _nonnegative(name: str, value: float) -> None:
    _finite(name, value)
    if value < 0:
        raise GraphError(f"{name} cannot be negative")


def _range(name: str, value: float, minimum: float, maximum: float) -> None:
    _finite(name, value)
    if not minimum <= value <= maximum:
        raise GraphError(f"{name} must be between {minimum:g} and {maximum:g}")


def _positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GraphError(f"{name} must be a positive integer")


def _nonnegative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphError(f"{name} must be a nonnegative integer")


def _nonnegative_position(name: str, value: int | Expression | None) -> None:
    if value is None or isinstance(value, Expression):
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphError(f"{name} must be a nonnegative integer or expression")
