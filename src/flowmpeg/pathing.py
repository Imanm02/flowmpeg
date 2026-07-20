"""Local path detection and identity checks."""

from __future__ import annotations

import os
import re
from pathlib import Path

_protocol = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")


def local_path(value: str) -> Path | None:
    """Return the local path represented by a filename or file URL."""

    if value == "-":
        return None
    drive, _ = os.path.splitdrive(value)
    protocol = _protocol.match(value)
    if drive or protocol is None:
        path = Path(value)
    elif protocol.group()[:-1].lower() == "file":
        path = Path(value[protocol.end() :])
    else:
        return None

    return None if _is_null_path(path) else path


def same_destination(first: str, second: str) -> bool:
    """Return whether two FFmpeg destinations identify the same resource."""

    first_path = local_path(first)
    second_path = local_path(second)
    if first_path is None or second_path is None:
        if _is_null_destination(first) and _is_null_destination(second):
            return True
        return first_path is None and second_path is None and first == second
    try:
        return os.path.samefile(first_path, second_path)
    except (FileNotFoundError, OSError):
        return _path_id(first_path) == _path_id(second_path)


def _path_id(path: Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def _is_null_path(path: Path) -> bool:
    if os.name == "nt":
        return path.name.upper() == "NUL"
    return os.path.abspath(path) == "/dev/null"


def _is_null_destination(value: str) -> bool:
    drive, _ = os.path.splitdrive(value)
    protocol = _protocol.match(value)
    if drive or protocol is None:
        path = Path(value)
    elif protocol.group()[:-1].lower() == "file":
        path = Path(value[protocol.end() :])
    else:
        return False
    return _is_null_path(path)
