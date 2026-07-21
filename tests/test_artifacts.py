from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from flowmpeg.artifacts import dash_package, frame_sequence, hls_package
from flowmpeg.errors import ExecutionError, GraphError, OutputExistsError
from flowmpeg.plan import Plan
from flowmpeg.runner import RunResult


def test_hls_plan_names_manifest_and_segments(tmp_path: Path) -> None:
    workflow = hls_package("input.mp4", tmp_path / "hls", segment_duration=5)

    plan = workflow.plan()
    argv = plan.raw_argv()

    assert Path(plan.outputs[0].destination).parts[-2:] == ("hls", "index.m3u8")
    assert "0:a:0?" in argv
    assert argv[argv.index("-hls_time") + 1] == "5"
    assert argv[argv.index("-hls_segment_filename") + 1] == "segment-%05d.ts"


def test_dash_plan_uses_template_names(tmp_path: Path) -> None:
    workflow = dash_package("input.mp4", tmp_path / "dash", include_audio=False)

    argv = workflow.plan().raw_argv()

    assert Path(argv[-1]).parts[-2:] == ("dash", "manifest.mpd")
    assert "0:a:0?" not in argv
    assert argv[argv.index("-init_seg_name") + 1] == "init-$RepresentationID$.m4s"
    assert (
        argv[argv.index("-media_seg_name") + 1]
        == "chunk-$RepresentationID$-$Number%05d$.m4s"
    )


def test_frame_plan_names_images_and_sampling(tmp_path: Path) -> None:
    workflow = frame_sequence(
        "input.mp4",
        tmp_path / "frames",
        interval=2.5,
        start=3,
        duration=10,
        width=640,
        max_frames=4,
    )

    plan = workflow.plan()
    argv = plan.raw_argv()

    assert Path(plan.outputs[0].destination).name == "frame-%06d.jpg"
    assert "-ss" in argv and argv[argv.index("-ss") + 1] == "3"
    assert "-t" in argv and argv[argv.index("-t") + 1] == "10"
    assert "fps=fps=0.4" in cast(str, plan.filter_graph())
    assert "scale=640:-2" in cast(str, plan.filter_graph())
    assert argv[argv.index("-frames:v") + 1] == "4"
    assert argv[argv.index("-q:v") + 1] == "2"


def test_frame_plan_accepts_rate_and_png(tmp_path: Path) -> None:
    workflow = frame_sequence(
        "input.mp4",
        tmp_path / "frames",
        fps=2,
        image_format="png",
    )

    plan = workflow.plan()

    assert Path(plan.outputs[0].destination).name == "frame-%06d.png"
    assert "fps=fps=2" in cast(str, plan.filter_graph())
    assert "-q:v" not in plan.raw_argv()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"segment_duration": 0},
        {"segment_duration": 3_601},
        {"crf": True},
        {"crf": 52},
        {"audio_bitrate": "free"},
        {"audio_bitrate": "0k"},
        {"include_audio": 1},
        {"overwrite": 1},
    ],
)
def test_artifact_workflow_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        hls_package("input.mp4", "delivery", **cast(Any, kwargs))


def test_artifact_workflow_rejects_nonlocal_output() -> None:
    with pytest.raises(GraphError, match="local filesystem"):
        hls_package("input.mp4", "https://example.com/hls")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"interval": 0},
        {"interval": 1, "fps": 1},
        {"fps": 241},
        {"start": -1},
        {"duration": 0},
        {"width": True},
        {"image_format": "gif"},
        {"quality": 32},
        {"max_frames": 0},
        {"overwrite": 1},
    ],
)
def test_frame_workflow_rejects_invalid_options(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphError):
        frame_sequence("input.mp4", "frames", **cast(Any, kwargs))


def test_frame_workflow_rejects_nonlocal_output() -> None:
    with pytest.raises(GraphError, match="local filesystem"):
        frame_sequence("input.mp4", "https://example.com/frames")


