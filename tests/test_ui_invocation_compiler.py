import pytest

from flowmpeg.ui.invocation import UiInvocation, UiValue
from flowmpeg.ui.invocation_compiler import compile_invocation
from flowmpeg.ui.schema import UiCommand, UiSchema
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
