from flowmpeg.ui.schema import FieldKind


def test_field_kinds_have_stable_json_values() -> None:
    assert [kind.value for kind in FieldKind] == [
        "text",
        "number",
        "choice",
        "boolean",
    ]
