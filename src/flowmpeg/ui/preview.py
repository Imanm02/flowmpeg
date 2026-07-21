"""Safe terminal previews for browser submissions."""

from __future__ import annotations

from dataclasses import dataclass

from flowmpeg.diagnostics import display_argv
from flowmpeg.ui.invocation import UiInvocation
from flowmpeg.ui.invocation_compiler import compile_invocation
from flowmpeg.ui.schema import UiSchema


@dataclass(frozen=True, slots=True)
class UiPreview:
    """A command argument list and its redacted terminal display."""

    arguments: tuple[str, ...]
    display: str


def preview_invocation(schema: UiSchema, invocation: UiInvocation) -> UiPreview:
    """Compile a submission and prepare a safe terminal display."""

    arguments = compile_invocation(schema, invocation)
    display = display_argv(("flowmpeg", *arguments))
    return UiPreview(arguments=arguments, display=display)


__all__ = ["UiPreview", "preview_invocation"]
