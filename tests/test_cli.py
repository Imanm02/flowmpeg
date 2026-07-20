from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import timedelta
from importlib.metadata import entry_points
from io import StringIO

import pytest

from flowmpeg import cli, diagnostics
from flowmpeg.errors import (
    BinaryNotFoundError,
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
    assert str(error) in captured.err
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
    def tool_report(executable: str, timeout: float) -> dict[str, object]:
        return {"ok": True, "path": executable, "version": f"{executable} 1.0"}

    monkeypatch.setattr(cli, "_tool_report", tool_report)
    monkeypatch.setattr(
        cli, "_capability_report", lambda *args: {"filter:overlay": True}
    )

    assert cli.main(["doctor", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["flowmpeg_version"] == "0.1.0"
    assert report["python_version"]
    assert report["capabilities"]["filter:overlay"] is True


def test_doctor_returns_three_when_a_tool_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def tool_report(executable: str, timeout: float) -> dict[str, object]:
        del timeout
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
    assert output.count("flowmpeg ") >= 10


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
