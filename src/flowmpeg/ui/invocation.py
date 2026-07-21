"""Validated command submissions from the local browser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

SubmittedValue: TypeAlias = str | int | float | bool | None | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UiValue:
    """One named value submitted for a command field."""

    name: str
    value: SubmittedValue

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("submitted field name is invalid")


@dataclass(frozen=True, slots=True)
class UiInvocation:
    """One command and the values selected in its form."""

    command: str
    values: tuple[UiValue, ...] = ()

    def __post_init__(self) -> None:
        if not self.command or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-"
            for character in self.command
        ):
            raise ValueError("submitted command name is invalid")
        names = [item.name for item in self.values]
        if len(names) != len(set(names)):
            raise ValueError("submitted field names must be unique")

    def value(self, name: str) -> SubmittedValue:
        """Return a submitted value, or None when it was omitted."""

        item = next((item for item in self.values if item.name == name), None)
        return None if item is None else item.value


__all__ = ["SubmittedValue", "UiInvocation", "UiValue"]
