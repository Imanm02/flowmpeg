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


__all__ = ["SubmittedValue", "UiValue"]
