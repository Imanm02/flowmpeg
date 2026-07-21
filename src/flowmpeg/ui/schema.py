"""Typed command metadata used by the local interface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


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


FieldValue: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class UiField:
    """One positional value or option in a command form."""

    name: str
    label: str
    kind: FieldKind
    flags: tuple[str, ...] = ()
    required: bool = False
    multiple: bool = False
    default: FieldValue = None
    help: str = ""
    choices: tuple[str, ...] = ()
    path_role: PathRole = PathRole.NONE
    advanced: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("field name must contain letters, digits, or underscores")


__all__ = ["FieldKind", "FieldValue", "PathRole", "UiField"]
