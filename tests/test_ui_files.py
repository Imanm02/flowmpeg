from flowmpeg.ui.files import DirectoryListing, FileEntry


def test_ui_directory_listing_distinguishes_files_and_folders() -> None:
    entry = FileEntry("clip.mp4", "C:/media/clip.mp4", False, 42, 1.0)
    listing = DirectoryListing("C:/media", "C:/", (entry,), False)

    assert listing.entries[0].directory is False
    assert listing.entries[0].size == 42
    assert listing.truncated is False
