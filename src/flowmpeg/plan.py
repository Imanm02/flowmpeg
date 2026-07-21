"""Inspectable media plans and output declarations."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from flowmpeg.diagnostics import redact_text
from flowmpeg.errors import GraphError
from flowmpeg.model import MediaGraph, StreamRef
from flowmpeg.pathing import same_destination
from flowmpeg.streams import Stream

if TYPE_CHECKING:
    from flowmpeg.compiler import CompiledCommand
    from flowmpeg.progress import Progress
    from flowmpeg.runner import RunResult


_STRUCTURAL_ARGS = frozenset(
    {
        "-filter_complex",
        "-filter_complex_script",
        "-i",
        "-lavfi",
        "-map",
        "-n",
        "-nostats",
        "-nostdin",
        "-progress",
        "-stats",
        "-stats_period",
        "-stdin",
        "-y",
    }
)


@dataclass(frozen=True, slots=True)
class OutputSpec:
    """Mapped streams and options for one output destination."""

    destination: str
    streams: tuple[StreamRef, ...]
    args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.destination, str) or not self.destination:
            raise GraphError("Output destinations cannot be empty")
        if self.destination.startswith("-"):
            raise GraphError("Output destinations cannot start with a dash")
        if not isinstance(self.streams, tuple):
            raise GraphError("Output streams must be an immutable tuple")
        if not self.streams:
            raise GraphError("Outputs require at least one stream")
        if not all(isinstance(value, StreamRef) for value in self.streams):
            raise GraphError("Output streams must be stream references")
        if not isinstance(self.args, tuple):
            raise GraphError("Output arguments must be an immutable tuple")
        if not all(isinstance(value, str) for value in self.args):
            raise GraphError("Output arguments must be strings")


@dataclass(frozen=True, slots=True)
class Plan:
    """A media graph and the FFmpeg outputs it should produce."""

    graph: MediaGraph
    outputs: tuple[OutputSpec, ...]
    global_args: tuple[str, ...] = ()
    overwrite_enabled: bool = False
    audio_probe_sources: tuple[str, ...] = ()
    missing_audio_fallback: Plan | None = None

    def __post_init__(self) -> None:
        self.validate()

    def overwrite(self, enabled: bool = True) -> Plan:
        """Return a plan with explicit output replacement behavior."""

        fallback = self.missing_audio_fallback
        if fallback is not None:
            fallback = fallback.overwrite(enabled)
        return replace(
            self,
            overwrite_enabled=enabled,
            missing_audio_fallback=fallback,
        )

    def with_global_args(self, *args: str) -> Plan:
        """Append ordered raw global arguments."""

        fallback = self.missing_audio_fallback
        if fallback is not None:
            fallback = fallback.with_global_args(*args)
        return replace(
            self,
            global_args=(*self.global_args, *_ordered_args(args)),
            missing_audio_fallback=fallback,
        )

    def with_missing_audio_fallback(
        self,
        fallback: Plan,
        *sources: str | os.PathLike[str],
    ) -> Plan:
        """Select a video-only plan at run time when source audio is absent."""

        if not sources:
            raise GraphError("Audio fallback plans require probe sources")
        values = tuple(os.fspath(source) for source in sources)
        return replace(
            self,
            audio_probe_sources=values,
            missing_audio_fallback=fallback,
        )

    def add_output(
        self,
        *streams: Stream,
        to: str | os.PathLike[str],
        args: Iterable[str] = (),
    ) -> Plan:
        """Return a plan with another output destination."""

        if self.missing_audio_fallback is not None:
            raise GraphError("Add outputs before attaching an audio fallback")
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
            self.audio_probe_sources,
            self.missing_audio_fallback,
        )

    def validate(self) -> None:
        """Check graph links and output declarations without running FFmpeg."""

        if not isinstance(self.graph, MediaGraph):
            raise GraphError("Plans require a media graph")
        if not isinstance(self.outputs, tuple):
            raise GraphError("Plan outputs must be an immutable tuple")
        if not all(isinstance(value, OutputSpec) for value in self.outputs):
            raise GraphError("Plan outputs must be output specifications")
        if not isinstance(self.global_args, tuple):
            raise GraphError("Global arguments must be an immutable tuple")
        if not all(isinstance(value, str) for value in self.global_args):
            raise GraphError("Global arguments must be strings")
        if not isinstance(self.overwrite_enabled, bool):
            raise GraphError("Overwrite state must be Boolean")
        if not isinstance(self.audio_probe_sources, tuple) or not all(
            isinstance(value, str) and value for value in self.audio_probe_sources
        ):
            raise GraphError("Audio probe sources must be nonempty strings")
        if (self.missing_audio_fallback is None) != (not self.audio_probe_sources):
            raise GraphError(
                "Audio fallbacks require probe sources and a fallback plan"
            )
        if self.missing_audio_fallback is not None:
            fallback = self.missing_audio_fallback
            if fallback.missing_audio_fallback is not None:
                raise GraphError("Audio fallback plans cannot be nested")
            if fallback.overwrite_enabled != self.overwrite_enabled:
                raise GraphError("Audio fallback overwrite state must match")
            if tuple(item.destination for item in fallback.outputs) != tuple(
                item.destination for item in self.outputs
            ):
                raise GraphError("Audio fallback destinations must match")
        self.graph.validate()
        _reject_structural_args(self.global_args, "Global")
        for node in self.graph.inputs:
            _reject_structural_args(node.args, "Input")
        if not self.outputs:
            raise GraphError("Plans require at least one output")

        for output_spec in self.outputs:
            _reject_structural_args(output_spec.args, "Output")

        destinations = [output.destination for output in self.outputs]
        if _contains_alias(destinations):
            raise GraphError("Output destinations must be unique")

        if any(
            same_destination(node.source, destination)
            for node in self.graph.inputs
            for destination in destinations
        ):
            raise GraphError("An output destination cannot replace a plan input")

        input_keys = {node.key for node in self.graph.inputs}
        filter_by_key = {node.key: node for node in self.graph.filters}
        for output_spec in self.outputs:
            for stream in output_spec.streams:
                if stream.node in input_keys:
                    continue
                if stream.optional:
                    raise GraphError("Only direct input mappings can be optional")
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
            f"  {index}: {redact_text(node.source)}"
            for index, node in enumerate(self.graph.inputs)
        )
        lines.append("Filters:")
        if self.graph.filters:
            lines.extend(f"  {node.name}" for node in self.graph.filters)
        else:
            lines.append("  none")
        lines.append("Outputs:")
        lines.extend(
            f"  {redact_text(output.destination)}: "
            f"{len(output.streams)} mapped stream(s)"
            for output in self.outputs
        )
        lines.append(f"Overwrite: {'yes' if self.overwrite_enabled else 'no'}")
        if self.missing_audio_fallback is not None:
            lines.append("Audio selection: probe sources when the plan runs")
            lines.append("Missing audio: use the video-only fallback")
        return "\n".join(lines)

    def run(
        self,
        *,
        ffmpeg: str = "ffmpeg",
        cwd: str | os.PathLike[str] | None = None,
        ffprobe: str = "ffprobe",
        probe_timeout: float | None = 10.0,
        on_progress: Callable[[Progress], None] | None = None,
        expected_duration: float | None = None,
        timeout: float | None = None,
        progress_interval: float = 0.5,
        stderr_limit: int = 128_000,
        termination_grace: float = 2.0,
    ) -> RunResult:
        """Run this plan with the synchronous process runner."""

        from flowmpeg.runner import run

        selected = self
        if self.missing_audio_fallback is not None:
            from flowmpeg.probe import probe

            has_audio = all(
                probe(source, ffprobe=ffprobe, timeout=probe_timeout).audio_streams
                for source in self.audio_probe_sources
            )
            selected = (
                replace(
                    self,
                    audio_probe_sources=(),
                    missing_audio_fallback=None,
                )
                if has_audio
                else self.missing_audio_fallback
            )
        return run(
            selected,
            ffmpeg=ffmpeg,
            cwd=cwd,
            on_progress=on_progress,
            expected_duration=expected_duration,
            timeout=timeout,
            progress_interval=progress_interval,
            stderr_limit=stderr_limit,
            termination_grace=termination_grace,
        )


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


def _contains_alias(destinations: list[str]) -> bool:
    return any(
        same_destination(destination, other)
        for index, destination in enumerate(destinations)
        for other in destinations[index + 1 :]
    )


def _reject_structural_args(args: tuple[str, ...], scope: str) -> None:
    for value in args:
        option = value.partition("=")[0]
        if option in _STRUCTURAL_ARGS:
            raise GraphError(f"{scope} arguments cannot set {option}")
