"""JSON-ready values for the local interface API."""

from __future__ import annotations

import json
from typing import Any

from flowmpeg.ui.files import DirectoryListing
from flowmpeg.ui.jobs import UiJobSnapshot
from flowmpeg.ui.preview import UiPreview
from flowmpeg.ui.schema import UiCommand, UiField, UiSchema
from flowmpeg.ui.validation import UiValidationIssue


def field_data(field: UiField) -> dict[str, Any]:
    """Return one UI field as JSON-compatible data."""

    return {
        "name": field.name,
        "label": field.label,
        "kind": field.kind.value,
        "flags": list(field.flags),
        "negativeFlags": list(field.negative_flags),
        "clearFlags": list(field.clear_flags),
        "required": field.required,
        "multiple": field.multiple,
        "default": field.default,
        "help": field.help,
        "choices": list(field.choices),
        "pathRole": field.path_role.value,
        "advanced": field.advanced,
        "integer": field.integer,
        "minimum": field.minimum,
        "exclusiveMinimum": field.exclusive_minimum,
    }


def command_data(command: UiCommand) -> dict[str, Any]:
    """Return one UI command as JSON-compatible data."""

    return {
        "name": command.name,
        "category": command.category,
        "summary": command.summary,
        "aliases": list(command.aliases),
        "tags": list(command.tags),
        "inputKind": command.input_kind,
        "outputKind": command.output_kind,
        "fields": [field_data(field) for field in command.fields],
    }


def schema_data(schema: UiSchema) -> dict[str, Any]:
    """Return the complete form schema as JSON-compatible data."""

    return {
        "version": schema.version,
        "categories": list(schema.categories),
        "commands": [command_data(command) for command in schema.commands],
    }


def schema_json(schema: UiSchema) -> str:
    """Render a deterministic compact schema response."""

    return json.dumps(schema_data(schema), ensure_ascii=False, separators=(",", ":"))


def validation_issue_data(issue: UiValidationIssue) -> dict[str, str | None]:
    """Return a field error as JSON-compatible data."""

    return {
        "code": issue.code,
        "message": issue.message,
        "field": issue.field,
    }


def preview_data(preview: UiPreview) -> dict[str, Any]:
    """Return a command preview as JSON-compatible data."""

    return {
        "arguments": list(preview.arguments),
        "display": preview.display,
    }


def job_data(job: UiJobSnapshot) -> dict[str, Any]:
    """Return safe public job state as JSON-compatible data."""

    return {
        "id": job.id,
        "display": job.display,
        "status": job.status.value,
        "createdAt": job.created_at,
        "startedAt": job.started_at,
        "finishedAt": job.finished_at,
        "returncode": job.returncode,
        "output": job.output,
    }


def directory_data(listing: DirectoryListing) -> dict[str, Any]:
    """Return a local directory listing as JSON-compatible data."""

    return {
        "path": listing.path,
        "parent": listing.parent,
        "truncated": listing.truncated,
        "entries": [
            {
                "name": entry.name,
                "path": entry.path,
                "directory": entry.directory,
                "size": entry.size,
                "modifiedAt": entry.modified_at,
            }
            for entry in listing.entries
        ],
    }


__all__ = [
    "command_data",
    "directory_data",
    "field_data",
    "job_data",
    "preview_data",
    "schema_data",
    "schema_json",
    "validation_issue_data",
]
