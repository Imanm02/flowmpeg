from flowmpeg.ui.schema import FieldKind, PathRole


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