def test_artifact_workflow_publishes_owned_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hls"

    def run(plan: Plan, **kwargs: object) -> RunResult:
        del kwargs
        manifest = Path(plan.outputs[0].destination)
        manifest.write_text("#EXTM3U\n", encoding="utf-8")
        (manifest.parent / "segment-00000.ts").write_bytes(b"segment")
        return RunResult(0, 0.1, "", None, (str(manifest),))

    monkeypatch.setattr(Plan, "run", run)

    result = hls_package("input.mp4", target).run()

    assert result.manifest == str(target / "index.m3u8")
    assert result.files == (
        str(target / "index.m3u8"),
        str(target / "segment-00000.ts"),
    )
    marker = json.loads(
        (target / ".flowmpeg-artifacts.json").read_text(encoding="utf-8")
    )
    assert marker["kind"] == "hls"
    assert marker["files"] == ["index.m3u8", "segment-00000.ts"]


def test_frame_workflow_publishes_owned_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "frames"

    def run(plan: Plan, **kwargs: object) -> RunResult:
        del kwargs
        root = Path(plan.outputs[0].destination).parent
        (root / "frame-000001.jpg").write_bytes(b"one")
        (root / "frame-000002.jpg").write_bytes(b"two")
        return RunResult(0, 0.1, "", None, (plan.outputs[0].destination,))

    monkeypatch.setattr(Plan, "run", run)

    result = frame_sequence("input.mp4", target).run()

    assert result.pattern == "frame-%06d.jpg"
    assert result.files == (
        str(target / "frame-000001.jpg"),
        str(target / "frame-000002.jpg"),
    )
    assert result.encoding.outputs == result.files
    marker = json.loads(
        (target / ".flowmpeg-artifacts.json").read_text(encoding="utf-8")
    )
    assert marker["kind"] == "frames"
    assert marker["pattern"] == "frame-%06d.jpg"


def test_artifact_failure_removes_created_partial_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hls"

    def fail(plan: Plan, **kwargs: object) -> RunResult:
        del kwargs
        manifest = Path(plan.outputs[0].destination)
        (manifest.parent / "partial.ts").write_bytes(b"partial")
        raise ExecutionError(
            "failed",
            returncode=1,
            stderr="failed",
            command="ffmpeg",
        )

    monkeypatch.setattr(Plan, "run", fail)

    with pytest.raises(ExecutionError):
        hls_package("input.mp4", target).run()
    assert not target.exists()


def test_frame_failure_removes_created_partial_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "frames"

    def fail(plan: Plan, **kwargs: object) -> RunResult:
        del kwargs
        root = Path(plan.outputs[0].destination).parent
        (root / "frame-000001.jpg").write_bytes(b"partial")
        raise ExecutionError(
            "failed",
            returncode=1,
            stderr="failed",
            command="ffmpeg",
        )

    monkeypatch.setattr(Plan, "run", fail)

    with pytest.raises(ExecutionError):
        frame_sequence("input.mp4", target).run()
    assert not target.exists()


