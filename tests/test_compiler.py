import pytest

from flowmpeg import (
    CompilationError,
    GraphError,
    StreamKind,
    apply_filter,
    input,
    output,
)
from flowmpeg.compiler import serialize_filter_value
from flowmpeg.model import FilterValue, expr


def test_direct_streams_compile_with_scoped_arguments() -> None:
    source = input("input file.mp4", "-ss", "2")
    plan = output(
        source.video(),
        source.audio(),
        to="output.mp4",
        args=("-c:v", "libx264"),
        global_args=("-loglevel", "warning"),
    )

    assert plan.raw_argv() == (
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-n",
        "-loglevel",
        "warning",
        "-ss",
        "2",
        "-i",
        "input file.mp4",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "libx264",
        "output.mp4",
    )


def test_filter_graph_uses_deterministic_typed_labels() -> None:
    video = input("movie.mp4").video().filter("scale", 1280, -2)
    plan = output(video, to="scaled.mp4")

    assert plan.filter_graph() == "[0:v:0]scale=1280:-2[v0]"
    assert plan.raw_argv()[-3:] == ("-map", "[v0]", "scaled.mp4")


def test_multi_input_filter_compiles_in_stream_order() -> None:
    background = input("movie.mp4").video()
    foreground = input("logo.png").video()
    options: dict[str, FilterValue] = {"x": expr("W-w-20"), "y": 20}
    (composite,) = apply_filter(
        (background, foreground),
        "overlay",
        output_kinds=(StreamKind.VIDEO,),
        options=options,
    )

    plan = output(composite, to="branded.mp4")

    assert plan.filter_graph() == ("[0:v:0][1:v:0]overlay=x=W-w-20:y=20[v0]")


def test_filter_values_escape_graph_separators() -> None:
    assert serialize_filter_value(r"a:b,c;[x]'\tail") == (r"a\:b\,c\;\[x\]\'\\tail")


def test_overwrite_returns_a_new_plan() -> None:
    source = input("movie.mp4").video()
    original = output(source, to="copy.mp4")

    replacement = original.overwrite()

    assert original.raw_argv()[3] == "-n"
    assert replacement.raw_argv()[3] == "-y"


def test_display_redacts_url_credentials_and_headers() -> None:
    source = input(
        "https://example-user:REDACT_ME@example.com/live",
        "-headers",
        "Authorization: REDACT_ME",
    )
    plan = output(source.video(), to="capture.mp4")

    command = plan.command()

    assert "REDACT_ME" not in command
    assert "<redacted>" in command


def test_unconnected_split_output_is_rejected() -> None:
    first, _ = input("movie.mp4").video().split()

    with pytest.raises(CompilationError, match="not connected"):
        output(first, to="first.mp4").compile()


def test_reused_filter_output_requires_split() -> None:
    scaled = input("movie.mp4").video().filter("scale", 640, -2)
    plan = output(scaled, to="first.mp4").add_output(
        scaled,
        to="second.mp4",
    )

    with pytest.raises(CompilationError, match="requires split"):
        plan.compile()


def test_deep_filter_chain_compiles_without_recursion() -> None:
    stream = input("movie.mp4").video()
    for _ in range(1_000):
        stream = stream.filter("null")

    graph = output(stream, to="copy.mp4").filter_graph()

    assert graph is not None
    assert graph.count("null") == 1_000


def test_unordered_raw_arguments_are_rejected() -> None:
    with pytest.raises(GraphError, match="stable order"):
        output(input("movie.mp4").video(), to="copy.mp4", args={"-an"})
