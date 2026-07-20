"""Generate the catalog-backed command reference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowmpeg.catalog import CATEGORIES, COMMAND_CATALOG  # noqa: E402

TARGET = ROOT / "docs" / "command-reference.md"


def render() -> str:
    """Render catalog fields as Markdown tables."""

    lines = [
        "# Generated command reference",
        "",
        "This file is generated from `COMMAND_CATALOG`. Run",
        "`python scripts/command_reference.py --check` before a release.",
        "",
        "Tags describe use cases. Capability groups provide broad doctor checks.",
        "Exact needs are checked by `flowmpeg doctor --command NAME`.",
        "",
    ]
    for category in CATEGORIES:
        specs = [spec for spec in COMMAND_CATALOG if spec.category == category]
        lines.extend(
            (
                f"## {category.title()} ({len(specs)})",
                "",
                "| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |",
                "|---|---|---|---|---|---|---|",
            )
        )
        for spec in specs:
            aliases = ", ".join(f"`{alias}`" for alias in spec.aliases) or "none"
            tags = ", ".join(f"`{tag}`" for tag in spec.tags)
            capability = (
                f"`{spec.capability_group}`"
                if spec.capability_group is not None
                else "none"
            )
            requirements = (
                ", ".join(f"`{item}`" for item in spec.requirements) or "none"
            )
            lines.append(
                f"| `{spec.name}` | {aliases} | {spec.input_kind} | "
                f"{spec.output_kind} | {tags} | {capability} | {requirements} |"
            )
        lines.append("")
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
        print("Command reference is out of date", file=sys.stderr)
        return 1
    print("Command reference is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
