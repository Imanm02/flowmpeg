from flowmpeg.ui.invocation import UiValue


def test_ui_value_keeps_scalar_and_multiple_values() -> None:
    assert UiValue("start", 3.5).value == 3.5
    assert UiValue("sources", ("one.mp4", "two.mp4")).value == (
        "one.mp4",
        "two.mp4",
    )
