"""Typed command metadata used by the local interface."""

from __future__ import annotations

from enum import Enum


class FieldKind(str, Enum):
    """Control types understood by the browser client."""

    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    BOOLEAN = "boolean"


class PathRole(str, Enum):
    """Filesystem behavior attached to a field."""

    NONE = "none"
    INPUT_FILE = "input-file"
    INPUT_FILES = "input-files"
    INPUT_DIRECTORY = "input-directory"
    OUTPUT_FILE = "output-file"
    OUTPUT_DIRECTORY = "output-directory"


__all__ = ["FieldKind", "PathRole"]
