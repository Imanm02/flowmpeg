"""Inspectable media plans and output declarations."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from flowmpeg.errors import GraphError
from flowmpeg.model import MediaGraph, StreamRef
from flowmpeg.streams import Stream

if TYPE_CHECKING:
    from flowmpeg.compiler import CompiledCommand


@dataclass(frozen=True, slots=True)
class OutputSpec:
    """Mapped streams and options for one output destination."""

    destination: str
    streams: tuple[StreamRef, ...]
    args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.destination:
            raise GraphError("Output destinations cannot be empty")
        if self.destination.startswith("-"):
            raise GraphError("Output destinations cannot start with a dash")
        if not self.streams:
            raise GraphError("Outputs require at least one stream")
        if not all(isinstance(value, str) for value in self.args):
            raise GraphError("Output arguments must be strings")


@dataclass(frozen=True, slots=True)
class Plan:
    """A media graph and the FFmpeg outputs it should produce."""

    graph: MediaGraph
    outputs: tuple[OutputSpec, ...]
    global_args: tuple[str, ...] = ()
    overwrite_enabled: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def overwrite(self, enabled: bool = True) -> Plan:
        """Return a plan with explicit output replacement behavior."""

        return replace(self, overwrite_enabled=enabled)

    def with_global_args(self, *args: str) -> Plan:
        """Append ordered raw global arguments."""

        return replace(self, global_args=(*self.global_args, *_ordered_args(args)))

    def add_output(
        self,
        *streams: Stream,
        to: str | os.PathLike[str],
        args: Iterable[str] = (),
    ) -> Plan:
        """Return a plan with another output destination."""

        if not streams:
            raise GraphError("Outputs require at least one stream")
        graph = MediaGraph.merge((self.graph, *(stream.graph for stream in streams)))
        spec = OutputSpec(
            os.fspath(to),
            tuple(stream.ref for stream in streams),
            _ordered_args(args),
        )
        return Plan(
            graph,
            (*self.outputs, spec),
            self.global_args,
            self.overwrite_enabled,
        )

    def validate(self) -> None:
        """Check graph links and output declarations without running FFmpeg."""

        self.graph.validate()
        if not self.outputs:
            raise GraphError("Plans require at least one output")

        destinations = [output.destination for output in self.outputs]
        if len(destinations) != len(set(destinations)):
            raise GraphError("Output destinations must be unique")

        input_keys = {node.key for node in self.graph.inputs}
        filter_by_key = {node.key: node for node in self.graph.filters}
        for output_spec in self.outputs:
            for stream in output_spec.streams:
                if stream.node in input_keys:
                    continue
                filter_node = filter_by_key.get(stream.node)
                if filter_node is None:
                    raise GraphError("An output maps an unknown stream")
                if stream.pad >= len(filter_node.output_kinds):
                    raise GraphError("An output maps a missing filter pad")
                if filter_node.output_kinds[stream.pad] is not stream.kind:
                    raise GraphError("An output maps a mismatched stream kind")

    def compile(self, ffmpeg: str = "ffmpeg") -> CompiledCommand:
        """Compile this plan into an immutable command value."""

        from flowmpeg.compiler import compile_plan

        return compile_plan(self, ffmpeg=ffmpeg)

    def raw_argv(self, ffmpeg: str = "ffmpeg") -> tuple[str, ...]:
        """Return the exact command tokens, including possible secrets."""

        return self.compile(ffmpeg).argv

    def command(self, ffmpeg: str = "ffmpeg") -> str:
        """Return a platform command line with credentials hidden."""

        return self.compile(ffmpeg).display()

    def filter_graph(self) -> str | None:
        """Return the compiled complex filter graph, if present."""

        return self.compile().filter_graph

    def explain(self) -> str:
        """Describe inputs, filters, mappings, and outputs."""

        lines = ["Inputs:"]
        lines.extend(
            f"  {index}: {node.source}" for index, node in enumerate(self.graph.inputs)
        )
        lines.append("Filters:")
        if self.graph.filters:
            lines.extend(f"  {node.name}" for node in self.graph.filters)
        else:
            lines.append("  none")
        lines.append("Outputs:")
        lines.extend(
            f"  {output.destination}: {len(output.streams)} mapped stream(s)"
            for output in self.outputs
        )
        lines.append(f"Overwrite: {'yes' if self.overwrite_enabled else 'no'}")
        return "\n".join(lines)


def output(
    *streams: Stream,
    to: str | os.PathLike[str],
    args: Iterable[str] = (),
    global_args: Iterable[str] = (),
) -> Plan:
    """Create a single-output plan without running FFmpeg."""

    if not streams:
        raise GraphError("Outputs require at least one stream")
    graph = MediaGraph.merge(stream.graph for stream in streams)
    spec = OutputSpec(
        os.fspath(to),
        tuple(stream.ref for stream in streams),
        _ordered_args(args),
    )
    return Plan(graph, (spec,), _ordered_args(global_args))


def _ordered_args(args: Iterable[str]) -> tuple[str, ...]:
    if isinstance(args, (set, frozenset)):
        raise GraphError("Raw arguments must have a stable order")
    values = tuple(args)
    if not all(isinstance(value, str) for value in values):
        raise GraphError("Raw arguments must be strings")
    return values
