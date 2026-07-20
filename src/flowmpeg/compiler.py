"""Pure FFmpeg command compilation."""

from __future__ import annotations

import heapq
import math
import re
from collections import Counter
from dataclasses import dataclass

from flowmpeg.diagnostics import display_argv
from flowmpeg.errors import CompilationError
from flowmpeg.model import (
    Expression,
    FilterNode,
    FilterValue,
    MediaGraph,
    NodeKey,
    StreamKind,
    StreamRef,
)
from flowmpeg.plan import Plan

_filter_option_name = re.compile(r"^[A-Za-z0-9_]+$")
_kind_letter = {
    StreamKind.VIDEO: "v",
    StreamKind.AUDIO: "a",
    StreamKind.SUBTITLE: "s",
}


@dataclass(frozen=True, slots=True)
class CompiledCommand:
    """The exact argv and filter graph produced for a plan."""

    argv: tuple[str, ...]
    filter_graph: str | None

    def display(self, *, redact: bool = True) -> str:
        """Format the command for the current platform."""

        return display_argv(self.argv, redact=redact)


def compile_plan(plan: Plan, *, ffmpeg: str = "ffmpeg") -> CompiledCommand:
    """Compile a plan without reading files or starting a process."""

    if not ffmpeg:
        raise CompilationError("The FFmpeg executable cannot be empty")

    plan.validate()
    filters = _topological_filters(plan.graph)
    _validate_filter_consumers(plan, filters)
    input_indexes = {node.key: index for index, node in enumerate(plan.graph.inputs)}
    labels = _allocate_labels(filters)
    filter_graph = _compile_filter_graph(filters, input_indexes, labels)

    argv: list[str] = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-y" if plan.overwrite_enabled else "-n",
        *plan.global_args,
    ]
    for node in plan.graph.inputs:
        argv.extend(node.args)
        argv.extend(("-i", node.source))
    if filter_graph:
        argv.extend(("-filter_complex", filter_graph))

    for output_spec in plan.outputs:
        for stream in output_spec.streams:
            argv.extend(("-map", _map_value(stream, input_indexes, labels)))
        argv.extend(output_spec.args)
        argv.append(output_spec.destination)

    return CompiledCommand(tuple(argv), filter_graph)


def serialize_filter_value(value: FilterValue) -> str:
    """Serialize and escape one FFmpeg filter value."""

    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CompilationError("Filter numbers must be finite")
        return str(value)
    if isinstance(value, Expression):
        value = value.value

    escaped: list[str] = []
    for character in value:
        if character in "\\':,;[]":
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


def _topological_filters(graph: MediaGraph) -> tuple[FilterNode, ...]:
    by_key = {node.key: node for node in graph.filters}
    positions = {node.key: index for index, node in enumerate(graph.filters)}
    incoming: dict[NodeKey, int] = {}
    dependents: dict[NodeKey, list[NodeKey]] = {key: [] for key in by_key}

    for node in graph.filters:
        dependencies = {stream.node for stream in node.inputs if stream.node in by_key}
        incoming[node.key] = len(dependencies)
        for dependency in dependencies:
            dependents[dependency].append(node.key)

    ready = [
        (positions[key], key.value, key)
        for key, degree in incoming.items()
        if degree == 0
    ]
    heapq.heapify(ready)
    ordered: list[FilterNode] = []

    while ready:
        _, _, key = heapq.heappop(ready)
        ordered.append(by_key[key])
        for dependent in dependents[key]:
            incoming[dependent] -= 1
            if incoming[dependent] == 0:
                heapq.heappush(
                    ready,
                    (positions[dependent], dependent.value, dependent),
                )

    if len(ordered) != len(graph.filters):
        raise CompilationError("The media graph contains a cycle")
    return tuple(ordered)


def _allocate_labels(filters: tuple[FilterNode, ...]) -> dict[StreamRef, str]:
    counters: Counter[StreamKind] = Counter()
    labels: dict[StreamRef, str] = {}
    for node in filters:
        for pad, kind in enumerate(node.output_kinds):
            labels[StreamRef(node.key, pad, kind)] = (
                f"{_kind_letter[kind]}{counters[kind]}"
            )
            counters[kind] += 1
    return labels


def _compile_filter_graph(
    filters: tuple[FilterNode, ...],
    input_indexes: dict[NodeKey, int],
    labels: dict[StreamRef, str],
) -> str | None:
    if not filters:
        return None

    specs: list[str] = []
    for node in filters:
        inputs = "".join(
            f"[{_filter_input(stream, input_indexes, labels)}]"
            for stream in node.inputs
        )
        values = [serialize_filter_value(value) for value in node.args]
        for option in node.options:
            if not _filter_option_name.fullmatch(option.name):
                raise CompilationError(f"Invalid filter option: {option.name!r}")
            values.append(f"{option.name}={serialize_filter_value(option.value)}")
        filter_text = node.name
        if values:
            filter_text += "=" + ":".join(values)
        outputs = "".join(
            f"[{labels[StreamRef(node.key, pad, kind)]}]"
            for pad, kind in enumerate(node.output_kinds)
        )
        specs.append(f"{inputs}{filter_text}{outputs}")
    return ";".join(specs)


def _filter_input(
    stream: StreamRef,
    input_indexes: dict[NodeKey, int],
    labels: dict[StreamRef, str],
) -> str:
    input_index = input_indexes.get(stream.node)
    if input_index is not None:
        return f"{input_index}:{_kind_letter[stream.kind]}:{stream.pad}"
    try:
        return labels[stream]
    except KeyError as error:
        raise CompilationError("A filter reads an unknown stream") from error


def _map_value(
    stream: StreamRef,
    input_indexes: dict[NodeKey, int],
    labels: dict[StreamRef, str],
) -> str:
    input_index = input_indexes.get(stream.node)
    if input_index is not None:
        suffix = "?" if stream.optional else ""
        return f"{input_index}:{_kind_letter[stream.kind]}:{stream.pad}{suffix}"
    try:
        return f"[{labels[stream]}]"
    except KeyError as error:
        raise CompilationError("An output maps an unknown stream") from error


def _validate_filter_consumers(plan: Plan, filters: tuple[FilterNode, ...]) -> None:
    counts: Counter[StreamRef] = Counter()
    filter_outputs: list[StreamRef] = []
    filter_keys = {node.key for node in filters}

    for node in filters:
        for pad, kind in enumerate(node.output_kinds):
            filter_outputs.append(StreamRef(node.key, pad, kind))
        counts.update(stream for stream in node.inputs if stream.node in filter_keys)
    for output_spec in plan.outputs:
        counts.update(
            stream for stream in output_spec.streams if stream.node in filter_keys
        )

    for stream in filter_outputs:
        uses = counts[stream]
        if uses == 0:
            raise CompilationError("A filter output is not connected")
        if uses > 1:
            raise CompilationError("A filter output requires split or asplit")
