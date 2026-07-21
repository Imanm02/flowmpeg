"""Compile validated browser submissions into terminal arguments."""

from __future__ import annotations

from flowmpeg.ui.invocation import UiInvocation
from flowmpeg.ui.schema import UiSchema
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
    return (command.name,)


__all__ = ["compile_invocation"]
