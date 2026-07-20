from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_demo_media_script_generates_example_inputs(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg and FFprobe are required")

    completed = subprocess.run(
        (sys.executable, "scripts/make_demo_media.py", str(tmp_path)),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
        shell=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "sample.mp4").stat().st_size > 0
    assert (tmp_path / "voice.wav").stat().st_size > 0
    assert (tmp_path / "cover.jpg").stat().st_size > 0
    assert "Flowmpeg demo caption" in (tmp_path / "captions.srt").read_text(
        encoding="utf-8"
    )
