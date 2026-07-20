from __future__ import annotations

import json
import platform
import shlex
import shutil
import subprocess
import sys
from datetime import timedelta
from importlib.metadata import entry_points
from io import StringIO

import pytest

from flowmpeg import cli, diagnostics
from flowmpeg.catalog import COMMAND_CATALOG
from flowmpeg.errors import (
    BinaryNotFoundError,
    BinaryUnusableError,
    CompilationError,
    ExecutionError,
    FlowmpegError,
    JobTimeoutError,
    OutputExistsError,
    ProbeError,
)
from flowmpeg.plan import Plan
from flowmpeg.probe import (
    AudioStreamInfo,
    FormatInfo,
    MediaInfo,
    VideoStreamInfo,
)
from flowmpeg.progress import Progress
from flowmpeg.runner import RunResult


@pytest.mark.parametrize(
    "arguments",
    [
        ["transcode", "in.mov", "-o", "out.mp4"],
        ["trim", "in.mp4", "--start", "2", "--duration", "5", "-o", "out.mp4"],
        ["resize", "in.mp4", "--width", "640", "-o", "out.mp4"],
        ["remove-audio", "in.mp4", "-o", "out.mp4"],
        ["extract-audio", "in.mp4", "-o", "out.mp3"],
        ["replace-audio", "in.mp4", "music.wav", "-o", "out.mp4"],
        ["watermark", "in.mp4", "mark.png", "-o", "out.mp4"],
        ["add-music", "in.mp4", "music.mp3", "-o", "out.mp4"],
        ["join-matching", "one.mp4", "two.mp4", "-o", "out.mp4"],
        ["mix-audio", "one.wav", "two.wav", "-o", "out.wav"],
        ["grid", "one.mp4", "two.mp4", "-o", "out.mp4"],
        ["thumbnail", "in.mp4", "-o", "out.jpg"],
        ["make-gif", "in.mp4", "-o", "out.gif"],
        ["rotate", "in.mp4", "-o", "out.mp4"],
        ["crop", "in.mp4", "--width", "320", "--height", "180", "-o", "out.mp4"],
        ["change-speed", "in.mp4", "--factor", "1.5", "-o", "out.mp4"],
        ["normalize-loudness", "in.wav", "-o", "out.wav"],
        ["fit-canvas", "in.mp4", "-o", "out.mp4"],
        ["picture-in-picture", "main.mp4", "inset.mp4", "-o", "out.mp4"],
        ["waveform-image", "in.mp3", "-o", "out.png"],
        ["spectrum-image", "in.mp3", "-o", "out.png"],
        ["still-image-video", "cover.jpg", "in.mp3", "-o", "out.mp4"],
        ["contact-sheet", "in.mp4", "-o", "out.jpg"],
        ["duck-music", "in.mp4", "music.mp3", "-o", "out.mp4"],
        ["fade-edges", "in.mp4", "--duration", "8", "-o", "out.mp4"],
        ["blurred-background", "in.mp4", "-o", "out.mp4"],
        ["reverse-clip", "in.mp4", "--duration", "5", "-o", "out.mp4"],
        ["compress-video", "in.mov", "-o", "out.mp4"],
        ["reframe", "in.mp4", "-o", "out.mp4"],
        ["social-video", "in.mp4", "-o", "out.mp4"],
        ["set-frame-rate", "in.mp4", "-o", "out.mp4"],
        ["deinterlace", "in.mp4", "-o", "out.mp4"],
        ["flip-video", "in.mp4", "-o", "out.mp4"],
        ["adjust-colors", "in.mp4", "-o", "out.mp4"],
        ["sharpen", "in.mp4", "-o", "out.mp4"],
        ["freeze-end", "in.mp4", "-o", "out.mp4"],
        [
            "mute-section",
            "in.mp4",
            "--start",
            "1",
            "--end",
            "2",
            "-o",
            "out.mp4",
        ],
        [
            "blur-region",
            "in.mp4",
            "--x",
            "0",
            "--y",
            "0",
            "--width",
            "100",
            "--height",
            "100",
            "-o",
            "out.mp4",
        ],
        ["boomerang", "in.mp4", "--duration", "2", "-o", "out.mp4"],
        ["denoise-audio", "in.wav", "-o", "out.wav"],
        ["compress-audio", "in.wav", "-o", "out.wav"],
        ["podcast-voice", "in.wav", "-o", "out.wav"],
        ["trim-silence", "in.wav", "-o", "out.wav"],
        ["mono-audio", "in.wav", "-o", "out.wav"],
        ["crossfade-audio", "one.wav", "two.wav", "-o", "out.wav"],
        ["extract-subtitles", "in.mkv", "-o", "out.srt"],
        ["add-subtitles", "in.mp4", "captions.srt", "-o", "out.mp4"],
        ["remove-subtitles", "in.mkv", "-o", "out.mp4"],
        ["image-sequence-video", "frame-%04d.png", "-o", "out.mp4"],
        ["podcast-audiogram", "in.wav", "cover.jpg", "-o", "out.mp4"],
        ["strip-metadata", "in.mkv", "-o", "out.mkv"],
        ["tag-audio", "in.m4a", "--title", "Episode 1", "-o", "out.m4a"],
    ],
)
def test_every_media_command_builds_a_dry_run(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main([*arguments, "--dry-run"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.startswith("ffmpeg ")
    assert captured.err == ""


@pytest.mark.parametrize(
    "arguments",
    [
        ["convert", "in.mov", "-o", "out.mp4"],
        ["cut", "in.mp4", "--duration", "2", "-o", "out.mp4"],
        ["mute", "in.mp4", "-o", "out.mp4"],
        ["strip-audio", "in.mp4", "-o", "out.mp4"],
        ["audio", "in.mp4", "-o", "out.mp3"],
        ["pip", "main.mp4", "inset.mp4", "-o", "out.mp4"],
        ["gif", "in.mp4", "-o", "out.gif"],
        ["waveform", "in.mp3", "-o", "out.png"],
        ["spectrum", "in.mp3", "-o", "out.png"],
        ["sheet", "in.mp4", "-o", "out.jpg"],
        ["reverse", "in.mp4", "--duration", "2", "-o", "out.mp4"],
        ["mix-audio-files", "one.wav", "two.wav", "-o", "out.wav"],
        ["compress", "in.mov", "-o", "out.mp4"],
        ["social", "in.mp4", "-o", "out.mp4"],
        ["fps", "in.mp4", "-o", "out.mp4"],
        ["mirror", "in.mp4", "-o", "out.mp4"],
        ["color", "in.mp4", "-o", "out.mp4"],
        ["freeze", "in.mp4", "-o", "out.mp4"],
        [
            "privacy-blur",
            "in.mp4",
            "--x",
            "0",
            "--y",
            "0",
            "--width",
            "100",
            "--height",
            "100",
            "-o",
            "out.mp4",
        ],
        ["bounce", "in.mp4", "--duration", "2", "-o", "out.mp4"],
        ["denoise", "in.wav", "-o", "out.wav"],
        ["voice", "in.wav", "-o", "out.wav"],
        ["mono", "in.wav", "-o", "out.wav"],
        ["crossfade", "one.wav", "two.wav", "-o", "out.wav"],
        ["captions", "in.mp4", "captions.srt", "-o", "out.mp4"],
        ["timelapse", "frame-%04d.png", "-o", "out.mp4"],
        ["audiogram", "in.wav", "cover.jpg", "-o", "out.mp4"],
        ["clean-metadata", "in.mkv", "-o", "out.mkv"],
        ["tag", "in.m4a", "--title", "Episode 1", "-o", "out.m4a"],
    ],
)
def test_short_aliases_build_the_same_kind_of_plan(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([*arguments, "--dry-run"]) == 0
    assert capsys.readouterr().out.startswith("ffmpeg ")


def test_dry_run_does_not_start_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_run(self: Plan, **kwargs: object) -> RunResult:
        del self, kwargs
        raise AssertionError("Plan.run was called")

    monkeypatch.setattr(Plan, "run", fail_run)

    code = cli.main(["mute", "in.mp4", "-o", "out.mp4", "--dry-run"])

    assert code == 0
    assert "-c:v copy" in capsys.readouterr().out


def test_media_command_runs_and_reports_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    received: dict[str, object] = {}

    def fake_run(self: Plan, **kwargs: object) -> RunResult:
        received.update(kwargs)
        return RunResult(0, 1.25, "", None, (self.outputs[0].destination,))

    monkeypatch.setattr(Plan, "run", fake_run)

    code = cli.main(
        [
            "trim",
            "in.mp4",
            "--duration",
            "2",
            "-o",
            "out.mp4",
            "--ffmpeg",
            "custom-ffmpeg",
            "--timeout",
            "12",
            "--expected-duration",
            "2",
            "--no-progress",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "Finished in 1.25s: out.mp4\n"
    assert received == {
        "ffmpeg": "custom-ffmpeg",
        "on_progress": None,
        "expected_duration": 2.0,
        "timeout": 12.0,
    }


def test_finished_output_hides_url_secrets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(self: Plan, **kwargs: object) -> RunResult:
        del self, kwargs
        return RunResult(
            0,
            0.1,
            "",
            None,
            ("https://example.com/upload?token=REDACT_ME",),
        )

    monkeypatch.setattr(Plan, "run", fake_run)

    assert cli.main(["mute", "in.mp4", "-o", "out.mp4"]) == 0
    output = capsys.readouterr().out
    assert "REDACT_ME" not in output
    assert "token=<redacted>" in output


def test_known_duration_drives_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    def fake_run(self: Plan, **kwargs: object) -> RunResult:
        received.update(kwargs)
        return RunResult(0, 0.1, "", None, (self.outputs[0].destination,))

    monkeypatch.setattr(Plan, "run", fake_run)

    assert cli.main(["reverse", "in.mp4", "--duration", "4", "-o", "out.mp4"]) == 0
    assert received["expected_duration"] == 4.0


def test_rotate_accepts_270_degrees(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(
        ["rotate", "in.mp4", "--degrees", "270", "-o", "out.mp4", "--dry-run"]
    )

    assert code == 0
    assert "transpose=dir=cclock" in capsys.readouterr().out


def test_no_audio_drops_the_audio_mapping(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        cli.main(["transcode", "in.mov", "-o", "out.mp4", "--no-audio", "--dry-run"])
        == 0
    )
    assert "0:a:0" not in capsys.readouterr().out


def test_gif_full_omits_trim_filter(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["gif", "in.mp4", "--full", "-o", "out.gif", "--dry-run"]) == 0
    assert "trim=" not in capsys.readouterr().out


def test_gif_original_width_omits_scale(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        cli.main(
            [
                "gif",
                "in.mp4",
                "--original-width",
                "-o",
                "out.gif",
                "--dry-run",
            ]
        )
        == 0
    )
    assert "scale=" not in capsys.readouterr().out


def test_boolean_shortcut_options_reach_the_plan(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        cli.main(
            [
                "add-music",
                "silent.mp4",
                "music.mp3",
                "--no-source-audio",
                "-o",
                "out.mp4",
                "--dry-run",
            ]
        )
        == 0
    )
    assert "0:a:0" not in capsys.readouterr().out

    assert (
        cli.main(
            [
                "duck",
                "in.mp4",
                "music.mp3",
                "--no-loop-music",
                "-o",
                "out.mp4",
                "--dry-run",
            ]
        )
        == 0
    )
    assert "-stream_loop" not in capsys.readouterr().out

    assert (
        cli.main(
            [
                "add-music",
                "silent.mp4",
                "music.mp3",
                "--silent-source",
                "-o",
                "out.mp4",
                "--dry-run",
            ]
        )
        == 0
    )
    assert "0:a:0" not in capsys.readouterr().out


def test_overwrite_changes_the_ffmpeg_policy(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        cli.main(["mute", "in.mp4", "-o", "out.mp4", "--overwrite", "--dry-run"]) == 0
    )
    assert " -y " in capsys.readouterr().out


def test_explain_prints_plan_before_dry_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(
        [
            "resize",
            "in.mp4",
            "--width",
            "640",
            "-o",
            "out.mp4",
            "--dry-run",
            "--explain",
        ]
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "Inputs:" in output
    assert "Outputs:" in output
    assert output.rstrip().endswith("out.mp4")


def test_dry_run_hides_url_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(
        [
            "transcode",
            "https://example-user:REDACT_ME@example.com/live.mp4",
            "-o",
            "out.mp4",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "REDACT_ME" not in output
    assert "<redacted>@example.com" in output


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (CompilationError("bad compile"), 2),
        (BinaryNotFoundError("missing binary"), 3),
        (BinaryUnusableError("blocked binary"), 3),
        (OutputExistsError("output exists"), 4),
        (
            ExecutionError(
                "failed",
                returncode=1,
                stderr="failure",
                command="ffmpeg",
            ),
            6,
        ),
        (JobTimeoutError("too slow"), 7),
        (FlowmpegError("other failure"), 1),
    ],
)
def test_media_errors_have_stable_exit_codes(
    error: FlowmpegError,
    expected_code: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_run(self: Plan, **kwargs: object) -> RunResult:
        del self, kwargs
        raise error

    monkeypatch.setattr(Plan, "run", fail_run)

    code = cli.main(["mute", "in.mp4", "-o", "out.mp4"])

    assert code == expected_code
    captured = capsys.readouterr()
    if isinstance(error, ExecutionError):
        assert "FFmpeg exited with code 1" in captured.err
        assert "Reason: failure" in captured.err
    else:
        assert str(error) in captured.err
    assert "FMG" in captured.err
    if isinstance(error, BinaryUnusableError):
        assert "FMG302" in captured.err
    if isinstance(error, OutputExistsError):
        assert "--overwrite" in captured.err


def test_graph_error_returns_usage_code(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(
        [
            "fade",
            "in.mp4",
            "--duration",
            "1",
            "--fade-in",
            "1",
            "--fade-out",
            "1",
            "-o",
            "out.mp4",
        ]
    )

    assert code == 2
    assert "Combined fades" in capsys.readouterr().err


def test_probe_error_prints_one_bounded_reason(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = ProbeError(
        "FFprobe exited with code 1",
        returncode=1,
        stderr="x" * 2_000,
        command="ffprobe input.mp4",
    )
    monkeypatch.setattr(cli, "_run_probe", lambda args: (_ for _ in ()).throw(error))

    assert cli.main(["probe", "input.mp4"]) == 5
    captured = capsys.readouterr().err
    assert "FFprobe exited with code 1" in captured
    assert "Reason: " in captured
    assert len(captured) < 700


def test_ffmpeg_path_containing_probe_uses_ffmpeg_error_id(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = BinaryNotFoundError(
        "FFmpeg was not found: C:/probe-tools/ffmpeg.exe", tool="ffmpeg"
    )

    def fail_run(self: Plan, **kwargs: object) -> RunResult:
        del self, kwargs
        raise error

    monkeypatch.setattr(Plan, "run", fail_run)

    assert cli.main(["mute", "in.mp4", "-o", "out.mp4"]) == 3
    assert "FMG300" in capsys.readouterr().err


def test_shortcut_dash_input_returns_usage_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(["mute", "-", "-o", "out.mp4"])

    assert code == 2
    assert "start with a dash" in capsys.readouterr().err


def test_keyboard_interrupt_returns_130(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def interrupt(self: Plan, **kwargs: object) -> RunResult:
        del self, kwargs
        raise KeyboardInterrupt

    monkeypatch.setattr(Plan, "run", interrupt)

    assert cli.main(["mute", "in.mp4", "-o", "out.mp4"]) == 130
    assert "interrupted" in capsys.readouterr().err


def test_probe_human_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "probe", lambda *args, **kwargs: _media_info())

    code = cli.main(["probe", "movie.mp4"])

    output = capsys.readouterr().out
    assert code == 0
    assert "Container: QuickTime / MOV" in output
    assert "video #0: h264, 1920x1080" in output
    assert "audio #1: aac, 48000 Hz, 2 channel(s)" in output
    assert "REDACT_ME" not in output
    assert "<redacted>@example.com" in output


def test_probe_typed_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "probe", lambda *args, **kwargs: _media_info())

    assert cli.main(["probe", "movie.mp4", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["schema_version"] == 1
    assert data["format"]["duration"] == 12.5
    assert data["format"]["filename"] == "https://<redacted>@example.com/movie.mp4"
    assert data["streams"][0]["width"] == 1920


def test_probe_raw_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "probe_raw",
        lambda *args, **kwargs: {
            "format": {
                "filename": "https://example-user:REDACT_ME@example.com/movie.mp4"
            },
            "streams": [{"codec_type": "video"}],
        },
    )

    assert cli.main(["probe", "movie.mp4", "--raw"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["streams"][0]["codec_type"] == "video"
    assert data["format"]["filename"] == "https://<redacted>@example.com/movie.mp4"


def test_probe_error_returns_five(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_probe(*args: object, **kwargs: object) -> MediaInfo:
        raise ProbeError("cannot inspect input")

    monkeypatch.setattr(cli, "probe", fail_probe)

    assert cli.main(["probe", "movie.mp4"]) == 5
    assert "cannot inspect input" in capsys.readouterr().err


def test_doctor_json_reports_ready(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def tool_report(
        executable: str,
        timeout: float,
        expected_tool: str,
    ) -> dict[str, object]:
        del expected_tool
        return {"ok": True, "path": executable, "version": f"{executable} 1.0"}

    monkeypatch.setattr(cli, "_tool_report", tool_report)
    monkeypatch.setattr(
        cli, "_capability_report", lambda *args: {"filter:overlay": True}
    )

    assert cli.main(["doctor", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == 1
    assert report["ok"] is True
    assert report["flowmpeg_version"] == "0.1.0"
    assert report["python_version"]
    assert report["capabilities"]["filter:overlay"] is True


def test_doctor_returns_three_when_a_tool_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def tool_report(
        executable: str,
        timeout: float,
        expected_tool: str,
    ) -> dict[str, object]:
        del timeout, expected_tool
        return {"ok": executable == "ffmpeg", "path": executable, "version": None}

    monkeypatch.setattr(cli, "_tool_report", tool_report)
    monkeypatch.setattr(
        cli, "_capability_report", lambda *args: {"filter:overlay": True}
    )

    assert cli.main(["doctor"]) == 3
    output = capsys.readouterr().out
    assert "ffprobe: missing or unusable" in output
    assert "Core ready: no" in output


def test_doctor_marks_missing_feature_without_failing_core(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {"ok": True, "path": "tool", "version": "tool 1.0"},
    )
    monkeypatch.setattr(
        cli,
        "_capability_report",
        lambda *args: {"encoder:aac": True, "encoder:libx264": False},
    )

    assert cli.main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "web-video: limited" in output
    assert "Core ready: yes" in output


def test_doctor_checks_filters_and_ass_subtitles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[str] = []
    monkeypatch.setattr(cli, "_listing", lambda *args: "listing")

    def listing_has(listing: str, name: str) -> bool:
        del listing
        checked.append(name)
        return True

    monkeypatch.setattr(cli, "_listing_has", listing_has)

    report = cli._capability_report("ffmpeg", 1)

    for name in (
        "acrossfade",
        "adelay",
        "aformat",
        "asplit",
        "gblur",
        "ipod",
        "setsar",
        "yadif",
        "ass",
    ):
        assert name in checked
    assert report["encoder:ass"] is True


def test_failed_capability_listing_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_listing", lambda *args: None)

    report = cli._capability_report("ffmpeg", 1)
    features = cli._feature_report(report)

    assert report
    assert set(report.values()) == {None}
    assert set(features.values()) == {None}


def test_doctor_required_group_controls_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {"ok": True, "status": "ready", "path": "tool"},
    )
    monkeypatch.setattr(cli, "_capability_report", lambda *args: {})
    monkeypatch.setattr(
        cli,
        "_feature_report",
        lambda capabilities: {"web-video": False},
    )

    assert cli.main(["doctor", "--require", "web-video"]) == 3
    assert "Required group: web-video (limited)" in capsys.readouterr().out


def test_doctor_without_requirement_reports_null_state(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {"ok": True, "status": "ready", "path": "tool"},
    )
    monkeypatch.setattr(cli, "_capability_report", lambda *args: {})

    assert cli.main(["doctor", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["required_group"] is None
    assert report["required_ready"] is None


def test_setup_ready_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {
            "ok": True,
            "status": "ready",
            "path": "tool",
            "version": "tool 1.0",
        },
    )
    monkeypatch.setattr(cli, "_detect_installer", lambda: None)

    assert cli.main(["setup"]) == 0
    output = capsys.readouterr().out
    assert "FFmpeg and FFprobe are ready" in output
    assert "No changes were made" in output


def test_setup_checks_custom_tool_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[str] = []

    def tool_report(
        executable: str,
        timeout: float,
        expected_tool: str,
    ) -> dict[str, object]:
        del timeout, expected_tool
        checked.append(executable)
        return {"ok": True, "status": "ready", "path": executable}

    monkeypatch.setattr(cli, "_tool_report", tool_report)
    monkeypatch.setattr(cli, "_detect_installer", lambda: None)

    assert (
        cli.main(
            [
                "setup",
                "--ffmpeg",
                "C:/media/ffmpeg.exe",
                "--ffprobe",
                "C:/media/ffprobe.exe",
            ]
        )
        == 0
    )
    assert checked == ["C:/media/ffmpeg.exe", "C:/media/ffprobe.exe"]


def test_setup_missing_prints_exact_suggestion(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {
            "ok": False,
            "status": "missing",
            "path": None,
            "version": None,
        },
    )
    monkeypatch.setattr(
        cli,
        "_detect_installer",
        lambda: cli._Installer(
            "winget",
            (("winget", "install", "--id", "Gyan.FFmpeg", "-e"),),
            "Install the exact package.",
        ),
    )

    assert cli.main(["setup"]) == 3
    output = capsys.readouterr().out
    assert "suggested: winget install --id Gyan.FFmpeg -e" in output
    assert "Add --install" in output


def test_setup_install_yes_runs_fixed_argv(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checks = iter((False, False, True, True))
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def tool_report(*args: object) -> dict[str, object]:
        ready = next(checks)
        return {
            "ok": ready,
            "status": "ready" if ready else "missing",
            "path": "tool" if ready else None,
            "version": "tool 1.0" if ready else None,
        }

    def run(
        command: tuple[str, ...],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli, "_tool_report", tool_report)
    monkeypatch.setattr(
        cli,
        "_detect_installer",
        lambda: cli._Installer(
            "test-manager",
            (("manager", "install", "ffmpeg"),),
            "Test package source.",
        ),
    )
    monkeypatch.setattr(subprocess, "run", run)

    assert cli.main(["setup", "--install", "--yes"]) == 0
    assert calls == [
        (
            ("manager", "install", "ffmpeg"),
            {"check": False, "shell": False, "timeout": 600.0},
        )
    ]
    assert "FFmpeg and FFprobe are ready" in capsys.readouterr().out


def test_setup_install_needs_yes_outside_a_tty(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {
            "ok": False,
            "status": "missing",
            "path": None,
            "version": None,
        },
    )
    monkeypatch.setattr(
        cli,
        "_detect_installer",
        lambda: cli._Installer(
            "manager",
            (("manager", "install", "ffmpeg"),),
            "Test package source.",
        ),
    )
    monkeypatch.setattr(sys, "stdin", StringIO())

    assert cli.main(["setup", "--install"]) == 2
    assert "requires --yes" in capsys.readouterr().err


def test_setup_prompt_eof_cancels_installation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class EmptyTty(StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {"ok": False, "status": "missing", "path": None},
    )
    monkeypatch.setattr(
        cli,
        "_detect_installer",
        lambda: cli._Installer(
            "manager",
            (("manager", "install", "ffmpeg"),),
            "Test package source.",
        ),
    )
    monkeypatch.setattr(sys, "stdin", EmptyTty())

    assert cli.main(["setup", "--install"]) == 3
    assert "Installation cancelled" in capsys.readouterr().out


def test_setup_install_failure_returns_eight(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {
            "ok": False,
            "status": "missing",
            "path": None,
            "version": None,
        },
    )
    monkeypatch.setattr(
        cli,
        "_detect_installer",
        lambda: cli._Installer(
            "manager",
            (("manager", "install", "ffmpeg"),),
            "Test package source.",
        ),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 5),
    )

    assert cli.main(["setup", "--install", "--yes"]) == 8
    assert "FMG304" in capsys.readouterr().err


def test_setup_install_timeout_returns_eight(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {"ok": False, "status": "missing", "path": None},
    )
    monkeypatch.setattr(
        cli,
        "_detect_installer",
        lambda: cli._Installer(
            "manager",
            (("manager", "install", "ffmpeg"),),
            "Test package source.",
        ),
    )

    def time_out(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise subprocess.TimeoutExpired(("manager", "install", "ffmpeg"), 2.0)

    monkeypatch.setattr(subprocess, "run", time_out)

    assert cli.main(["setup", "--install", "--yes", "--install-timeout", "2"]) == 8
    output = capsys.readouterr().err
    assert "timed out after 2 seconds" in output
    assert "FMG304" in output


def test_setup_json_describes_state_without_changes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_tool_report",
        lambda *args: {
            "ok": False,
            "status": "missing",
            "path": None,
            "version": None,
        },
    )
    monkeypatch.setattr(cli, "_detect_installer", lambda: None)

    assert cli.main(["setup", "--json"]) == 3
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == 1
    assert report["changed"] is False
    assert report["installer"] is None


def test_setup_rejects_install_only_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["setup", "--yes"]) == 2
    assert "--yes requires --install" in capsys.readouterr().err

    assert cli.main(["setup", "--install", "--json"]) == 2
    assert "--json cannot be combined" in capsys.readouterr().err


def test_setup_rejects_install_with_custom_tool_paths(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(
        [
            "setup",
            "--install",
            "--ffmpeg",
            "C:/tools/ffmpeg.exe",
            "--ffprobe",
            "C:/tools/ffprobe.exe",
        ]
    )

    assert code == 2
    assert "cannot be combined with custom tool paths" in capsys.readouterr().err


def test_windows_installer_uses_exact_winget_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: f"C:/tools/{name}.exe" if name == "winget" else None,
    )

    installer = cli._detect_installer()

    assert installer is not None
    assert installer.manager == "winget"
    assert installer.commands[0][:7] == (
        "winget",
        "install",
        "--id",
        "Gyan.FFmpeg",
        "-e",
        "--source",
        "winget",
    )


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (PermissionError(), "permission-denied"),
        (subprocess.TimeoutExpired("ffmpeg", 1), "timeout"),
        (OSError(), "unusable"),
    ],
)
def test_tool_report_describes_start_failures(
    failure: OSError | subprocess.TimeoutExpired,
    status: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda executable: "tool")

    def fail(*args: object, **kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(subprocess, "run", fail)

    assert cli._tool_report("ffmpeg", 1)["status"] == status


def test_tool_report_keeps_failure_code_and_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda executable: "tool")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            2,
            stdout="",
            stderr="configuration rejected\n",
        ),
    )

    report = cli._tool_report("ffmpeg", 1)

    assert report["status"] == "failed"
    assert report["returncode"] == 2
    assert report["reason"] == "configuration rejected"


@pytest.mark.parametrize("expected_tool", ["ffmpeg", "ffprobe"])
def test_tool_report_rejects_a_different_ffmpeg_program(
    monkeypatch: pytest.MonkeyPatch,
    expected_tool: str,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda executable: "ffplay")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            0,
            stdout="ffplay version 7.1\n",
            stderr="",
        ),
    )

    report = cli._tool_report("ffplay", 1, expected_tool)

    assert report["ok"] is False
    assert report["status"] == "wrong-tool"
    assert report["reason"] == f"Expected {expected_tool} version output"


def test_error_catalog_lists_and_explains_identifiers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["errors"]) == 0
    listed = capsys.readouterr().out
    assert "FMG300  FFmpeg missing" in listed
    assert "FMG700  Job timed out" in listed

    assert cli.main(["explain-error", "fmg610"]) == 0
    explained = capsys.readouterr().out
    assert "FMG610: Encoder missing" in explained
    assert "Cause:" in explained
    assert "Try:" in explained


@pytest.mark.parametrize(
    ("stderr", "error_id"),
    [
        ("Unknown encoder 'madeup'", "FMG610"),
        ("Unknown decoder 'madeup'", "FMG611"),
        ("No such filter: madeup", "FMG612"),
        ("Permission denied", "FMG620"),
        ("No space left on device", "FMG621"),
        ("HTTP error 403 Forbidden", "FMG630"),
        ("Invalid argument", "FMG600"),
    ],
)
def test_execution_errors_get_specific_identifiers(
    stderr: str,
    error_id: str,
) -> None:
    assert cli._execution_error_id(stderr) == error_id


def test_execution_error_output_is_bounded(
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = ExecutionError(
        "failed",
        returncode=1,
        stderr="x" * 2_000,
        command="ffmpeg",
    )

    assert cli._execution_error(error) == 6
    output = capsys.readouterr().err
    assert len(output) < 700


def test_execution_error_prefers_the_causal_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = ExecutionError(
        "failed",
        returncode=1,
        stderr="Unknown encoder 'madeup'\nNothing was written into output file",
        command="ffmpeg",
    )

    assert cli._execution_error(error) == 6
    output = capsys.readouterr().err
    assert "Reason: Unknown encoder 'madeup'" in output
    assert "Reason: Nothing was written" not in output
    assert "A partial output may remain" in output


def test_progress_completion_is_printed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    progress = Progress(
        frame=50,
        fps=25.0,
        output_time=timedelta(seconds=2),
        total_size=1024,
        speed=1.5,
        percent=100.0,
        state="end",
        raw=(),
    )

    cli._show_progress(progress)

    assert (
        capsys.readouterr().err == "Progress: 100.0% time=0:00:02 speed=1.5x frame=50\n"
    )


def test_progress_printer_closes_an_open_tty_line() -> None:
    class TtyBuffer(StringIO):
        def isatty(self) -> bool:
            return True

    stream = TtyBuffer()
    printer = cli._ProgressPrinter(stream)
    progress = Progress(None, None, None, None, 1.0, None, "continue", ())

    printer(progress)
    printer.close()

    assert stream.getvalue() == "Progress: speed=1x\r\n"


def test_examples_are_ready_to_edit(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["examples"]) == 0
    output = capsys.readouterr().out
    assert "flowmpeg cut" in output
    assert "flowmpeg doctor" in output
    assert output.count("flowmpeg ") >= 50


def test_example_catalog_parses_every_command() -> None:
    parser = cli.build_parser()

    for example in cli._EXAMPLES:
        args = parser.parse_args(shlex.split(example.command)[1:])
        assert callable(args.handler), example.command


def test_example_categories_match_the_command_catalog() -> None:
    commands = {
        name: spec for spec in COMMAND_CATALOG for name in (spec.name, *spec.aliases)
    }

    for example in cli._EXAMPLES:
        command = shlex.split(example.command)[1]
        assert commands[command].category == example.category, example.command


def test_examples_cover_every_catalog_command() -> None:
    commands = {
        name: spec for spec in COMMAND_CATALOG for name in (spec.name, *spec.aliases)
    }
    covered = {
        commands[shlex.split(example.command)[1]].name for example in cli._EXAMPLES
    }

    assert {spec.name for spec in COMMAND_CATALOG} <= covered


def test_editing_examples_build_dry_run_plans(
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = cli.build_parser()
    for example in cli._EXAMPLES:
        values = shlex.split(example.command)[1:]
        args = parser.parse_args(values)
        if args.handler is not cli._run_media:
            continue
        assert cli.main([*values, "--dry-run"]) == 0, example.command
        assert capsys.readouterr().out.startswith("ffmpeg "), example.command


def test_examples_filter_by_category_and_search(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["examples", "--category", "images", "--search", "wave"]) == 0
    output = capsys.readouterr().out
    assert "flowmpeg waveform" in output
    assert "flowmpeg cut" not in output


def test_examples_report_an_empty_search(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["examples", "--search", "not-a-real-command"]) == 2
    assert "no examples matched" in capsys.readouterr().err


def test_examples_json_keeps_active_filters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        cli.main(["examples", "--category", "images", "--search", "wave", "--json"])
        == 0
    )
    report = json.loads(capsys.readouterr().out)

    assert report["schema_version"] == 1
    assert report["examples"] == [
        {
            "category": "images",
            "command": "flowmpeg waveform song.mp3 -o waveform.png",
        }
    ]


def test_commands_are_grouped_by_task(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["commands"]) == 0
    output = capsys.readouterr().out
    assert "VIDEO (" in output
    assert "AUDIO (" in output
    assert "transcode (convert):" in output
    assert "crossfade-audio (crossfade):" in output


def test_commands_filter_one_task_category(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["commands", "--category", "images"]) == 0
    output = capsys.readouterr().out
    assert "IMAGES (" in output
    assert "make-gif (gif):" in output
    assert "VIDEO (" not in output


def test_commands_filter_by_use_case_tag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["commands", "--tag", "privacy"]) == 0
    output = capsys.readouterr().out

    assert "remove-audio" in output
    assert "blur-region" in output
    assert "transcode" not in output


def test_commands_report_empty_category_and_tag_pair(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["commands", "--category", "help", "--tag", "privacy"]) == 2
    assert "no commands matched" in capsys.readouterr().err


def test_commands_json_exposes_discovery_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["commands", "--category", "subtitles", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == 1
    data = report["commands"]
    assert {item["name"] for item in data} == {
        "extract-subtitles",
        "add-subtitles",
        "remove-subtitles",
    }
    assert data[0]["category"] == "subtitles"
    assert data[0]["tags"] == ["accessibility", "archive", "copy"]
    assert "input_kind" in data[0]
    assert "capability_group" in data[0]


def test_no_arguments_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 0
    assert "usage: flowmpeg" in capsys.readouterr().out


def test_long_options_cannot_be_abbreviated() -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["transcode", "in.mov", "-o", "out.mp4", "--overw"])
    assert raised.value.code == 2


@pytest.mark.parametrize(
    "arguments",
    [
        ["mute", "in.mp4", "-o", "out.mp4", "--timeout", "nan"],
        ["mute", "in.mp4", "-o", "out.mp4", "--expected-duration", "inf"],
        ["trim", "in.mp4", "--start", "-inf", "-o", "out.mp4"],
        ["watermark", "in.mp4", "mark.png", "--opacity", "nan", "-o", "out.mp4"],
    ],
)
def test_nonfinite_numbers_are_rejected(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(arguments)
    assert raised.value.code == 2


def test_negative_crop_coordinates_are_rejected() -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(
            [
                "crop",
                "in.mp4",
                "--width",
                "320",
                "--height",
                "180",
                "--x",
                "-1",
                "-o",
                "out.mp4",
            ]
        )
    assert raised.value.code == 2


def test_windows_display_quotes_cmd_metacharacters() -> None:
    command = diagnostics._windows_display_argv(
        ("ffmpeg", "layout=0_0|w0_0", "(PTS-STARTPTS)/2", "plain")
    )

    assert command == 'ffmpeg "layout=0_0|w0_0" "(PTS-STARTPTS)/2" plain'


def test_console_entry_point_is_installed() -> None:
    matches = [
        item
        for item in entry_points(group="console_scripts")
        if item.name == "flowmpeg"
    ]
    assert len(matches) == 1
    assert matches[0].value == "flowmpeg.cli:main"


def test_module_entry_point_runs() -> None:
    completed = subprocess.run(
        (sys.executable, "-m", "flowmpeg", "--version"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout == "flowmpeg 0.1.0\n"


def test_console_program_runs() -> None:
    executable = shutil.which("flowmpeg")
    assert executable is not None
    completed = subprocess.run(
        (executable, "--version"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout == "flowmpeg 0.1.0\n"


def _media_info() -> MediaInfo:
    return MediaInfo(
        FormatInfo(
            filename="https://example-user:REDACT_ME@example.com/movie.mp4",
            format_name="mov,mp4,m4a,3gp,3g2,mj2",
            format_long_name="QuickTime / MOV",
            duration=12.5,
            size=1_048_576,
            bit_rate=671_088,
        ),
        (
            VideoStreamInfo(
                index=0,
                codec_type="video",
                codec_name="h264",
                codec_long_name="H.264",
                duration=12.5,
                time_base=None,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
            ),
            AudioStreamInfo(
                index=1,
                codec_type="audio",
                codec_name="aac",
                codec_long_name="AAC",
                duration=12.5,
                time_base=None,
                sample_rate=48_000,
                channels=2,
                channel_layout="stereo",
            ),
        ),
    )
