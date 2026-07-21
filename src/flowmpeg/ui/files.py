"""Local path browsing for command form fields."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_DIRECTORY_ENTRIES = 1000


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


def list_directory(
    requested_path: str | None = None,
    *,
    limit: int = MAX_DIRECTORY_ENTRIES,
) -> DirectoryListing:
    """List one local directory without reading file contents."""

    if limit < 1 or limit > MAX_DIRECTORY_ENTRIES:
        raise ValueError("directory limit is out of range")
    path = Path.cwd() if not requested_path else Path(requested_path).expanduser()
    path = path.resolve()
    if not path.exists():
        raise ValueError("directory does not exist")
    if not path.is_dir():
        raise ValueError("path is not a directory")
    children = sorted(
        path.iterdir(),
        key=lambda child: (not child.is_dir(), child.name.casefold()),
    )
    entries: list[FileEntry] = []
    for child in children[:limit]:
        try:
            stat = child.stat()
            directory = child.is_dir()
            entries.append(
                FileEntry(
                    name=child.name,
                    path=str(child),
                    directory=directory,
                    size=None if directory else stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )
        except OSError:
            continue
    parent = None if path.parent == path else str(path.parent)
    return DirectoryListing(
        path=str(path),
        parent=parent,
        entries=tuple(entries),
        truncated=len(children) > limit,
    )


def create_directory(parent_path: str, name: str) -> str:
    """Create one direct child folder after strict name checks."""

    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or any(ord(character) < 32 for character in name)
    ):
        raise ValueError("folder name must be one plain path component")
    parent = Path(parent_path).expanduser().resolve()
    if not parent.is_dir():
        raise ValueError("parent path is not a directory")
    target = parent / name
    if target.exists():
        raise ValueError("folder already exists")
    target.mkdir()
    return str(target.resolve())


__all__ = [
    "DirectoryListing",
    "FileEntry",
    "MAX_DIRECTORY_ENTRIES",
    "create_directory",
    "list_directory",
]
