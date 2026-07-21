from flowmpeg.ui.invocation import UiInvocation, UiValue
from flowmpeg.ui.preview import UiPreview, preview_invocation
from flowmpeg.ui.schema import FieldKind, UiCommand, UiField, UiSchema


def test_ui_preview_keeps_arguments_separate_from_display() -> None:
    preview = UiPreview(
        arguments=("trim", "input file.mp4"),
        display='flowmpeg trim "input file.mp4"',
    )

    assert preview.arguments == ("trim", "input file.mp4")
    assert preview.display.startswith("flowmpeg trim")


def test_ui_preview_redacts_secret_query_values() -> None:
    command = UiCommand(
        name="probe",
        category="inspect",
        summary="Inspect media",
        fields=(UiField("source", "Source", FieldKind.TEXT, required=True),),
    )
    schema = UiSchema(
        version=1,
        categories=("inspect",),
        commands=(command,),
    )
    invocation = UiInvocation(
        "probe",
        (UiValue("source", "https://example.com/v.mp4?token=private-value"),),
    )

    preview = preview_invocation(schema, invocation)

    assert preview.arguments[-1].endswith("private-value")
    assert "private-value" not in preview.display
    assert "<redacted>" in preview.display
