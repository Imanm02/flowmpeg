"""JSON-ready values for the local interface API."""

from __future__ import annotations

from typing import Any

from flowmpeg.ui.schema import UiField


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


__all__ = ["field_data"]
