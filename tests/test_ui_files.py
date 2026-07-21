from pathlib import Path

import pytest

from flowmpeg.ui.files import DirectoryListing, FileEntry, list_directory


def test_ui_directory_listing_distinguishes_files_and_folders() -> None:
    entry = FileEntry("clip.mp4", "C:/media/clip.mp4", False, 42, 1.0)
    listing = DirectoryListing("C:/media", "C:/", (entry,), False)

    assert listing.entries[0].directory is False
    assert listing.entries[0].size == 42
    assert listing.truncated is False


def test_ui_directory_listing_sorts_folders_before_files(tmp_path: Path) -> None:
    (tmp_path / "z-folder").mkdir()
    (tmp_path / "a-file.mp4").write_bytes(b"video")

    listing = list_directory(str(tmp_path))

    assert [entry.name for entry in listing.entries] == ["z-folder", "a-file.mp4"]
    assert listing.parent == str(tmp_path.parent)


def test_ui_directory_listing_rejects_files_and_missing_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")

    with pytest.raises(ValueError, match="not a directory"):
        list_directory(str(source))
    with pytest.raises(ValueError, match="does not exist"):
        list_directory(str(tmp_path / "missing"))


def test_ui_directory_listing_reports_truncation(tmp_path: Path) -> None:
    (tmp_path / "one").touch()
    (tmp_path / "two").touch()

    listing = list_directory(str(tmp_path), limit=1)

    assert len(listing.entries) == 1
    assert listing.truncated is True
