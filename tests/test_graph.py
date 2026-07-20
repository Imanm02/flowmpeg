from typing import cast

import pytest

from flowmpeg import GraphError, OutputSpec, Plan, input
from flowmpeg.model import (
    Expression,
    FilterNode,
    FilterOption,
    FilterValue,
    InputNode,
    MediaGraph,
    NodeKey,
    StreamKind,
    StreamRef,
)
from flowmpeg.streams import AudioStream, VideoStream, apply_filter


def test_input_selects_typed_streams() -> None:
    source = input("movie.mp4")

    assert isinstance(source.video(), VideoStream)
    assert isinstance(source.audio(1), AudioStream)
    assert source.audio(1).ref.pad == 1


def test_expressions_reject_non_text_values() -> None:
    with pytest.raises(GraphError, match="nonempty text"):
        Expression(cast(str, 12))


def test_filter_nodes_reject_unknown_runtime_values() -> None:
    source = InputNode(NodeKey(20), "movie.mp4")
    stream = StreamRef(source.key, 0, StreamKind.VIDEO)

    with pytest.raises(GraphError, match="unsupported type"):
        FilterNode(
            NodeKey(21),
            "scale",
            (stream,),
            (StreamKind.VIDEO,),
            args=(cast(FilterValue, object()),),
        )


def test_hand_built_filters_reject_optional_inputs() -> None:
    source = InputNode(NodeKey(30), "silent.mp4")
    optional_audio = StreamRef(source.key, 0, StreamKind.AUDIO, optional=True)

    with pytest.raises(GraphError, match="cannot feed filters"):
        FilterNode(
            NodeKey(31),
            "volume",
            (optional_audio,),
            (StreamKind.AUDIO,),
        )


def test_filter_options_reject_unknown_runtime_values() -> None:
    with pytest.raises(GraphError, match="unsupported type"):
        FilterOption("width", cast(FilterValue, object()))


@pytest.mark.parametrize("selector", ["video", "audio", "subtitle"])
def test_stream_selectors_reject_boolean_indexes(selector: str) -> None:
    source = input("movie.mp4")

    with pytest.raises(GraphError, match="must be integers"):
        getattr(source, selector)(True)


def test_filter_keeps_the_source_graph_unchanged() -> None:
    source = input("movie.mp4")
    original = source.video()

    scaled = original.filter("scale", 1280, -2)

    assert original.graph.filters == ()
    assert len(scaled.graph.filters) == 1
    assert scaled.graph.filters[0].args == (1280, -2)


def test_filter_merges_independent_inputs() -> None:
    foreground = input("logo.png").video()
    background = input("movie.mp4").video()

    (result,) = apply_filter(
        (background, foreground),
        "overlay",
        output_kinds=(StreamKind.VIDEO,),
        options={"x": 20, "y": 30},
    )

    assert len(result.graph.inputs) == 2
    assert result.graph.filters[0].inputs == (background.ref, foreground.ref)


def test_split_returns_distinct_output_pads() -> None:
    outputs = input("movie.mp4").video().split(3)

    assert [stream.ref.pad for stream in outputs] == [0, 1, 2]
    assert len({stream.ref.node for stream in outputs}) == 1
    assert outputs[0].graph.filters[0].name == "split"


def test_invalid_filter_name_is_rejected() -> None:
    with pytest.raises(GraphError, match="Invalid filter name"):
        input("movie.mp4").video().filter("scale;movie=bad")


def test_unordered_filter_options_are_rejected() -> None:
    video = input("movie.mp4").video()

    with pytest.raises(GraphError, match="stable order"):
        apply_filter(
            (video,),
            "scale",
            output_kinds=(StreamKind.VIDEO,),
            options={("width", 640), ("height", 360)},
        )


def test_duplicate_filter_options_are_rejected() -> None:
    video = input("movie.mp4").video()

    with pytest.raises(GraphError, match="must be unique"):
        apply_filter(
            (video,),
            "scale",
            output_kinds=(StreamKind.VIDEO,),
            options=(("width", 640), ("width", 1280)),
        )


def test_subtitle_split_is_rejected() -> None:
    with pytest.raises(GraphError, match="Subtitle streams cannot be split"):
        input("movie.mkv").subtitle().split()


def test_graph_rejects_unknown_references() -> None:
    node = FilterNode(
        key=NodeKey(2),
        name="scale",
        inputs=(StreamRef(NodeKey(1), 0, StreamKind.VIDEO),),
        output_kinds=(StreamKind.VIDEO,),
    )

    with pytest.raises(GraphError, match="unknown input"):
        MediaGraph(filters=(node,)).validate()


def test_graph_rejects_cycles() -> None:
    first = FilterNode(
        key=NodeKey(1),
        name="scale",
        inputs=(StreamRef(NodeKey(2), 0, StreamKind.VIDEO),),
        output_kinds=(StreamKind.VIDEO,),
    )
    second = FilterNode(
        key=NodeKey(2),
        name="fps",
        inputs=(StreamRef(NodeKey(1), 0, StreamKind.VIDEO),),
        output_kinds=(StreamKind.VIDEO,),
    )

    with pytest.raises(GraphError, match="cycles"):
        MediaGraph(filters=(first, second)).validate()


def test_graph_rejects_malformed_node_members() -> None:
    graph = MediaGraph(inputs=(cast(InputNode, object()),))

    with pytest.raises(GraphError, match="must be input nodes"):
        graph.validate()


def test_output_spec_rejects_malformed_stream_members() -> None:
    with pytest.raises(GraphError, match="must be stream references"):
        OutputSpec("out.mp4", (cast(StreamRef, object()),))


def test_filter_outputs_cannot_be_optional() -> None:
    filtered = input("movie.mp4").video().filter("scale", 640, -2)
    optional_output = StreamRef(
        filtered.ref.node,
        filtered.ref.pad,
        filtered.ref.kind,
        optional=True,
    )
    spec = OutputSpec("out.mp4", (optional_output,))

    with pytest.raises(GraphError, match="direct input mappings"):
        Plan(filtered.graph, (spec,))
