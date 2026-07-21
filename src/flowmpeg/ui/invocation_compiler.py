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
    return (command.name,)


__all__ = ["compile_invocation"]
