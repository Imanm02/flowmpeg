from flowmpeg.ui.schema import FieldKind, PathRole, UiField


def test_field_kinds_have_stable_json_values() -> None:
    assert [kind.value for kind in FieldKind] == [
        "text",
        "number",
        "choice",
        "boolean",
    ]


def test_path_roles_distinguish_files_and_directories() -> None:
    assert PathRole.INPUT_FILE.value == "input-file"
    assert PathRole.OUTPUT_DIRECTORY.value == "output-directory"


def test_ui_field_keeps_form_metadata() -> None:
    field = UiField(
        name="output",
        label="Output",
        kind=FieldKind.TEXT,
        flags=("-o", "--output"),
        required=True,
        path_role=PathRole.OUTPUT_FILE,
    )

    assert field.flags == ("-o", "--output")
    assert field.required is True
    assert field.path_role is PathRole.OUTPUT_FILE
