import pytest

from flowmpeg.ui.validation import UiValidationError, UiValidationIssue


def test_ui_validation_error_keeps_all_issues() -> None:
    source = UiValidationIssue("required", "Source is required", "source")
    output = UiValidationIssue("required", "Output is required", "output")
    error = UiValidationError(source, output)

    assert str(error) == "Source is required"
    assert error.issues == (source, output)


def test_ui_validation_error_requires_an_issue() -> None:
    with pytest.raises(ValueError, match="at least one"):
        UiValidationError()
