from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from flowmpeg import GraphError, input, output
from flowmpeg.model import StreamKind
from flowmpeg.plan import Plan
from flowmpeg.runner import RunResult


def _conditional_plan() -> tuple[Plan, Plan]:
    source = input("movie.mp4")
    primary = output(source.audio(), to="out.mp4")
    fallback = output(source.video(), to="out.mp4")
    return primary.with_missing_audio_fallback(fallback, "movie.mp4"), fallback


def test_missing_audio_selects_the_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, fallback = _conditional_plan()
    selected: list[Plan] = []
    probe_module = importlib.import_module("flowmpeg.probe")

    monkeypatch.setattr(
        probe_module,
        "probe",
        lambda *args, **kwargs: SimpleNamespace(audio_streams=()),
    )

    def run(value: Plan, **kwargs: object) -> RunResult:
        del kwargs
        selected.append(value)
        return RunResult(0, 0, "", None, ("out.mp4",))

    monkeypatch.setattr("flowmpeg.runner.run", run)

    plan.run(ffprobe="custom-ffprobe", probe_timeout=3)

    assert selected == [fallback]
    assert selected[0].outputs[0].streams[0].kind is StreamKind.VIDEO


def test_present_audio_selects_the_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _ = _conditional_plan()
    selected: list[Plan] = []
    probe_module = importlib.import_module("flowmpeg.probe")
    monkeypatch.setattr(
        probe_module,
        "probe",
        lambda *args, **kwargs: SimpleNamespace(audio_streams=(object(),)),
    )

    def run(value: Plan, **kwargs: object) -> RunResult:
        del kwargs
        selected.append(value)
        return RunResult(0, 0, "", None, ("out.mp4",))

    monkeypatch.setattr("flowmpeg.runner.run", run)

    plan.run()

    assert selected[0].missing_audio_fallback is None
    assert selected[0].outputs[0].streams[0].kind is StreamKind.AUDIO


def test_audio_fallback_state_follows_overwrite() -> None:
    plan, _ = _conditional_plan()

    changed = plan.overwrite()

    assert changed.overwrite_enabled
    assert changed.missing_audio_fallback is not None
    assert changed.missing_audio_fallback.overwrite_enabled


def test_audio_fallback_destinations_must_match() -> None:
    source = input("movie.mp4")
    primary = output(source.audio(), to="audio.mp4")
    fallback = output(source.video(), to="video.mp4")

    with pytest.raises(GraphError, match="destinations must match"):
        primary.with_missing_audio_fallback(fallback, "movie.mp4")
