from flowmpeg import compare_media_info
from flowmpeg.probe import parse_probe_data


def test_media_comparison_reports_measured_changes() -> None:
    before = parse_probe_data(
        {
            "format": {"duration": "10", "size": "1000", "bit_rate": "800"},
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                },
                {"index": 1, "codec_type": "audio", "codec_name": "aac"},
                {"index": 2, "codec_type": "subtitle", "codec_name": "mov_text"},
            ],
        }
    )
    after = parse_probe_data(
        {
            "format": {"duration": "9.5", "size": "600", "bit_rate": "500"},
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "24000/1001",
                },
                {"index": 1, "codec_type": "audio", "codec_name": "aac"},
            ],
        }
    )

    result = compare_media_info("before.mp4", before, "after.mp4", after)

    assert result.size_delta == -400
    assert result.size_change_percent == -40
    assert result.duration_delta == -0.5
    assert result.before.video_codec == "h264"
    assert result.after.video_codec == "hevc"
    assert result.after.width == 1280
    assert result.after.frame_rate == 24000 / 1001
    assert result.before.subtitle_streams == 1
    assert result.after.subtitle_streams == 0


def test_media_comparison_keeps_unknown_deltas_empty() -> None:
    unknown = parse_probe_data({"streams": []})

    result = compare_media_info("one", unknown, "two", unknown)

    assert result.size_delta is None
    assert result.size_change_percent is None
    assert result.duration_delta is None
