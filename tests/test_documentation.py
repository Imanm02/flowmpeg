from __future__ import annotations

import argparse
import ast
import contextlib
import inspect
import io
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import flowmpeg
from flowmpeg import cli, shortcuts
from flowmpeg.catalog import COMMAND_CATALOG
from flowmpeg.cli import build_parser
from flowmpeg.plan import Plan

_ROOT = Path(__file__).parents[1]
_MARKDOWN_FILES = (_ROOT / "README.md", *sorted((_ROOT / "docs").glob("*.md")))
_PYTHON_BLOCK = re.compile(r"^```python\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)
_MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*$", re.MULTILINE)
_BATCH_BLOCK = re.compile(
    r"^```(bat|powershell|bash)\s*\n(.*?)^```",
    re.MULTILINE | re.DOTALL,
)
_BATCH_OPTION = re.compile(
    r"--(crf|codec|bitrate|factor|columns|rows|interval|target|fill|at)\s+"
    r"([^\s;|}]+)"
)


def _code_cases() -> list[tuple[str, str]]:
    cases: list[tuple[str, str]] = []
    for path in _MARKDOWN_FILES:
        text = path.read_text(encoding="utf-8")
        for match in _PYTHON_BLOCK.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            name = f"{path.relative_to(_ROOT)}:{line}"
            cases.append((name, match.group(1)))
    return cases


_CODE_CASES = _code_cases()
_BUILD_PATHS = tuple(
    path
    for path in _MARKDOWN_FILES
    if _PYTHON_BLOCK.search(path.read_text(encoding="utf-8"))
)


@pytest.mark.parametrize(
    ("case_name", "source"),
    _CODE_CASES,
    ids=[case[0] for case in _CODE_CASES],
)
def test_python_documentation_blocks_parse(case_name: str, source: str) -> None:
    ast.parse(source, filename=case_name)


@pytest.mark.parametrize("path", _MARKDOWN_FILES, ids=lambda path: path.name)
def test_markdown_code_fences_are_closed(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count("```") % 2 == 0


@pytest.mark.parametrize("path", _MARKDOWN_FILES, ids=lambda path: path.name)
def test_local_markdown_links_resolve(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for match in _MARKDOWN_LINK.finditer(text):
        target, separator, fragment = match.group(1).partition("#")
        if "://" in target:
            continue
        target_path = path if not target else path.parent / target
        assert target_path.exists(), target
        if separator:
            assert fragment in _markdown_anchors(target_path), match.group(1)


def _markdown_anchors(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return {
        _github_anchor(match.group(1)) for match in _MARKDOWN_HEADING.finditer(text)
    }


def _github_anchor(heading: str) -> str:
    heading = re.sub(r"[`*_~]", "", heading).strip().lower()
    heading = re.sub(r"[^\w\- ]", "", heading)
    return re.sub(r"\s+", "-", heading)


@pytest.mark.parametrize("path", _BUILD_PATHS, ids=lambda path: path.name)
def test_python_documentation_examples_build(
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
) -> None:
    def skip_run(self: Plan, **kwargs: object) -> object:
        del kwargs
        return SimpleNamespace(
            returncode=0,
            elapsed=0.0,
            stderr="",
            last_progress=None,
            outputs=tuple(output.destination for output in self.outputs),
        )

    video = SimpleNamespace(
        codec_name="h264",
        width=1920,
        height=1080,
        average_frame_rate=None,
    )
    audio = SimpleNamespace(codec_name="aac", sample_rate=48_000, channels=2)
    info = SimpleNamespace(
        duration=60.0,
        format=SimpleNamespace(
            format_long_name="QuickTime / MOV",
            format_name="mov,mp4",
            size=1_000,
        ),
        streams=(video, audio),
        video_streams=(video,),
        audio_streams=(audio,),
        subtitle_streams=(),
    )

    monkeypatch.setattr(Plan, "run", skip_run)
    monkeypatch.setattr(flowmpeg, "probe", lambda *args, **kwargs: info)
    monkeypatch.setattr(
        flowmpeg,
        "measure_loudness",
        lambda *args, **kwargs: SimpleNamespace(integrated_lufs=-18.4),
    )
    monkeypatch.setattr(
        flowmpeg,
        "detect_silence",
        lambda *args, **kwargs: SimpleNamespace(
            intervals=(SimpleNamespace(start=1.0, end=2.0, duration=1.0),),
            total_silence=1.0,
            longest_silence=1.0,
        ),
    )
    monkeypatch.setattr(
        flowmpeg,
        "detect_black",
        lambda *args, **kwargs: SimpleNamespace(
            intervals=(SimpleNamespace(start=1.0, end=2.0, duration=1.0),),
            total_black=1.0,
            longest_black=1.0,
        ),
    )
    text = path.read_text(encoding="utf-8")
    namespace: dict[str, object] = {"ff": shortcuts}
    for match in _PYTHON_BLOCK.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        code = compile(match.group(1), f"{path.name}:{line}", "exec")
        exec(code, namespace)


def test_documentation_uses_known_commands() -> None:
    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    known = {*subparsers.choices, "--help", "--version"}
    command_lines: list[str] = []
    for path in _MARKDOWN_FILES:
        command_lines.extend(
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("flowmpeg ") and not line.startswith("flowmpeg [")
        )

    assert len(command_lines) >= 150
    for line in command_lines:
        command = line.split(maxsplit=2)[1]
        assert command in known, line


def test_documented_terminal_options_parse() -> None:
    parser = build_parser()
    checked: list[str] = []
    failures: list[str] = []
    for path in _MARKDOWN_FILES:
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.startswith("flowmpeg ") or line.startswith("flowmpeg ["):
                continue
            argv = shlex.split(line)[1:]
            if "--help" in argv or "--version" in argv:
                continue
            if any(token in argv for token in ("|", ">", "<", "&&")):
                continue
            checked.append(line)
            try:
                with (
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    parser.parse_args(argv)
            except SystemExit:
                failures.append(f"{path.relative_to(_ROOT)}:{number}: {line}")

    assert len(checked) >= 200
    assert not failures, "\n".join(failures)


def test_documented_edit_commands_build() -> None:
    editing_names = {
        value
        for spec in COMMAND_CATALOG
        if spec.category not in {"help", "inspect"}
        for value in (spec.name, *spec.aliases)
    }
    checked: list[str] = []
    failures: list[str] = []
    for path in _MARKDOWN_FILES:
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.startswith("flowmpeg "):
                continue
            argv = shlex.split(line)[1:]
            if not argv or argv[0] not in editing_names:
                continue
            if "--help" in argv or "--version" in argv:
                continue
            if any(token in argv for token in ("|", ">", "<", "&&")):
                continue
            if "--dry-run" not in argv:
                argv.append("--dry-run")
            checked.append(line)
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                result = cli.main(argv)
            if result != 0:
                failures.append(f"{path.relative_to(_ROOT)}:{number}: {line}")

    assert len(checked) >= 190
    assert not failures, "\n".join(failures)


def test_batch_shell_commands_build_without_media() -> None:
    path = _ROOT / "docs" / "batch-jobs.md"
    text = path.read_text(encoding="utf-8")
    calls: list[tuple[str, str]] = []
    for block in _BATCH_BLOCK.finditer(text):
        language, source = block.groups()
        for match in re.finditer(r"\bflowmpeg\s+([a-z][a-z-]*)([^\n}]*)", source):
            calls.append((language, match.group(0)))

    assert len(calls) == 12
    for _, call in calls:
        command = call.split(maxsplit=2)[1]
        if command == "commands":
            argv = ["commands", "--json"]
        else:
            argv = [command, "input file.mp4"]
            for option, value in _BATCH_OPTION.findall(call):
                argv.extend((f"--{option}", value.strip("\"'")))
            if "--no-audio" in call:
                argv.append("--no-audio")
            suffix = (
                ".mp3"
                if command == "audio"
                else ".jpg"
                if command
                in {
                    "sheet",
                    "thumb",
                }
                else ".mp4"
            )
            argv.extend(("-o", f"output file{suffix}", "--dry-run"))
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            assert cli.main(argv) == 0, call


def test_batch_shell_examples_show_quoting_and_failure_choices() -> None:
    text = (_ROOT / "docs" / "batch-jobs.md").read_text(encoding="utf-8")
    blocks = list(_BATCH_BLOCK.finditer(text))

    assert len(blocks) == 12
    assert '"%F"' in text and '"%%F"' in text
    assert "$_.FullName" in text and '"$file"' in text
    assert "|| exit" in text
    assert "$LASTEXITCODE -ne 0" in text
    assert "failed-files.txt" in text


def test_shortcut_reference_names_every_factory() -> None:
    text = (_ROOT / "docs" / "shortcuts.md").read_text(encoding="utf-8")
    factories = {
        name
        for name in shortcuts.__all__
        if inspect.isfunction(getattr(shortcuts, name))
    }

    assert len(factories) == 67
    for name in factories:
        assert f"`{name}`" in text


def test_generated_project_statistics_are_current() -> None:
    completed = subprocess.run(
        (sys.executable, "scripts/project_stats.py", "--check"),
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_generated_command_reference_is_current() -> None:
    completed = subprocess.run(
        (sys.executable, "scripts/command_reference.py", "--check"),
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
