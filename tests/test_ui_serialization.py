from flowmpeg.ui.schema import FieldKind, PathRole, UiField
from flowmpeg.ui.serialization import field_data


def test_field_data_uses_browser_property_names() -> None:
    field = UiField(
        name="output",
        label="Output",
        kind=FieldKind.TEXT,
        flags=("-o", "--output"),
        required=True,
        path_role=PathRole.OUTPUT_FILE,
    )

    assert field_data(field) == {
        "name": "output",
        "label": "Output",
        "kind": "text",
        "flags": ["-o", "--output"],
        "required": True,
        "multiple": False,
        "default": None,
        "help": "",
        "choices": [],
        "pathRole": "output-file",
        "advanced": False,
    }
