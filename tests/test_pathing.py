import os
from pathlib import Path

import pytest

from flowmpeg.pathing import (
    _strip_windows_extended_prefix,
    local_path,
    same_destination,
)


def test_null_sink_matches_the_current_platform() -> None:
    if os.name == "nt":
        assert local_path("NUL") is None
        assert local_path("/dev/null") == Path("/dev/null")
    else:
        assert local_path("/dev/null") is None
        assert local_path("NUL") == Path("NUL")


def test_file_protocol_null_sink_is_an_alias() -> None:
    if os.name == "nt":
        assert local_path("file:NUL") is None
        assert same_destination("NUL", "file:NUL")
    else:
        assert local_path("file:/dev/null") is None
        assert same_destination("/dev/null", "file:/dev/null")


def test_windows_extended_prefixes_are_removed() -> None:
    assert _strip_windows_extended_prefix(r"\\?\C:\media\clip.mp4") == (
        r"C:\media\clip.mp4"
    )
    assert _strip_windows_extended_prefix(r"\\?\UNC\server\share\clip.mp4") == (
        r"\\server\share\clip.mp4"
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows path identity test")
def test_windows_extended_path_is_an_output_alias(tmp_path: Path) -> None:
    target = tmp_path / "missing.mp4"
    extended = "\\\\?\\" + os.fspath(target)

    assert same_destination(os.fspath(target), extended)
