"""Immutable values used to describe media graphs."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from itertools import count
from typing import TypeAlias

from flowmpeg.errors import GraphError


@dataclass(frozen=True, slots=True)
class Expression:
    """An FFmpeg expression supplied as a filter value."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise GraphError("Expressions cannot be empty")


FilterValue: TypeAlias = str | int | float | bool | Expression

_node_ids = count()


class StreamKind(str, Enum):
    """Kinds of streams that can move through a media graph."""

    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"


@dataclass(frozen=True, slots=True)
class NodeKey:
    """Identity for one node inside a media graph."""

    value: int


def new_node_key() -> NodeKey:
    """Return an identity that is unique for this Python process."""

    return NodeKey(next(_node_ids))


@dataclass(frozen=True, slots=True)
class StreamRef:
    """A reference to one output pad or input stream."""

    node: NodeKey
    pad: int
    kind: StreamKind

    def __post_init__(self) -> None:
        if self.pad < 0:
            raise GraphError("Stream indexes cannot be negative")


@dataclass(frozen=True, slots=True)
class FilterOption:
    """One named FFmpeg filter option."""

    name: str
    value: FilterValue

    def __post_init__(self) -> None:
        if not self.name:
            raise GraphError("Filter option names cannot be empty")


@dataclass(frozen=True, slots=True)
class InputNode:
    """A file, URL, device, or FFmpeg source."""

    key: NodeKey
    source: str
    args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source:
            raise GraphError("Input sources cannot be empty")
        if not all(isinstance(value, str) for value in self.args):
            raise GraphError("Input arguments must be strings")


@dataclass(frozen=True, slots=True)
class FilterNode:
    """A filter and its connected stream pads."""

    key: NodeKey
    name: str
    inputs: tuple[StreamRef, ...]
    output_kinds: tuple[StreamKind, ...]
    args: tuple[FilterValue, ...] = ()
    options: tuple[FilterOption, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise GraphError("Filter names cannot be empty")
        if not self.inputs:
            raise GraphError("Filters require at least one input")
        if not self.output_kinds:
            raise GraphError("Filters require at least one output")


@dataclass(frozen=True, slots=True)
class MediaGraph:
    """An immutable collection of connected input and filter nodes."""

    inputs: tuple[InputNode, ...] = ()
    filters: tuple[FilterNode, ...] = ()

    @classmethod
    def merge(cls, graphs: Iterable[MediaGraph]) -> MediaGraph:
        """Combine graphs while preserving their first-seen node order."""

        inputs: dict[NodeKey, InputNode] = {}
        filters: dict[NodeKey, FilterNode] = {}

        for graph in graphs:
            for input_node in graph.inputs:
                previous_input = inputs.setdefault(input_node.key, input_node)
                if previous_input != input_node:
                    raise GraphError("An input key refers to different nodes")
            for filter_node in graph.filters:
                previous_filter = filters.setdefault(filter_node.key, filter_node)
                if previous_filter != filter_node:
                    raise GraphError("A filter key refers to different nodes")

        merged = cls(tuple(inputs.values()), tuple(filters.values()))
        merged.validate()
        return merged

    def with_filter(self, node: FilterNode) -> MediaGraph:
        """Return a graph with one filter appended."""

        graph = MediaGraph(self.inputs, (*self.filters, node))
        graph.validate()
        return graph

    def validate(self) -> None:
        """Raise GraphError when node identities or links are invalid."""

        input_keys = {node.key for node in self.inputs}
        filter_by_key = {node.key: node for node in self.filters}

        if len(input_keys) != len(self.inputs):
            raise GraphError("Input node keys must be unique")
        if len(filter_by_key) != len(self.filters):
            raise GraphError("Filter node keys must be unique")
        if input_keys.intersection(filter_by_key):
            raise GraphError("Input and filter node keys must be distinct")

        known_keys = input_keys.union(filter_by_key)
        dependencies: dict[NodeKey, set[NodeKey]] = {
            key: set() for key in filter_by_key
        }

        for node in self.filters:
            for stream in node.inputs:
                if stream.node not in known_keys:
                    raise GraphError(f"Filter {node.name!r} has an unknown input")
                if stream.node == node.key:
                    raise GraphError(f"Filter {node.name!r} cannot read itself")
                upstream = filter_by_key.get(stream.node)
                if upstream is None:
                    continue
                if stream.pad >= len(upstream.output_kinds):
                    raise GraphError(f"Filter {node.name!r} reads a missing output pad")
                if upstream.output_kinds[stream.pad] is not stream.kind:
                    raise GraphError(
                        f"Filter {node.name!r} reads a mismatched stream kind"
                    )
                dependencies[node.key].add(upstream.key)

        self._validate_acyclic(dependencies)

    @staticmethod
    def _validate_acyclic(dependencies: dict[NodeKey, set[NodeKey]]) -> None:
        incoming = {key: len(value) for key, value in dependencies.items()}
        dependents: dict[NodeKey, list[NodeKey]] = {key: [] for key in dependencies}
        for node, upstream_keys in dependencies.items():
            for upstream in upstream_keys:
                dependents[upstream].append(node)

        ready = deque(key for key, degree in incoming.items() if degree == 0)
        visited = 0
        while ready:
            key = ready.popleft()
            visited += 1
            for dependent in dependents[key]:
                incoming[dependent] -= 1
                if incoming[dependent] == 0:
                    ready.append(dependent)

        if visited != len(dependencies):
            raise GraphError("Media graphs cannot contain cycles")


def expr(value: str) -> Expression:
    """Mark a string as an FFmpeg expression."""

    return Expression(value)
