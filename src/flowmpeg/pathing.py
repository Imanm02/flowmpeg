"""Local path detection and identity checks."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

_protocol = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")
_windows_uri_path = re.compile(r"^/[A-Za-z]:[/\\]")


def local_path(value: str) -> Path | None:
    """Return the local path represented by a filename or file URL."""

    if value == "-" or value.upper() == "NUL" or value == "/dev/null":
        return None
    drive, _ = os.path.splitdrive(value)
    protocol = _protocol.match(value)
    if drive or protocol is None:
        return Path(value)
    if protocol.group()[:-1].lower() != "file":
        return None

    parsed = urlsplit(value)
    path = unquote(parsed.path)
    if parsed.netloc and parsed.netloc.lower() != "localhost":
        path = f"//{parsed.netloc}{path}"
    if os.name == "nt" and _windows_uri_path.match(path):
        path = path[1:]
    return Path(path)


def same_destination(first: str, second: str) -> bool:
    """Return whether two FFmpeg destinations identify the same resource."""

    first_path = local_path(first)
    second_path = local_path(second)
    if first_path is None or second_path is None:
        return first_path is None and second_path is None and first == second
    try:
        return os.path.samefile(first_path, second_path)
    except (FileNotFoundError, OSError):
        return _path_id(first_path) == _path_id(second_path)


def _path_id(path: Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))
