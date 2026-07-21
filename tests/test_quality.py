from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from flowmpeg import quality
from flowmpeg.errors import BinaryNotFoundError, ExecutionError, GraphError
from flowmpeg.probe import MediaInfo
from flowmpeg.quality import measure_quality

_PSNR = (
    "[Parsed_psnr_0] PSNR y:42.100000 u:44.200000 v:43.300000 "
    "average:42.700000 min:40.100000 max:45.900000\n"
)
_SSIM = (
    "[Parsed_ssim_0] SSIM Y:0.991000 (20.457000) U:0.995000 (23.010300) "
    "V:0.994000 (22.218500) All:0.993000 (21.549000)\n"
)
_VMAF = "[Parsed_libvmaf_0] VMAF score: 98.714706\n"


def _info(width: int = 1920, height: int = 1080) -> MediaInfo:
    video = SimpleNamespace(width=width, height=height)
    return cast(MediaInfo, SimpleNamespace(video_streams=(video,)))


def test_quality_measurement_returns_both_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(quality, "probe", lambda *args, **kwargs: _info())

    def run(
        argv: tuple[str, ...],
        *,
        timeout: float | None,
        activity: str,
    ) -> tuple[str, int]:
        del timeout, activity
        calls.append(argv)
        has_psnr = any("psnr=shortest=1" in value for value in argv)
        return (_PSNR if has_psnr else _SSIM), 0

    monkeypatch.setattr(quality, "run_ffmpeg_analysis", run)

    report = measure_quality(
        "reference.mp4",
        "candidate.mp4",
        start=2,
        duration=5,
    )

    assert report.width == 1920
    assert report.height == 1080
    assert report.start == 2
    assert report.duration == 5
    assert report.psnr is not None
    assert report.psnr.average_db == 42.7
    assert report.psnr.components[0].name == "y"
    assert report.ssim is not None
    assert report.ssim.all == 0.993
    assert report.ssim.db == 21.549
    assert report.vmaf is None
    assert len(calls) == 2
    for argv in calls:
        assert argv[argv.index("-i") + 1] == "candidate.mp4"
        second_input = argv.index("-i", argv.index("-i") + 1)
        assert argv[second_input + 1] == "reference.mp4"
        assert argv.count("-ss") == 2
        assert argv.count("-t") == 2


@pytest.mark.parametrize(
    ("metric", "expected_marker"),
    [
        ("psnr", "psnr=shortest=1"),
        ("ssim", "ssim=shortest=1"),
        ("vmaf", "libvmaf=shortest=1"),
    ],
)
def test_quality_measurement_can_select_one_metric(
    metric: str,
    expected_marker: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(quality, "probe", lambda *args, **kwargs: _info())

    def run(
        argv: tuple[str, ...],
        **kwargs: object,
    ) -> tuple[str, int]:
        del kwargs
        calls.append(argv)
        return {"psnr": _PSNR, "ssim": _SSIM, "vmaf": _VMAF}[metric], 0

    monkeypatch.setattr(quality, "run_ffmpeg_analysis", run)

    report = measure_quality(
        "reference.mp4",
        "candidate.mp4",
        metric=cast(Any, metric),
    )

    assert len(calls) == 1
    assert any(expected_marker in value for value in calls[0])
    assert (report.psnr is not None) is (metric == "psnr")
    assert (report.ssim is not None) is (metric == "ssim")
    assert (report.vmaf is not None) is (metric == "vmaf")


def test_quality_preserves_infinite_identical_scores() -> None:
    psnr = quality._parse_psnr("PSNR y:inf u:inf v:inf average:inf min:inf max:inf")
    ssim = quality._parse_ssim(
        "SSIM Y:1.000000 (inf) U:1.000000 (inf) V:1.000000 (inf) All:1.000000 (inf)"
    )

    assert psnr is not None and math.isinf(psnr.average_db)
    assert ssim is not None and ssim.all == 1
    assert math.isinf(ssim.db)


def test_quality_parser_accepts_rgb_components() -> None:
    psnr = quality._parse_psnr(
        "PSNR r:31.1 g:32.2 b:33.3 average:32.0 min:29.0 max:35.0"
    )

    assert psnr is not None
    assert [item.name for item in psnr.components] == ["r", "g", "b"]


def test_quality_parser_reads_vmaf_score() -> None:
    score = quality._parse_vmaf(_VMAF)

    assert score is not None
    assert score.score == 98.714706


def test_quality_rejects_mismatched_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter((_info(1920, 1080), _info(1280, 720)))
    monkeypatch.setattr(quality, "probe", lambda *args, **kwargs: next(values))

    with pytest.raises(GraphError, match="matching dimensions"):
        measure_quality("reference.mp4", "candidate.mp4")


def test_quality_rejects_missing_video_track(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(quality, "probe", lambda *args, **kwargs: _info())

    with pytest.raises(GraphError, match="track 1 does not exist"):
        measure_quality("reference.mp4", "candidate.mp4", candidate_track=1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"metric": "butter"},
        {"reference_track": -1},
        {"candidate_track": True},
        {"start": -1},
        {"duration": 0},
        {"timeout": float("inf")},
        {"probe_timeout": 0},
        {"ffmpeg": ""},
        {"ffprobe": ""},
    ],
)
def test_quality_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises((GraphError, BinaryNotFoundError)):
        measure_quality("reference.mp4", "candidate.mp4", **cast(Any, kwargs))


