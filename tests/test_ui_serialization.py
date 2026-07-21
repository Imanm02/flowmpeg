import json

from flowmpeg.ui.schema import FieldKind, PathRole, UiCommand, UiField, UiSchema
from flowmpeg.ui.serialization import command_data, field_data, schema_data, schema_json
from flowmpeg.ui.serialization import validation_issue_data
from flowmpeg.ui.validation import UiValidationIssue


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
        "negativeFlags": [],
        "clearFlags": [],
        "required": True,
        "multiple": False,
        "default": None,
        "help": "",
        "choices": [],
        "pathRole": "output-file",
        "advanced": False,
    }


def test_command_data_contains_discovery_and_field_data() -> None:
    field = UiField(name="source", label="Source", kind=FieldKind.TEXT)
    command = UiCommand(
        name="trim",
        category="video",
        summary="Cut video",
        aliases=("cut",),
        tags=("creator",),
        fields=(field,),
    )

    data = command_data(command)

    assert data["name"] == "trim"
    assert data["aliases"] == ["cut"]
    assert data["fields"] == [field_data(field)]


def test_schema_data_contains_categories_and_commands() -> None:
    command = UiCommand(name="trim", category="video", summary="Cut video")
    schema = UiSchema(version=1, categories=("video",), commands=(command,))

    assert schema_data(schema) == {
        "version": 1,
        "categories": ["video"],
        "commands": [command_data(command)],
    }


def test_schema_json_round_trips_without_extra_whitespace() -> None:
    schema = UiSchema(version=1, categories=(), commands=())
    rendered = schema_json(schema)

    assert rendered == '{"version":1,"categories":[],"commands":[]}'
    assert json.loads(rendered) == schema_data(schema)


def test_validation_issue_data_keeps_field_context() -> None:
    issue = UiValidationIssue("required", "Source is required", "source")

    assert validation_issue_data(issue) == {
        "code": "required",
        "message": "Source is required",
        "field": "source",
    }
