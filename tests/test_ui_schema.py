import pytest

from flowmpeg.ui.schema import FieldKind, PathRole, UiCommand, UiField, UiSchema


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


@pytest.mark.parametrize("name", ["", "output path", "--output", "a/b"])
def test_ui_field_rejects_unsafe_names(name: str) -> None:
    with pytest.raises(ValueError, match="field name"):
        UiField(name=name, label="Value", kind=FieldKind.TEXT)


def test_ui_choice_field_requires_choices() -> None:
    with pytest.raises(ValueError, match="must define choices"):
        UiField(name="codec", label="Codec", kind=FieldKind.CHOICE)


def test_ui_text_field_rejects_choices() -> None:
    with pytest.raises(ValueError, match="only choice"):
        UiField(
            name="codec",
            label="Codec",
            kind=FieldKind.TEXT,
            choices=("aac",),
        )


def test_ui_field_rejects_duplicate_choices() -> None:
    with pytest.raises(ValueError, match="unique"):
        UiField(
            name="codec",
            label="Codec",
            kind=FieldKind.CHOICE,
            choices=("aac", "aac"),
        )


def test_ui_command_keeps_discovery_metadata() -> None:
    command = UiCommand(
        name="trim",
        category="video",
        summary="Cut an exact time range",
        aliases=("cut",),
        tags=("creator",),
    )

    assert command.name == "trim"
    assert command.aliases == ("cut",)
    assert command.tags == ("creator",)


@pytest.mark.parametrize("name", ["", "Trim", "trim_video", "trim video"])
def test_ui_command_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError, match="command name"):
        UiCommand(name=name, category="video", summary="Cut video")


@pytest.mark.parametrize(
    ("category", "summary"),
    [("", "Cut video"), ("video", "")],
)
def test_ui_command_requires_category_and_summary(
    category: str,
    summary: str,
) -> None:
    with pytest.raises(ValueError, match="category and summary"):
        UiCommand(name="trim", category=category, summary=summary)


def test_ui_command_rejects_duplicate_field_names() -> None:
    field = UiField(name="source", label="Source", kind=FieldKind.TEXT)

    with pytest.raises(ValueError, match="field names must be unique"):
        UiCommand(
            name="trim",
            category="video",
            summary="Cut video",
            fields=(field, field),
        )


def test_ui_schema_records_version_categories_and_commands() -> None:
    command = UiCommand(name="trim", category="video", summary="Cut video")
    schema = UiSchema(version=1, categories=("video",), commands=(command,))

    assert schema.version == 1
    assert schema.categories == ("video",)
    assert schema.commands == (command,)


def test_ui_schema_rejects_nonpositive_versions() -> None:
    with pytest.raises(ValueError, match="version must be positive"):
        UiSchema(version=0, categories=(), commands=())


@pytest.mark.parametrize("categories", [("video", "video"), ("",)])
def test_ui_schema_rejects_invalid_categories(categories: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="schema categories"):
        UiSchema(version=1, categories=categories, commands=())


def test_ui_schema_rejects_unknown_command_categories() -> None:
    command = UiCommand(name="trim", category="video", summary="Cut video")

    with pytest.raises(ValueError, match="command category"):
        UiSchema(version=1, categories=("audio",), commands=(command,))


def test_ui_schema_finds_commands_by_name_or_alias() -> None:
    command = UiCommand(
        name="trim",
        category="video",
        summary="Cut video",
        aliases=("cut",),
    )
    schema = UiSchema(version=1, categories=("video",), commands=(command,))

    assert schema.command("trim") is command
    assert schema.command("cut") is command
    assert schema.command("missing") is None
