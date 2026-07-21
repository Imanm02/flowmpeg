import json

from flowmpeg.ui.files import DirectoryListing, FileEntry
from flowmpeg.ui.jobs import JobStatus, UiJobSnapshot
from flowmpeg.ui.preview import UiPreview
from flowmpeg.ui.schema import FieldKind, PathRole, UiCommand, UiField, UiSchema
from flowmpeg.ui.serialization import (
    command_data,
    directory_data,
    field_data,
    job_data,
    preview_data,
    schema_data,
    schema_json,
    validation_issue_data,
)
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
        "integer": False,
        "minimum": None,
        "exclusiveMinimum": False,
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


def test_preview_data_keeps_tokens_and_display_separate() -> None:
    preview = UiPreview(("trim", "input file.mp4"), "flowmpeg trim input.mp4")

    assert preview_data(preview) == {
        "arguments": ["trim", "input file.mp4"],
        "display": "flowmpeg trim input.mp4",
    }


def test_job_data_uses_public_safe_snapshot_fields() -> None:
    snapshot = UiJobSnapshot(
        id="job-1",
        display="flowmpeg errors",
        status=JobStatus.SUCCEEDED,
        created_at=1.0,
        started_at=2.0,
        finished_at=3.0,
        returncode=0,
        output="done",
    )

    assert job_data(snapshot) == {
        "id": "job-1",
        "display": "flowmpeg errors",
        "status": "succeeded",
        "createdAt": 1.0,
        "startedAt": 2.0,
        "finishedAt": 3.0,
        "returncode": 0,
        "output": "done",
    }


def test_directory_data_keeps_path_metadata_only() -> None:
    listing = DirectoryListing(
        path="C:/media",
        parent="C:/",
        entries=(FileEntry("clip.mp4", "C:/media/clip.mp4", False, 42, 1.0),),
        truncated=False,
    )

    assert directory_data(listing)["entries"] == [
        {
            "name": "clip.mp4",
            "path": "C:/media/clip.mp4",
            "directory": False,
            "size": 42,
            "modifiedAt": 1.0,
        }
    ]
