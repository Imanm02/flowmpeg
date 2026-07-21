"""Safe terminal previews for browser submissions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiPreview:
    """A command argument list and its redacted terminal display."""

    arguments: tuple[str, ...]
    display: str


__all__ = ["UiPreview"]
