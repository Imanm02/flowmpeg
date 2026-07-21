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
    negative_flags: tuple[str, ...] = ()
    clear_flags: tuple[str, ...] = ()
    required: bool = False
    multiple: bool = False
    default: FieldValue = None
    help: str = ""
    choices: tuple[str, ...] = ()
    path_role: PathRole = PathRole.NONE
    advanced: bool = False
    integer: bool = False
    minimum: int | float | None = None
    exclusive_minimum: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("field name must contain letters, digits, or underscores")
        if self.kind is FieldKind.CHOICE and not self.choices:
            raise ValueError("choice fields must define choices")
        if self.kind is not FieldKind.CHOICE and self.choices:
            raise ValueError("only choice fields can define choices")
        if len(self.choices) != len(set(self.choices)):
            raise ValueError("field choices must be unique")
        all_flags = (*self.flags, *self.negative_flags, *self.clear_flags)
        if len(all_flags) != len(set(all_flags)):
            raise ValueError("field flags must be unique")
        if self.kind is not FieldKind.NUMBER and (
            self.integer or self.minimum is not None or self.exclusive_minimum
        ):
            raise ValueError("numeric constraints require a number field")
        if self.exclusive_minimum and self.minimum is None:
            raise ValueError("an exclusive minimum requires a minimum")


@dataclass(frozen=True, slots=True)
class UiCommand:
    """One terminal command presented as a browser form."""

    name: str
    category: str
    summary: str
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    input_kind: str = "media"
    output_kind: str = "media"
    fields: tuple[UiField, ...] = ()

    def __post_init__(self) -> None:
        if not self.name or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-"
            for character in self.name
        ):
            raise ValueError(
                "command name must use lowercase letters, digits, or hyphens"
            )
        if not self.category or not self.summary:
            raise ValueError("command category and summary are required")
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("command field names must be unique")


@dataclass(frozen=True, slots=True)
class UiSchema:
    """The command surface and its stable schema version."""

    version: int
    categories: tuple[str, ...]
    commands: tuple[UiCommand, ...]

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("schema version must be positive")
        if any(not category for category in self.categories):
            raise ValueError("schema categories cannot be empty")
        if len(self.categories) != len(set(self.categories)):
            raise ValueError("schema categories must be unique")
        names = [command.name for command in self.commands]
        if len(names) != len(set(names)):
            raise ValueError("schema command names must be unique")
        all_names = [
            name
            for command in self.commands
            for name in (command.name, *command.aliases)
        ]
        if len(all_names) != len(set(all_names)):
            raise ValueError("schema command names and aliases must be unique")
        unknown = {
            command.category
            for command in self.commands
            if command.category not in self.categories
        }
        if unknown:
            raise ValueError("every command category must appear in the schema")

    def command(self, name: str) -> UiCommand | None:
        """Find a command by canonical name or alias."""

        return next(
            (
                command
                for command in self.commands
                if name == command.name or name in command.aliases
            ),
            None,
        )


__all__ = [
    "FieldKind",
    "FieldValue",
    "PathRole",
    "UiCommand",
    "UiField",
    "UiSchema",
]
