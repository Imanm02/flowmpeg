from __future__ import annotations

import argparse
import ast
import inspect
import re
import subprocess
import sys
from pathlib import Path

import pytest

from flowmpeg import shortcuts
from flowmpeg.cli import build_parser
from flowmpeg.plan import Plan

_ROOT = Path(__file__).parents[1]
_MARKDOWN_FILES = (_ROOT / "README.md", *sorted((_ROOT / "docs").glob("*.md")))
_PYTHON_BLOCK = re.compile(r"^```python\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)
_MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


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
        target = match.group(1).split("#", 1)[0]
        if not target or "://" in target:
            continue
        assert (path.parent / target).exists(), target


def test_shortcut_guide_examples_build(monkeypatch: pytest.MonkeyPatch) -> None:
    def skip_run(self: Plan, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(Plan, "run", skip_run)
    path = _ROOT / "docs" / "shortcuts.md"
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


def test_workflow_guide_examples_build(monkeypatch: pytest.MonkeyPatch) -> None:
    def skip_run(self: Plan, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(Plan, "run", skip_run)
    path = _ROOT / "docs" / "workflows.md"
    text = path.read_text(encoding="utf-8")
    namespace: dict[str, object] = {"ff": shortcuts}
    for match in _PYTHON_BLOCK.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        code = compile(match.group(1), f"{path.name}:{line}", "exec")
        exec(code, namespace)


def test_shortcut_reference_names_every_factory() -> None:
    text = (_ROOT / "docs" / "shortcuts.md").read_text(encoding="utf-8")
    factories = {
        name
        for name in shortcuts.__all__
        if inspect.isfunction(getattr(shortcuts, name))
    }

    assert len(factories) == 52
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
