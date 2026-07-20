import shutil
import subprocess
from pathlib import Path

import pytest

from flowmpeg.audit import AUDIT_CODES, AuditConstraints, audit_media
from flowmpeg.probe import (
    AudioStreamInfo,
    FormatInfo,
    MediaInfo,
    Rational,
    VideoStreamInfo,
    probe,
)


def _video(*, width: int = 1920, height: int = 1080) -> VideoStreamInfo:
    return VideoStreamInfo(
        index=0,
        codec_type="video",
        codec_name="h264",
        codec_long_name=None,
        duration=2,
        time_base=Rational(1, 1000),
        width=width,
        height=height,
        pixel_format="yuv420p",
        average_frame_rate=Rational(30, 1),
        sample_aspect_ratio=Rational(1, 1),
    )


def _audio() -> AudioStreamInfo:
    return AudioStreamInfo(
        index=1,
        codec_type="audio",
        codec_name="aac",
        codec_long_name=None,
        duration=2,
        time_base=Rational(1, 48_000),
        sample_rate=48_000,
        channels=2,
        channel_layout="stereo",
        sample_format="fltp",
    )


def _media(*streams: VideoStreamInfo | AudioStreamInfo) -> MediaInfo:
    return MediaInfo(
        FormatInfo(
            filename="input.mp4",
            format_name="mov,mp4",
            format_long_name="QuickTime / MOV",
            duration=2,
            size=1000,
            bit_rate=4000,
        ),
        streams,
    )


def test_audit_accepts_complete_audio_video_media() -> None:
    result = audit_media(_media(_video(), _audio()), expect="av")

    assert result.passes()
    assert result.findings == ()
    assert result.summary.video_streams == 1
    assert result.summary.audio_streams == 1
    assert result.summary.frame_rate == 30
    assert len(AUDIT_CODES) == 20


def test_audit_finds_missing_audio_and_odd_dimensions() -> None:
    result = audit_media(_media(_video(width=1279)), expect="av")

    assert {item.code for item in result.findings} == {"AUD102", "AUD213"}
    assert not result.passes("error")
    assert not result.passes("warning")
    assert result.passes("never")


def test_audit_warns_when_probe_fields_are_incomplete() -> None:
    result = audit_media(MediaInfo(None, ()), expect="any")

    assert {item.code for item in result.findings} == {
        "AUD001",
        "AUD201",
        "AUD202",
    }


def test_audit_rejects_unknown_policy_values() -> None:
    result = audit_media(_media(_audio()), expect="audio")

    with pytest.raises(ValueError, match="threshold"):
        result.passes("all")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="expectation"):
        audit_media(_media(_audio()), expect="pictures")  # type: ignore[arg-type]


def test_audit_accepts_matching_delivery_constraints() -> None:
    constraints = AuditConstraints(
        minimum_duration=1,
        maximum_duration=3,
        width=1920,
        height=1080,
        video_codec="H264",
        audio_codec="AAC",
        sample_rate=48_000,
        channels=2,
    )

    result = audit_media(
        _media(_video(), _audio()), expect="av", constraints=constraints
    )

    assert result.passes()
    assert result.findings == ()
    assert result.constraints == constraints


def test_audit_reports_delivery_constraint_mismatches() -> None:
    constraints = AuditConstraints(
        maximum_duration=1,
        width=1280,
        height=720,
        video_codec="hevc",
        audio_codec="opus",
        sample_rate=44_100,
        channels=1,
    )

    result = audit_media(_media(_video(), _audio()), constraints=constraints)

    assert {item.code for item in result.findings} == {
        "AUD204",
        "AUD215",
        "AUD216",
        "AUD217",
        "AUD224",
        "AUD225",
        "AUD226",
    }
    assert not result.passes()
    assert "expected hevc" in next(
        item.message for item in result.findings if item.code == "AUD217"
    )


def test_audit_fails_when_minimum_duration_is_not_met() -> None:
    result = audit_media(
        _media(_video()),
        constraints=AuditConstraints(minimum_duration=3),
    )

    assert "AUD203" in {item.code for item in result.findings}


@pytest.mark.parametrize(
    "constraints",
    [
        AuditConstraints(minimum_duration=0),
        AuditConstraints(maximum_duration=float("nan")),
        AuditConstraints(minimum_duration=3, maximum_duration=2),
        AuditConstraints(width=True),
        AuditConstraints(channels=0),
        AuditConstraints(video_codec=""),
    ],
)
def test_audit_rejects_invalid_constraints(constraints: AuditConstraints) -> None:
    with pytest.raises(ValueError, match="Audit"):
        audit_media(_media(_video()), constraints=constraints)


@pytest.mark.integration
def test_audit_accepts_generated_audio_video_media(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg and FFprobe are required")
    source = tmp_path / "audit.mp4"
    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=32x24:rate=10:duration=0.2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.2",
            "-shortest",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(source),
        ),
        check=True,
    )

    result = audit_media(probe(source), expect="av")

    assert result.passes("warning")
    assert result.findings == ()
