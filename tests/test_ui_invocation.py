import pytest

from flowmpeg.ui.invocation import UiInvocation, UiValue, parse_invocation


def test_ui_value_keeps_scalar_and_multiple_values() -> None:
    assert UiValue("start", 3.5).value == 3.5
    assert UiValue("sources", ("one.mp4", "two.mp4")).value == (
        "one.mp4",
        "two.mp4",
    )


@pytest.mark.parametrize("name", ["", "source path", "--output", "a/b"])
def test_ui_value_rejects_invalid_field_names(name: str) -> None:
    with pytest.raises(ValueError, match="field name"):
        UiValue(name, "value")


def test_ui_invocation_finds_submitted_values() -> None:
    invocation = UiInvocation(
        command="trim",
        values=(UiValue("source", "input.mp4"), UiValue("start", 5)),
    )

    assert invocation.value("source") == "input.mp4"
    assert invocation.value("start") == 5
    assert invocation.value("duration") is None
    assert invocation.has("source") is True
    assert invocation.has("duration") is False


def test_ui_invocation_rejects_duplicate_values() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        UiInvocation(
            command="trim",
            values=(UiValue("start", 2), UiValue("start", 5)),
        )


def test_parse_ui_invocation_converts_text_lists_to_tuples() -> None:
    invocation = parse_invocation(
        {
            "command": "join-matching",
            "values": {"sources": ["one.mp4", "two.mp4"]},
        }
    )

    assert invocation.value("sources") == ("one.mp4", "two.mp4")


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"command": 3, "values": {}},
        {"command": "trim", "values": []},
        {"command": "trim", "values": {"start": {"bad": True}}},
    ],
)
def test_parse_ui_invocation_rejects_invalid_json_shapes(data: object) -> None:
    with pytest.raises(ValueError, match="submission|submitted"):
        parse_invocation(data)