def test_artifact_workflow_refuses_unowned_directory(tmp_path: Path) -> None:
    target = tmp_path / "hls"
    target.mkdir()
    (target / "personal.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(OutputExistsError, match="not Flowmpeg-owned"):
        hls_package("input.mp4", target, overwrite=True).run()

    assert (target / "personal.txt").read_text(encoding="utf-8") == "keep"


def test_frame_workflow_refuses_unowned_directory(tmp_path: Path) -> None:
    target = tmp_path / "frames"
    target.mkdir()
    (target / "personal.jpg").write_bytes(b"keep")

    with pytest.raises(OutputExistsError, match="not Flowmpeg-owned"):
        frame_sequence("input.mp4", target, overwrite=True).run()

    assert (target / "personal.jpg").read_bytes() == b"keep"


def test_owned_overwrite_stages_then_replaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hls"
    calls = 0

    def run(plan: Plan, **kwargs: object) -> RunResult:
        nonlocal calls
        del kwargs
        calls += 1
        manifest = Path(plan.outputs[0].destination)
        manifest.write_text("#EXTM3U\n", encoding="utf-8")
        name = "old.ts" if calls == 1 else "new.ts"
        (manifest.parent / name).write_bytes(name.encode())
        return RunResult(0, 0.1, "", None, (str(manifest),))

    monkeypatch.setattr(Plan, "run", run)

    hls_package("input.mp4", target).run()
    result = hls_package("input.mp4", target, overwrite=True).run()

    assert not (target / "old.ts").exists()
    assert (target / "new.ts").is_file()
    assert str(target / "new.ts") in result.files
    assert not tuple(tmp_path.glob(".hls.flowmpeg-*"))


def test_owned_frame_overwrite_stages_then_replaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "frames"
    calls = 0

    def run(plan: Plan, **kwargs: object) -> RunResult:
        nonlocal calls
        del kwargs
        calls += 1
        root = Path(plan.outputs[0].destination).parent
        name = "frame-000001.jpg" if calls == 1 else "frame-000002.jpg"
        (root / name).write_bytes(name.encode())
        return RunResult(0, 0.1, "", None, (plan.outputs[0].destination,))

    monkeypatch.setattr(Plan, "run", run)

    frame_sequence("input.mp4", target).run()
    result = frame_sequence("input.mp4", target, overwrite=True).run()

    assert not (target / "frame-000001.jpg").exists()
    assert (target / "frame-000002.jpg").is_file()
    assert result.files == (str(target / "frame-000002.jpg"),)
    assert not tuple(tmp_path.glob(".frames.flowmpeg-*"))


def test_owned_directory_kind_cannot_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "delivery"

    def run(plan: Plan, **kwargs: object) -> RunResult:
        del kwargs
        manifest = Path(plan.outputs[0].destination)
        manifest.write_text("#EXTM3U\n", encoding="utf-8")
        return RunResult(0, 0.1, "", None, (str(manifest),))

    monkeypatch.setattr(Plan, "run", run)
    hls_package("input.mp4", target).run()

    with pytest.raises(OutputExistsError, match="belongs to hls"):
        dash_package("input.mp4", target, overwrite=True).run()

    with pytest.raises(OutputExistsError, match="belongs to hls"):
        frame_sequence("input.mp4", target, overwrite=True).run()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("kind", "manifest_name", "suffix"),
    [
        ("hls", "index.m3u8", ".ts"),
        ("dash", "manifest.mpd", ".m4s"),
    ],
)
def test_segment_workflow_runs_on_generated_video(
    tmp_path: Path,
    kind: str,
    manifest_name: str,
    suffix: str,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "source.mp4"
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
            "testsrc2=size=128x128:rate=10:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(source),
        ),
        check=True,
    )
    target = tmp_path / kind
    workflow = (
        hls_package(source, target, segment_duration=0.5)
        if kind == "hls"
        else dash_package(source, target, segment_duration=0.5)
    )

    result = workflow.run(ffmpeg=ffmpeg, timeout=20)

    assert Path(result.manifest).name == manifest_name
    assert Path(result.manifest).is_file()
    assert any(Path(path).suffix == suffix for path in result.files)
    assert (target / ".flowmpeg-artifacts.json").is_file()


@pytest.mark.integration
def test_frame_workflow_runs_on_generated_video(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "source.mp4"
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
            "testsrc2=size=128x96:rate=10:duration=1",
            "-c:v",
            "libx264",
            str(source),
        ),
        check=True,
    )

    result = frame_sequence(
        source,
        tmp_path / "frames",
        interval=0.25,
        width=64,
        max_frames=3,
    ).run(ffmpeg=ffmpeg, timeout=20)

    assert len(result.files) == 3
    assert all(Path(path).is_file() for path in result.files)
    assert (tmp_path / "frames" / ".flowmpeg-artifacts.json").is_file()
