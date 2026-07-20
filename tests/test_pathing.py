import os
from pathlib import Path

from flowmpeg.pathing import local_path, same_destination


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
