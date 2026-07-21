from __future__ import annotations

import subprocess

import pytest

from flowmpeg.ui.readiness import (
    SystemReadiness,
    ToolReadiness,
    ToolState,
    check_readiness,
    check_tool,
)


def test_tool_readiness_reports_ready_state() -> None:
    tool = ToolReadiness("ffmpeg", ToolState.READY, path="ffmpeg")

    assert tool.ready is True


def test_system_readiness_requires_both_tools() -> None:
    ready = ToolReadiness("ffmpeg", ToolState.READY)
    missing = ToolReadiness("ffprobe", ToolState.MISSING)

    assert SystemReadiness(ready, ready).ready is True
    assert SystemReadiness(ready, missing).ready is False


def test_check_tool_reports_missing_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("flowmpeg.ui.readiness.shutil.which", lambda value: None)

    result = check_tool("ffmpeg")

    assert result == ToolReadiness("ffmpeg", ToolState.MISSING)


def test_check_tool_keeps_the_version_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("flowmpeg.ui.readiness.shutil.which", lambda value: value)
    monkeypatch.setattr(
        "flowmpeg.ui.readiness.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="ffmpeg version 8.0\nconfiguration", stderr=""
        ),
    )

    result = check_tool("ffmpeg")

    assert result.state is ToolState.READY
    assert result.version == "ffmpeg version 8.0"


def test_check_tool_reports_nonzero_version_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("flowmpeg.ui.readiness.shutil.which", lambda value: value)
    monkeypatch.setattr(
        "flowmpeg.ui.readiness.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="", stderr="cannot start"
        ),
    )

    result = check_tool("ffmpeg")

    assert result.state is ToolState.UNUSABLE
    assert result.reason == "cannot start"


def test_check_tool_reports_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise subprocess.TimeoutExpired(("ffmpeg",), 2)

    monkeypatch.setattr("flowmpeg.ui.readiness.shutil.which", lambda value: value)
    monkeypatch.setattr("flowmpeg.ui.readiness.subprocess.run", timeout)

    result = check_tool("ffmpeg", timeout=2)

    assert result.state is ToolState.TIMEOUT
    assert result.reason == "Version check exceeded 2 seconds"


def test_check_readiness_checks_the_media_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[tuple[str, float]] = []

    def check(name: str, timeout: float) -> ToolReadiness:
        checked.append((name, timeout))
        return ToolReadiness(name, ToolState.READY)

    monkeypatch.setattr("flowmpeg.ui.readiness.check_tool", check)

    result = check_readiness(timeout=4)

    assert result.ready is True
    assert checked == [("ffmpeg", 4), ("ffprobe", 4)]