def test_quality_raises_structured_ffmpeg_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(quality, "probe", lambda *args, **kwargs: _info())
    monkeypatch.setattr(
        quality,
        "run_ffmpeg_analysis",
        lambda *args, **kwargs: ("No such filter: psnr", 1),
    )

    with pytest.raises(ExecutionError) as captured:
        measure_quality("reference.mp4", "candidate.mp4", metric="psnr")

    assert captured.value.returncode == 1
    assert "No such filter" in captured.value.stderr
    assert "psnr=shortest=1" in captured.value.command


def test_quality_rejects_missing_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(quality, "probe", lambda *args, **kwargs: _info())
    monkeypatch.setattr(
        quality,
        "run_ffmpeg_analysis",
        lambda *args, **kwargs: ("No summary", 0),
    )

    with pytest.raises(ExecutionError, match="did not return PSNR") as captured:
        measure_quality("reference.mp4", "candidate.mp4", metric="psnr")

    assert captured.value.returncode == 0


@pytest.mark.integration
def test_quality_measurement_runs_on_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("FFmpeg and FFprobe are required")
    reference = tmp_path / "reference.mkv"
    candidate = tmp_path / "candidate.mkv"
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
            "testsrc2=size=96x64:rate=10:duration=1",
            "-c:v",
            "ffv1",
            str(reference),
        ),
        check=True,
    )
    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(reference),
            "-vf",
            "eq=brightness=0.03",
            "-c:v",
            "ffv1",
            str(candidate),
        ),
        check=True,
    )

    report = measure_quality(
        reference,
        candidate,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        timeout=20,
    )

    assert report.psnr is not None
    assert 10 < report.psnr.average_db < math.inf
    assert report.ssim is not None
    assert 0 < report.ssim.all < 1


@pytest.mark.integration
def test_vmaf_measurement_runs_when_filter_is_available(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("FFmpeg and FFprobe are required")
    filters = subprocess.run(
        (ffmpeg, "-hide_banner", "-filters"),
        check=True,
        capture_output=True,
        text=True,
    )
    if "libvmaf" not in filters.stdout:
        pytest.skip("The libvmaf filter is not available")
    reference = tmp_path / "reference.mkv"
    candidate = tmp_path / "candidate.mkv"
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
            "testsrc2=size=96x64:rate=10:duration=0.4",
            "-c:v",
            "ffv1",
            str(reference),
        ),
        check=True,
    )
    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(reference),
            "-vf",
            "eq=brightness=0.03",
            "-c:v",
            "ffv1",
            str(candidate),
        ),
        check=True,
    )

    report = measure_quality(
        reference,
        candidate,
        metric="vmaf",
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        timeout=20,
    )

    assert report.vmaf is not None
    assert report.vmaf.score > 0
