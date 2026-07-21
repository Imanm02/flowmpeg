"""JSON-ready values for the local interface API."""

from __future__ import annotations

from typing import Any

from flowmpeg.ui.schema import UiCommand, UiField


def field_data(field: UiField) -> dict[str, Any]:
    """Return one UI field as JSON-compatible data."""

    return {
        "name": field.name,
        "label": field.label,
        "kind": field.kind.value,
        "flags": list(field.flags),
        "required": field.required,
        "multiple": field.multiple,
        "default": field.default,
        "help": field.help,
        "choices": list(field.choices),
        "pathRole": field.path_role.value,
        "advanced": field.advanced,
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


__all__ = ["command_data", "field_data"]
