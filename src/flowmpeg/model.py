"""Immutable values used to describe media graphs."""

from __future__ import annotations

import re
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
        if not isinstance(self.value, str) or not self.value:
            raise GraphError("Expressions must be nonempty text")


FilterValue: TypeAlias = str | int | float | bool | Expression

_node_ids = count()
_filter_name = re.compile(r"^[A-Za-z0-9_]+(?:@[A-Za-z0-9_.-]+)?$")


class StreamKind(str, Enum):
    """Kinds of streams that can move through a media graph."""

    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"


@dataclass(frozen=True, slots=True)
class NodeKey:
    """Identity for one node inside a media graph."""

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise GraphError("Node keys must be integers")
        if self.value < 0:
            raise GraphError("Node keys cannot be negative")


def new_node_key() -> NodeKey:
    """Return an identity that is unique for this Python process."""

    return NodeKey(next(_node_ids))


@dataclass(frozen=True, slots=True)
class StreamRef:
    """A reference to one output pad or input stream."""

    node: NodeKey
    pad: int
    kind: StreamKind
    optional: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.node, NodeKey):
            raise GraphError("Stream references require a node key")
        if isinstance(self.pad, bool) or not isinstance(self.pad, int):
            raise GraphError("Stream indexes must be integers")
        if self.pad < 0:
            raise GraphError("Stream indexes cannot be negative")
        if not isinstance(self.kind, StreamKind):
            raise GraphError("Stream references require a known stream kind")
        if not isinstance(self.optional, bool):
            raise GraphError("Optional stream state must be Boolean")


@dataclass(frozen=True, slots=True)
class FilterOption:
    """One named FFmpeg filter option."""

    name: str
    value: FilterValue

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise GraphError("Filter option names cannot be empty")
        if not _is_filter_value(self.value):
            raise GraphError("Filter option values have an unsupported type")


@dataclass(frozen=True, slots=True)
class InputNode:
    """A file, URL, device, or FFmpeg source."""

    key: NodeKey
    source: str
    args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.key, NodeKey):
            raise GraphError("Inputs require a node key")
        if not isinstance(self.source, str) or not self.source:
            raise GraphError("Input sources cannot be empty")
        if not isinstance(self.args, tuple):
            raise GraphError("Input arguments must be an immutable tuple")
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
        if not isinstance(self.key, NodeKey):
            raise GraphError("Filters require a node key")
        validate_filter_name(self.name)
        if not isinstance(self.inputs, tuple):
            raise GraphError("Filter inputs must be an immutable tuple")
        if not self.inputs:
            raise GraphError("Filters require at least one input")
        if not all(isinstance(value, StreamRef) for value in self.inputs):
            raise GraphError("Filter inputs must be stream references")
        if any(value.optional for value in self.inputs):
            raise GraphError("Optional input streams cannot feed filters")
        if not isinstance(self.output_kinds, tuple):
            raise GraphError("Filter outputs must be an immutable tuple")
        if not self.output_kinds:
            raise GraphError("Filters require at least one output")
        if not all(isinstance(value, StreamKind) for value in self.output_kinds):
            raise GraphError("Filters require known output kinds")
        if not isinstance(self.args, tuple):
            raise GraphError("Filter arguments must be an immutable tuple")
        if not all(_is_filter_value(value) for value in self.args):
            raise GraphError("Filter arguments have an unsupported type")
        if not isinstance(self.options, tuple):
            raise GraphError("Filter options must be an immutable tuple")
        if not all(isinstance(value, FilterOption) for value in self.options):
            raise GraphError("Filter options must be named values")
        names = [option.name for option in self.options]
        if len(names) != len(set(names)):
            raise GraphError("Filter option names must be unique")


@dataclass(frozen=True, slots=True)
class MediaGraph:
    """An immutable collection of connected input and filter nodes."""

    inputs: tuple[InputNode, ...] = ()
    filters: tuple[FilterNode, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.inputs, tuple):
            raise GraphError("Graph inputs must be an immutable tuple")
        if not isinstance(self.filters, tuple):
            raise GraphError("Graph filters must be an immutable tuple")

    @classmethod
    def merge(cls, graphs: Iterable[MediaGraph]) -> MediaGraph:
        """Combine graphs while preserving their first-seen node order."""

        inputs: dict[NodeKey, InputNode] = {}
        filters: dict[NodeKey, FilterNode] = {}

        for graph in graphs:
            if not isinstance(graph, MediaGraph):
                raise GraphError("Graph merges require media graphs")
            graph.validate()
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

        if not all(isinstance(node, InputNode) for node in self.inputs):
            raise GraphError("Graph inputs must be input nodes")
        if not all(isinstance(node, FilterNode) for node in self.filters):
            raise GraphError("Graph filters must be filter nodes")

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


def _is_filter_value(value: object) -> bool:
    return isinstance(value, (str, int, float, bool, Expression))


def validate_filter_name(value: object) -> None:
    """Reject names that can alter FFmpeg filter graph structure."""

    if not isinstance(value, str) or not _filter_name.fullmatch(value):
        raise GraphError(f"Invalid filter name: {value!r}")


def expr(value: str) -> Expression:
    """Mark a string as an FFmpeg expression."""

    return Expression(value)
