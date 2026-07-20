import shutil
from math import inf, nan
from pathlib import Path
from typing import cast

import pytest

from flowmpeg import (
    Clip,
    GraphError,
    concat_clips,
    input,
    media,
    output,
    stack_video,
)
from flowmpeg.recipes.video import (
    change_video_speed,
    named_overlay_position,
    overlay_video,
    scale,
    trim_video,
)


def test_clip_edits_video_and_keeps_audio() -> None:
    source = media("talk.mp4")
    logo = media("logo.png", audio=False)

    edited = (
        source.trim(start=2, end=12)
        .scale(width=1280)
        .overlay(
            logo,
            position="bottom-right",
            opacity=0.8,
        )
    )

    assert edited.audio is not None
    assert edited.video is not None
    graph = edited.output("edited.mp4").filter_graph()
    assert graph is not None
    assert "trim=start=2:end=12" in graph
    assert "scale=1280:-2" in graph
    assert "colorchannelmixer=aa=0.8" in graph
    assert "overlay=x=W-w-24:y=H-h-24" in graph


def test_stack_builds_grid_layout() -> None:
    streams = tuple(input(f"{index}.mp4").video() for index in range(4))

    grid = stack_video(*streams, columns=2)
    graph = output(grid, to="grid.mp4").filter_graph()

    assert graph is not None
    assert "xstack=inputs=4:layout=0_0|w0_0|0_h0|w2_h0:fill=black" in graph


def test_concat_keeps_paired_outputs() -> None:
    first = media("first.mp4")
    second = media("second.mp4")

    joined = concat_clips(first, second)
    graph = joined.output("joined.mp4").filter_graph()

    assert joined.video is not None
    assert joined.audio is not None
    assert graph is not None
    assert "concat=n=2:v=1:a=1" in graph


def test_web_preset_is_visible_in_argv() -> None:
    plan = media("talk.mp4").output("web.mp4", preset="web")

    assert plan.raw_argv()[-15:] == (
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "web.mp4",
    )


def test_direct_video_recipes_compose() -> None:
    background = trim_video(input("main.mp4").video(), end=5)
    foreground = scale(input("logo.png").video(), width=120)

    result = overlay_video(background, foreground, x=10, y=20)
    graph = output(result, to="overlay.mp4").filter_graph()

    assert graph is not None
    assert "trim=end=5" in graph
    assert "scale=120:-2" in graph
    assert "overlay=x=10:y=20" in graph


@pytest.mark.parametrize("value", [True, 1.5, "640", 0, -1])
def test_scale_requires_integer_dimensions(value: object) -> None:
    with pytest.raises(GraphError, match="positive integer"):
        scale(input("movie.mp4").video(), width=cast(int, value))


@pytest.mark.parametrize("value", [True, 1.5, "2", 0, -1])
def test_stack_requires_integer_columns(value: object) -> None:
    first = input("first.mp4").video()
    second = input("second.mp4").video()

    with pytest.raises(GraphError, match="positive integer"):
        stack_video(first, second, columns=cast(int, value))


@pytest.mark.parametrize("value", [True, 1.5, "24", -1])
def test_overlay_padding_requires_nonnegative_integer(value: object) -> None:
    with pytest.raises(GraphError, match="nonnegative integer"):
        named_overlay_position("top-left", padding=cast(int, value))


@pytest.mark.parametrize("value", [True, "1", inf, nan, 10**1_000])
def test_trim_rejects_nonfinite_numbers(value: object) -> None:
    with pytest.raises(GraphError, match="must be finite"):
        trim_video(input("movie.mp4").video(), start=cast(float, value))


@pytest.mark.parametrize("value", [True, "2", inf, nan, 10**1_000])
def test_video_speed_rejects_nonfinite_numbers(value: object) -> None:
    with pytest.raises(GraphError, match="must be finite"):
        change_video_speed(input("movie.mp4").video(), cast(float, value))


@pytest.mark.parametrize("value", [True, "1", inf, nan, 10**1_000])
def test_overlay_rejects_nonfinite_opacity(value: object) -> None:
    background = input("background.mp4").video()
    foreground = input("foreground.mp4").video()

    with pytest.raises(GraphError, match="must be finite"):
        overlay_video(background, foreground, opacity=cast(float, value))


@pytest.mark.integration
def test_overlay_runs_with_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")

    background = media(
        "color=blue:size=64x64:duration=0.2",
        "-f",
        "lavfi",
        audio=False,
    )
    foreground = media(
        "color=red:size=16x16:duration=0.2",
        "-f",
        "lavfi",
        audio=False,
    )
    target = tmp_path / "overlay.mp4"
    plan = background.overlay(
        foreground,
        position="center",
    ).output(
        target,
        preset="web",
    )

    result = plan.run(ffmpeg=ffmpeg, expected_duration=0.2, timeout=10)

    assert result.returncode == 0
    assert target.stat().st_size > 0


@pytest.mark.integration
def test_concat_runs_with_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")

    first = media(
        "color=blue:size=32x32:duration=0.1",
        "-f",
        "lavfi",
        audio=False,
    )
    second = media(
        "color=red:size=32x32:duration=0.1",
        "-f",
        "lavfi",
        audio=False,
    )
    target = tmp_path / "concat.mp4"
    plan = concat_clips(first, second).output(target, preset="web")

    result = plan.run(ffmpeg=ffmpeg, expected_duration=0.2, timeout=10)

    assert result.returncode == 0
    assert target.stat().st_size > 0


def test_clip_requires_at_least_one_stream() -> None:
    with pytest.raises(GraphError, match="require video or audio"):
        Clip()
