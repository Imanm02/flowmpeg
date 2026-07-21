"""Compile validated browser submissions into terminal arguments."""

from __future__ import annotations

import math

from flowmpeg.ui.invocation import UiInvocation
from flowmpeg.ui.schema import FieldKind, UiField, UiSchema
from flowmpeg.ui.validation import UiValidationError, UiValidationIssue


def compile_invocation(schema: UiSchema, invocation: UiInvocation) -> tuple[str, ...]:
    """Compile a browser command submission without invoking a shell."""

    command = schema.command(invocation.command)
    if command is None:
        raise UiValidationError(
            UiValidationIssue(
                code="unknown-command",
                message="The selected command is not available",
            )
        )
    known_fields = {field.name for field in command.fields}
    unknown_fields = [
        item.name for item in invocation.values if item.name not in known_fields
    ]
    if unknown_fields:
        raise UiValidationError(
            *(
                UiValidationIssue(
                    code="unknown-field",
                    message=f"{name} is not accepted by {command.name}",
                    field=name,
                )
                for name in unknown_fields
            )
        )
    missing = [
        field
        for field in command.fields
        if field.required
        and (
            not invocation.has(field.name)
            or invocation.value(field.name) in {None, "", ()}
        )
    ]
    if missing:
        raise UiValidationError(
            *(
                UiValidationIssue(
                    code="required",
                    message=f"{field.label} is required",
                    field=field.name,
                )
                for field in missing
            )
        )
    arguments = [command.name]
    for field in command.fields:
        if not invocation.has(field.name):
            continue
        value = invocation.value(field.name)
        if value is None:
            if field.clear_flags:
                arguments.append(field.clear_flags[0])
            continue
        if field.flags and value == field.default:
            continue
        arguments.extend(_field_arguments(field, value))
    return tuple(arguments)


def _field_arguments(field: UiField, value: object) -> tuple[str, ...]:
    if field.multiple:
        return _multiple_arguments(field, value)
    if field.kind is FieldKind.BOOLEAN:
        return _boolean_arguments(field, value)
    if field.kind is FieldKind.CHOICE:
        if not isinstance(value, str) or value not in field.choices:
            raise UiValidationError(
                UiValidationIssue(
                    code="invalid-choice",
                    message=f"{field.label} is not one of the available choices",
                    field=field.name,
                )
            )
    if field.kind is FieldKind.NUMBER:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _invalid_type(field)
        if not math.isfinite(value):
            raise UiValidationError(
                UiValidationIssue(
                    code="nonfinite-number",
                    message=f"{field.label} must be a finite number",
                    field=field.name,
                )
            )
    if field.kind is FieldKind.TEXT and (
        not isinstance(value, str) or not value
    ):
        raise _invalid_type(field)
    return _scalar_arguments(field, value)


def _multiple_arguments(field: UiField, value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise _invalid_type(field)
    if field.flags:
        return (field.flags[-1], *value)
    return value


def _boolean_arguments(field: UiField, value: object) -> tuple[str, ...]:
    if not isinstance(value, bool):
        raise _invalid_type(field)
    if value == field.default:
        return ()
    flags = field.flags if value else field.negative_flags
    if not flags:
        raise UiValidationError(
            UiValidationIssue(
                code="unsupported-value",
                message=f"{field.label} cannot be set to {str(value).lower()}",
                field=field.name,
            )
        )
    return (flags[0] if not value else flags[-1],)


def _scalar_arguments(field: UiField, value: object) -> tuple[str, ...]:
    if isinstance(value, (tuple, bool)):
        raise _invalid_type(field)
    rendered = str(value)
    if field.flags:
        return (field.flags[-1], rendered)
    return (rendered,)


def _invalid_type(field: UiField) -> UiValidationError:
    return UiValidationError(
        UiValidationIssue(
            code="invalid-type",
            message=f"{field.label} has an invalid value",
            field=field.name,
        )
    )


__all__ = ["compile_invocation"]
