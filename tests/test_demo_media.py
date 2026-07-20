from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from flowmpeg import cli, probe


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
    assert (tmp_path / "second.mp4").stat().st_size > 0
    assert (tmp_path / "silent.mp4").stat().st_size > 0
    assert (tmp_path / "voice.wav").stat().st_size > 0
    assert (tmp_path / "music.wav").stat().st_size > 0
    assert (tmp_path / "cover.jpg").stat().st_size > 0
    assert (tmp_path / "logo.png").stat().st_size > 0
    for index in range(1, 5):
        assert (tmp_path / f"frame-{index:03}.png").stat().st_size > 0
    assert "Flowmpeg demo caption" in (tmp_path / "captions.srt").read_text(
        encoding="utf-8"
    )
    assert probe(tmp_path / "silent.mp4").audio_streams == ()

    video = tmp_path / "sample.mp4"
    clip = tmp_path / "clip.mp4"
    waveform = tmp_path / "waveform.png"
    captioned = tmp_path / "captioned.mp4"
    audiogram = tmp_path / "audiogram.mp4"
    joined = tmp_path / "joined.mp4"
    grid = tmp_path / "grid.mp4"
    branded = tmp_path / "branded.mp4"
    square = tmp_path / "square.mp4"
    assert cli.main(["probe", str(video)]) == 0
    assert (
        cli.main(
            [
                "cut",
                str(video),
                "--duration",
                "1",
                "--no-progress",
                "-o",
                str(clip),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "waveform",
                str(tmp_path / "voice.wav"),
                "--no-progress",
                "-o",
                str(waveform),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "captions",
                str(video),
                str(tmp_path / "captions.srt"),
                "--no-progress",
                "-o",
                str(captioned),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "audiogram",
                str(tmp_path / "voice.wav"),
                str(tmp_path / "cover.jpg"),
                "--no-progress",
                "-o",
                str(audiogram),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "join",
                str(video),
                str(tmp_path / "second.mp4"),
                "--no-progress",
                "-o",
                str(joined),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "grid",
                str(video),
                str(tmp_path / "second.mp4"),
                "--columns",
                "2",
                "--cell-width",
                "320",
                "--cell-height",
                "180",
                "--no-progress",
                "-o",
                str(grid),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "mark",
                str(video),
                str(tmp_path / "logo.png"),
                "--position",
                "top-right",
                "--width",
                "64",
                "--no-progress",
                "-o",
                str(branded),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "social",
                str(video),
                "--target",
                "square",
                "--fill",
                "blur",
                "--no-progress",
                "-o",
                str(square),
            ]
        )
        == 0
    )

    for target in (
        clip,
        waveform,
        captioned,
        audiogram,
        joined,
        grid,
        branded,
        square,
    ):
        assert target.stat().st_size > 0
    assert len(probe(captioned).subtitle_streams) == 1
    assert probe(audiogram).duration == pytest.approx(2.0, abs=0.2)
    joined_info = probe(joined)
    assert joined_info.duration == pytest.approx(4.0, abs=0.2)
    assert len(joined_info.video_streams) == 1
    assert len(joined_info.audio_streams) == 1
    grid_video = probe(grid).video_streams[0]
    assert (grid_video.width, grid_video.height) == (640, 180)
    branded_info = probe(branded)
    branded_video = branded_info.video_streams[0]
    assert (branded_video.width, branded_video.height) == (320, 180)
    assert len(branded_info.audio_streams) == 1
    square_info = probe(square)
    square_video = square_info.video_streams[0]
    assert (square_video.width, square_video.height) == (1080, 1080)
    assert len(square_info.audio_streams) == 1
