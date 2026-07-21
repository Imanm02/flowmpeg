"""Local path browsing for command form fields."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileEntry:
    """One child path shown in the local file browser."""

    name: str
    path: str
    directory: bool
    size: int | None
    modified_at: float | None


@dataclass(frozen=True, slots=True)
class DirectoryListing:
    """A bounded view of one local directory."""

    path: str
    parent: str | None
    entries: tuple[FileEntry, ...]
    truncated: bool


__all__ = ["DirectoryListing", "FileEntry"]
