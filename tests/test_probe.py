import shutil
import subprocess
from pathlib import Path

import pytest

from flowmpeg import (
    BinaryNotFoundError,
    BinaryUnusableError,
    ProbeError,
    probe,
    probe_raw,
)
from flowmpeg.probe import AudioStreamInfo, Rational, parse_probe_data


def test_parse_probe_data_returns_typed_streams() -> None:
    info = parse_probe_data(
        {
            "format": {
                "filename": "sample.mp4",
                "format_name": "mov,mp4",
                "duration": "2.500000",
                "size": "1000",
                "tags": {"title": "Sample"},
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30000/1001",
                    "time_base": "1/90000",
                },
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                },
            ],
        }
    )

    assert info.duration == 2.5
    assert info.video_streams[0].width == 1920
    assert info.video_streams[0].average_frame_rate == Rational(30000, 1001)
    assert isinstance(info.audio_streams[0], AudioStreamInfo)
    assert info.audio_streams[0].sample_rate == 48000
    assert info.format is not None
    assert info.format.tags == (("title", "Sample"),)


def test_unknown_stream_fields_remain_optional() -> None:
    info = parse_probe_data(
        {"streams": [{"index": 0, "codec_type": "video", "width": "N/A"}]}
    )

    assert info.format is None
    assert info.video_streams[0].width is None
    assert info.video_streams[0].time_base is None


def test_invalid_stream_collection_is_rejected() -> None:
    with pytest.raises(ProbeError, match="streams must be a list"):
        parse_probe_data({"streams": {"index": 0}})


def test_missing_probe_binary_has_specific_error() -> None:
    with pytest.raises(BinaryNotFoundError, match="was not found"):
        probe("sample.mp4", ffprobe="missing-flowmpeg-ffprobe")


def test_unusable_probe_binary_has_specific_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_start(*args: object, **kwargs: object) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(subprocess, "run", deny_start)

    with pytest.raises(BinaryUnusableError, match="could not be started"):
        probe_raw("sample.mp4", ffprobe="blocked-ffprobe")


@pytest.mark.integration
def test_probe_reads_generated_media(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("FFmpeg and FFprobe are required")

    target = tmp_path / "tone.wav"
    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.1",
            str(target),
        ),
        check=True,
    )

    info = probe(target, ffprobe=ffprobe)

    assert info.audio_streams[0].sample_rate == 44100
