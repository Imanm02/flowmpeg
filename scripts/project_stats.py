"""Generate source-backed Flowmpeg project statistics."""

from __future__ import annotations

import argparse
import ast
import inspect
import shlex
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowmpeg import shortcuts  # noqa: E402
from flowmpeg.audit import AUDIT_CODES  # noqa: E402
from flowmpeg.catalog import (  # noqa: E402
    CATEGORIES,
    COMMAND_CATALOG,
    TAGS,
    command_spec,
)
from flowmpeg.cli import _ERROR_GUIDE, _EXAMPLES, _FEATURE_REQUIREMENTS  # noqa: E402

TARGET = ROOT / "docs" / "project-stats.md"


def _test_counts() -> tuple[int, int, int]:
    tests = 0
    integration = 0
    ui_tests = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and node.name.startswith("test_"):
                tests += 1
                if path.stem.startswith("test_ui_"):
                    ui_tests += 1
                if any(_is_integration_mark(item) for item in node.decorator_list):
                    integration += 1
    return tests, integration, ui_tests


def _is_integration_mark(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "integration"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
    )


def _documentation_counts() -> tuple[int, int]:
    pages = sorted((ROOT / "docs").glob("*.md"))
    command_lines = sum(
        1
        for path in pages
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.lstrip().startswith("flowmpeg ")
    )
    return len(pages), command_lines


def _roadmap_counts() -> tuple[int, int]:
    text = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    return text.count("- [x]"), text.count("- [ ]")


def render() -> str:
    """Render the current statistics as Markdown."""

    tests, integration, ui_tests = _test_counts()
    docs, documented_commands = _documentation_counts()
    completed, open_items = _roadmap_counts()
    aliases = sum(len(spec.aliases) for spec in COMMAND_CATALOG)
    shortcut_names = set(shortcuts.__all__)
    shortcut_functions = sum(
        inspect.isfunction(getattr(shortcuts, name)) for name in shortcuts.__all__
    )
    category_counts = Counter(spec.category for spec in COMMAND_CATALOG)
    alias_counts = Counter(
        spec.category for spec in COMMAND_CATALOG for _ in spec.aliases
    )
    example_counts = Counter(example.category for example in _EXAMPLES)
    covered_commands: dict[str, set[str]] = {category: set() for category in CATEGORIES}
    for example in _EXAMPLES:
        values = shlex.split(example.command)
        spec = command_spec(values[1])
        if spec is not None:
            covered_commands[spec.category].add(spec.name)
    shortcut_counts = Counter(
        spec.category
        for spec in COMMAND_CATALOG
        if any(
            name.replace("-", "_") in shortcut_names
            for name in (spec.name, *spec.aliases)
        )
    )
    command_tag_counts = Counter(tag for spec in COMMAND_CATALOG for tag in spec.tags)
    example_tag_counts = Counter(tag for example in _EXAMPLES for tag in example.tags)
    lines = [
        "# Flowmpeg project statistics",
        "",
        "This file is generated from the command catalog, tests, documentation,",
        "and roadmap. Run `python scripts/project_stats.py --check` before a",
        "release, or `python scripts/project_stats.py --write` after an intended",
        "source change.",
        "",
        "## Current surface",
        "",
        "| Measure | Count | Source |",
        "|---|---:|---|",
        f"| Canonical terminal commands | {len(COMMAND_CATALOG)} | `COMMAND_CATALOG` |",
        f"| Generated UI command forms | {len(COMMAND_CATALOG)} | UI schema builder |",
        f"| Command aliases | {aliases} | `COMMAND_CATALOG` |",
        f"| Python shortcut functions | {shortcut_functions} | `shortcuts.__all__` |",
        f"| One-line terminal examples | {len(_EXAMPLES)} | CLI example catalog |",
        f"| Stable error identifiers | {len(_ERROR_GUIDE)} | CLI error guide |",
        f"| Stable audit findings | {len(AUDIT_CODES)} | Media audit |",
        f"| Doctor feature groups | {len(_FEATURE_REQUIREMENTS)} | Doctor requirements |",
        f"| Test function definitions | {tests} | `tests/test_*.py` |",
        f"| UI test function definitions | {ui_tests} | `tests/test_ui_*.py` |",
        f"| FFmpeg integration tests | {integration} | Pytest markers |",
        f"| Documentation pages | {docs} | `docs/*.md` |",
        f"| Documented command lines | {documented_commands} | Markdown code lines |",
        f"| Completed roadmap items | {completed} | `ROADMAP.md` |",
        f"| Open roadmap items | {open_items} | `ROADMAP.md` |",
        "",
        "## Category matrix",
        "",
        "The command bar uses one `#` per canonical command. Example coverage",
        "counts distinct canonical commands with at least one built-in example.",
        "",
        "| Category | Commands | Aliases | Examples | Coverage | Python | Bar |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for category in CATEGORIES:
        count = category_counts[category]
        covered = len(covered_commands[category])
        percent = round(covered / count * 100) if count else 0
        lines.append(
            f"| {category} | {count} | {alias_counts[category]} | "
            f"{example_counts[category]} | {covered}/{count} ({percent}%) | "
            f"{shortcut_counts[category]} | `{'#' * count}` |"
        )
    lines.extend(
        (
            "",
            "## Use-case coverage",
            "",
            "The bar uses one `#` per canonical command carrying the tag.",
            "",
            "| Tag | Commands | Examples | Bar |",
            "|---|---:|---:|---|",
        )
    )
    for tag in TAGS:
        count = command_tag_counts[tag]
        lines.append(
            f"| {tag} | {count} | {example_tag_counts[tag]} | `{'#' * count}` |"
        )
    lines.extend(
        (
            "",
            "## What the counts mean",
            "",
            "Aliases are alternate terminal spellings, not separate operations.",
            "Python counts catalog commands with a shortcut that has the same",
            "canonical or alias spelling after hyphens become underscores.",
            "A test function may contain several assertions or parameter cases.",
            "Documented command lines count lines beginning with `flowmpeg` after",
            "leading spaces are removed. The report does not claim a count of all",
            "possible FFmpeg operations.",
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    content = render()
    if args.write:
        TARGET.write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {TARGET.relative_to(ROOT)}")
        return 0
    current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if current != content:
        print("Project statistics are out of date", file=sys.stderr)
        return 1
    print("Project statistics are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
