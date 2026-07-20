from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

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
