from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest

from flowmpeg import (
    BatchJob,
    BatchWorkspace,
    CancellationToken,
    ExecutionError,
    JobCancelledError,
    Progress,
    input,
    output,
    run_batch,
    shortcuts,
)
from flowmpeg.plan import Plan
from flowmpeg.runner import RunResult


def _plan(name: str) -> Plan:
    return output(input(f"{name}.mp4").video(), to=f"{name}-out.mp4")


def _result(name: str, elapsed: float = 0.2) -> RunResult:
    return RunResult(0, elapsed, "", None, (f"{name}-out.mp4",))


def test_batch_runs_jobs_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    reported: list[str] = []

    def run(self: Plan, **kwargs: object) -> RunResult:
        name = self.graph.inputs[0].source.removesuffix(".mp4")
        called.append(name)
        callback = kwargs["on_progress"]
        assert callable(callback)
        callback(Progress(None, None, None, None, None, None, "end", ()))
        return _result(name)

    monkeypatch.setattr(Plan, "run", run)
    jobs = (BatchJob("one", _plan("one")), BatchJob("two", _plan("two")))

    result = run_batch(
        jobs,
        on_progress=lambda job, event: reported.append(f"{job.name}:{event.state}"),
    )

    assert called == ["one", "two"]
    assert reported == ["one:end", "two:end"]
    assert [item.status for item in result.items] == ["completed", "completed"]
    assert result.completed == 2
    assert result.failed == 0
    assert result.cancelled == 0
    assert result.skipped == 0
    assert result.ok


def test_batch_stops_and_skips_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states: list[str] = []

    def run(self: Plan, **kwargs: object) -> RunResult:
        del kwargs
        name = self.graph.inputs[0].source.removesuffix(".mp4")
        if name == "broken":
            raise ExecutionError(
                "FFmpeg failed",
                returncode=1,
                stderr="failure",
                command="ffmpeg",
            )
        return _result(name)

    monkeypatch.setattr(Plan, "run", run)
    jobs = (
        BatchJob("one", _plan("one")),
        BatchJob("broken", _plan("broken")),
        BatchJob("three", _plan("three")),
    )

    result = run_batch(jobs, on_item=lambda item: states.append(item.status))

    assert states == ["completed", "failed", "skipped"]
    assert result.failed == 1
    assert result.skipped == 1
    assert not result.ok


def test_batch_can_continue_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(self: Plan, **kwargs: object) -> RunResult:
        del kwargs
        name = self.graph.inputs[0].source.removesuffix(".mp4")
        if name == "broken":
            raise ExecutionError(
                "FFmpeg failed",
                returncode=1,
                stderr="failure",
                command="ffmpeg",
            )
        return _result(name)

    monkeypatch.setattr(Plan, "run", run)
    jobs = (BatchJob("broken", _plan("broken")), BatchJob("two", _plan("two")))

    result = run_batch(jobs, continue_on_error=True)

    assert [item.status for item in result.items] == ["failed", "completed"]
    assert result.completed == 1
    assert result.failed == 1


def test_batch_marks_all_jobs_cancelled_before_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = CancellationToken()
    token.cancel()
    states: list[str] = []
    monkeypatch.setattr(
        Plan,
        "run",
        lambda *args, **kwargs: pytest.fail("A cancelled batch must not run jobs"),
    )

    result = run_batch(
        (BatchJob("one", _plan("one")), BatchJob("two", _plan("two"))),
        token=token,
        on_item=lambda item: states.append(item.status),
    )

    assert result.cancelled == 2
    assert [item.status for item in result.items] == ["cancelled", "cancelled"]
    assert states == ["cancelled", "cancelled"]


def test_batch_cancels_current_and_remaining_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = CancellationToken()

    def run(self: Plan, **kwargs: object) -> RunResult:
        del self, kwargs
        token.cancel()
        raise JobCancelledError("FFmpeg job was cancelled")

    monkeypatch.setattr(Plan, "run", run)
    jobs = (BatchJob("one", _plan("one")), BatchJob("two", _plan("two")))

    result = run_batch(jobs, token=token)

    assert result.cancelled == 2
    assert result.items[0].error == "FFmpeg job was cancelled"
    assert result.items[0].error_type == "JobCancelledError"
    assert result.items[1].error is None


@pytest.mark.parametrize("value", ["", "   ", 12])
def test_batch_job_rejects_invalid_name(value: object) -> None:
    with pytest.raises(ValueError, match="names cannot be empty"):
        BatchJob(cast(str, value), _plan("one"))


@pytest.mark.parametrize("value", [0, -1, True, float("inf")])
def test_batch_job_rejects_invalid_limits(value: object) -> None:
    with pytest.raises(ValueError, match="positive and finite"):
        BatchJob("one", _plan("one"), timeout=cast(float, value))


def test_batch_rejects_empty_and_duplicate_jobs() -> None:
    with pytest.raises(ValueError, match="at least one"):
        run_batch(())
    with pytest.raises(ValueError, match="names must be unique"):
        run_batch((BatchJob("one", _plan("one")), BatchJob("one", _plan("two"))))


def test_workspace_allocates_contained_paths(tmp_path: Path) -> None:
    with BatchWorkspace(tmp_path) as workspace:
        root = workspace.root
        target = workspace.allocate("stage/intermediate.mp4")
        target.write_text("temporary", encoding="utf-8")

        assert target.parent.is_dir()
        assert target.is_relative_to(root)

    assert not root.exists()


def test_workspace_cleans_after_an_error(tmp_path: Path) -> None:
    root: Path | None = None

    with (
        pytest.raises(RuntimeError, match="stop"),
        BatchWorkspace(tmp_path) as workspace,
    ):
        root = workspace.root
        workspace.allocate("partial.bin").write_bytes(b"partial")
        raise RuntimeError("stop")

    assert root is not None
    assert not root.exists()


@pytest.mark.parametrize("value", ["../outside.mp4", "folder/../../outside.mp4"])
def test_workspace_rejects_parent_escape(tmp_path: Path, value: str) -> None:
    with (
        BatchWorkspace(tmp_path) as workspace,
        pytest.raises(ValueError, match="stay under"),
    ):
        workspace.path(value)


def test_workspace_rejects_use_after_cleanup(tmp_path: Path) -> None:
    workspace = BatchWorkspace(tmp_path)
    workspace.cleanup()

    with pytest.raises(RuntimeError, match="closed"):
        _ = workspace.root


@pytest.mark.integration
def test_batch_runs_generated_videos(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("FFmpeg and FFprobe are required")
    sources = (tmp_path / "one.mov", tmp_path / "two.mov")
    for index, source in enumerate(sources, start=1):
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
                f"color=c=0x{index}{index}{index}{index}{index}{index}:s=32x32:d=0.2",
                "-c:v",
                "mpeg4",
                str(source),
            ),
            check=True,
        )
    targets = (tmp_path / "one.mp4", tmp_path / "two.mp4")
    jobs = tuple(
        BatchJob(source.name, shortcuts.transcode(source, target, include_audio=False))
        for source, target in zip(sources, targets, strict=True)
    )

    result = run_batch(jobs, ffmpeg=ffmpeg, ffprobe=ffprobe)

    assert result.ok
    assert result.completed == 2
    assert all(target.is_file() for target in targets)
