"""Public input and stream objects."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeVar, cast

from flowmpeg.errors import GraphError
from flowmpeg.model import (
    FilterNode,
    FilterOption,
    FilterValue,
    InputNode,
    MediaGraph,
    NodeKey,
    StreamKind,
    StreamRef,
    new_node_key,
)

_filter_name = re.compile(r"^[A-Za-z0-9_]+(?:@[A-Za-z0-9_.-]+)?$")


@dataclass(frozen=True, slots=True)
class Stream:
    """One typed connection in a media graph."""

    graph: MediaGraph
    ref: StreamRef

    def filter(
        self: StreamType,
        name: str,
        *args: FilterValue,
        **options: FilterValue,
    ) -> StreamType:
        """Connect this stream to a single-output filter."""

        output = apply_filter(
            (self,),
            name,
            output_kinds=(self.ref.kind,),
            args=args,
            options=options,
        )[0]
        return cast(StreamType, output)

    def split(self: StreamType, count: int = 2) -> tuple[StreamType, ...]:
        """Split this stream into independently consumable outputs."""

        if count < 2:
            raise GraphError("A split requires at least two outputs")
        if self.ref.kind is StreamKind.VIDEO:
            name = "split"
        elif self.ref.kind is StreamKind.AUDIO:
            name = "asplit"
        else:
            raise GraphError("Subtitle streams cannot be split")
        outputs = apply_filter(
            (self,),
            name,
            output_kinds=(self.ref.kind,) * count,
            options={"outputs": count},
        )
        return cast(tuple[StreamType, ...], outputs)


@dataclass(frozen=True, slots=True)
class VideoStream(Stream):
    """A video stream connection."""

    def __post_init__(self) -> None:
        if self.ref.kind is not StreamKind.VIDEO:
            raise GraphError("VideoStream requires a video reference")


@dataclass(frozen=True, slots=True)
class AudioStream(Stream):
    """An audio stream connection."""

    def __post_init__(self) -> None:
        if self.ref.kind is not StreamKind.AUDIO:
            raise GraphError("AudioStream requires an audio reference")


@dataclass(frozen=True, slots=True)
class SubtitleStream(Stream):
    """A subtitle stream connection."""

    def __post_init__(self) -> None:
        if self.ref.kind is not StreamKind.SUBTITLE:
            raise GraphError("SubtitleStream requires a subtitle reference")


StreamType = TypeVar("StreamType", bound=Stream)


@dataclass(frozen=True, slots=True)
class MediaInput:
    """An input node with typed stream selectors."""

    graph: MediaGraph
    key: NodeKey

    def video(self, index: int = 0) -> VideoStream:
        """Select a video stream by its video-only index."""

        return VideoStream(
            self.graph,
            StreamRef(self.key, index, StreamKind.VIDEO),
        )

    def audio(self, index: int = 0, *, optional: bool = False) -> AudioStream:
        """Select an audio stream by its audio-only index."""

        return AudioStream(
            self.graph,
            StreamRef(self.key, index, StreamKind.AUDIO, optional),
        )

    def subtitle(self, index: int = 0) -> SubtitleStream:
        """Select a subtitle stream by its subtitle-only index."""

        return SubtitleStream(
            self.graph,
            StreamRef(self.key, index, StreamKind.SUBTITLE),
        )


def input(source: str | os.PathLike[str], *args: str) -> MediaInput:
    """Create an input node without reading the source."""

    key = new_node_key()
    node = InputNode(key, os.fspath(source), tuple(args))
    return MediaInput(MediaGraph(inputs=(node,)), key)


def apply_filter(
    streams: Sequence[Stream],
    name: str,
    *,
    output_kinds: Sequence[StreamKind],
    args: Iterable[FilterValue] = (),
    options: Mapping[str, FilterValue] | Iterable[tuple[str, FilterValue]] = (),
) -> tuple[Stream, ...]:
    """Connect one or more streams to an FFmpeg filter node."""

    if not streams:
        raise GraphError("A filter requires at least one stream")
    if any(stream.ref.optional for stream in streams):
        raise GraphError("Optional input streams cannot feed filters")
    if not _filter_name.fullmatch(name):
        raise GraphError(f"Invalid filter name: {name!r}")

    kinds = tuple(output_kinds)
    if not kinds:
        raise GraphError("A filter requires at least one output kind")

    graph = MediaGraph.merge(stream.graph for stream in streams)
    key = new_node_key()
    if isinstance(options, (set, frozenset)):
        raise GraphError("Filter options must have a stable order")
    option_items = tuple(options.items() if isinstance(options, Mapping) else options)
    option_names = [name for name, _ in option_items]
    if len(option_names) != len(set(option_names)):
        raise GraphError("Filter option names must be unique")
    node = FilterNode(
        key=key,
        name=name,
        inputs=tuple(stream.ref for stream in streams),
        output_kinds=kinds,
        args=tuple(args),
        options=tuple(FilterOption(option, value) for option, value in option_items),
    )
    graph = graph.with_filter(node)

    return tuple(
        _make_stream(graph, StreamRef(key, pad, kind)) for pad, kind in enumerate(kinds)
    )


def _make_stream(graph: MediaGraph, ref: StreamRef) -> Stream:
    if ref.kind is StreamKind.VIDEO:
        return VideoStream(graph, ref)
    if ref.kind is StreamKind.AUDIO:
        return AudioStream(graph, ref)
    return SubtitleStream(graph, ref)
