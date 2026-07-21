"""Typed command metadata used by the local interface."""

from __future__ import annotations

from enum import Enum


class FieldKind(str, Enum):
    """Control types understood by the browser client."""

    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    BOOLEAN = "boolean"


__all__ = ["FieldKind"]
