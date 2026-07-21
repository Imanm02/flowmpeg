import pytest

from flowmpeg.ui.invocation import UiValue


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
