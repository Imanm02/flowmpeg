import pytest

from flowmpeg.ui.invocation import UiInvocation, UiValue
from flowmpeg.ui.invocation_compiler import compile_invocation
from flowmpeg.ui.schema import FieldKind, UiCommand, UiField, UiSchema
from flowmpeg.ui.validation import UiValidationError


def _schema(*commands: UiCommand) -> UiSchema:
    categories = tuple(dict.fromkeys(command.category for command in commands))
    return UiSchema(version=1, categories=categories, commands=commands)


def test_ui_compiler_returns_canonical_command_name() -> None:
    command = UiCommand(
        name="trim",
        category="video",
        summary="Cut video",
        aliases=("cut",),
    )

    assert compile_invocation(_schema(command), UiInvocation("cut")) == ("trim",)


def test_ui_compiler_rejects_unknown_commands() -> None:
    with pytest.raises(UiValidationError) as caught:
        compile_invocation(_schema(), UiInvocation("missing"))

    assert caught.value.issues[0].code == "unknown-command"


def test_ui_compiler_rejects_fields_from_another_command() -> None:
    command = UiCommand(name="errors", category="help", summary="List errors")
    invocation = UiInvocation("errors", (UiValue("source", "input.mp4"),))

    with pytest.raises(UiValidationError) as caught:
        compile_invocation(_schema(command), invocation)

    assert caught.value.issues[0].code == "unknown-field"
    assert caught.value.issues[0].field == "source"


def test_ui_compiler_reports_every_missing_required_field() -> None:
    command = UiCommand(
        name="trim",
        category="video",
        summary="Cut video",
        fields=(
            UiField("source", "Source", FieldKind.TEXT, required=True),
            UiField("output", "Output", FieldKind.TEXT, required=True),
        ),
    )

    with pytest.raises(UiValidationError) as caught:
        compile_invocation(_schema(command), UiInvocation("trim"))

    assert [issue.field for issue in caught.value.issues] == ["source", "output"]


def test_ui_compiler_builds_positional_and_option_arguments() -> None:
    command = UiCommand(
        name="trim",
        category="video",
        summary="Cut video",
        fields=(
            UiField("source", "Source", FieldKind.TEXT, required=True),
            UiField(
                "start",
                "Start",
                FieldKind.NUMBER,
                flags=("--start",),
            ),
            UiField(
                "output",
                "Output",
                FieldKind.TEXT,
                flags=("-o", "--output"),
                required=True,
            ),
        ),
    )
    invocation = UiInvocation(
        "trim",
        (
            UiValue("source", "input file.mp4"),
            UiValue("start", 2.5),
            UiValue("output", "clip file.mp4"),
        ),
    )

    assert compile_invocation(_schema(command), invocation) == (
        "trim",
        "input file.mp4",
        "--start",
        "2.5",
        "--output",
        "clip file.mp4",
    )
