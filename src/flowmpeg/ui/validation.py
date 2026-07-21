"""Structured validation errors for browser command forms."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiValidationIssue:
    """One command or field problem shown to the user."""

    code: str
    message: str
    field: str | None = None


class UiValidationError(ValueError):
    """One or more invalid values in a browser submission."""

    def __init__(self, *issues: UiValidationIssue) -> None:
        if not issues:
            raise ValueError("at least one validation issue is required")
        self.issues = issues
        super().__init__(issues[0].message)


__all__ = ["UiValidationError", "UiValidationIssue"]
