from flowmpeg.ui.preview import UiPreview


def test_ui_preview_keeps_arguments_separate_from_display() -> None:
    preview = UiPreview(
        arguments=("trim", "input file.mp4"),
        display='flowmpeg trim "input file.mp4"',
    )

    assert preview.arguments == ("trim", "input file.mp4")
    assert preview.display.startswith("flowmpeg trim")
