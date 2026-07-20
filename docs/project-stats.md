# Flowmpeg project statistics

This file is generated from the command catalog, tests, documentation,
and roadmap. Run `python scripts/project_stats.py --check` before a
release, or `python scripts/project_stats.py --write` after an intended
source change.

## Current surface

| Measure | Count | Source |
|---|---:|---|
| Canonical terminal commands | 59 | `COMMAND_CATALOG` |
| Command aliases | 53 | `COMMAND_CATALOG` |
| Python shortcut functions | 52 | `shortcuts.__all__` |
| One-line terminal examples | 54 | CLI example catalog |
| Stable error identifiers | 16 | CLI error guide |
| Doctor feature groups | 12 | Doctor requirements |
| Test functions | 268 | `tests/test_*.py` |
| FFmpeg integration tests | 24 | Pytest markers |
| Documentation pages | 12 | `docs/*.md` |
| Documented command lines | 268 | Markdown code lines |
| Completed roadmap items | 49 | `ROADMAP.md` |
| Open roadmap items | 7 | `ROADMAP.md` |

## Commands by task

The bar is one `#` per canonical command.

| Category | Commands | Bar |
|---|---:|---|
| video | 16 | `################` |
| audio | 13 | `#############` |
| composition | 8 | `########` |
| effects | 5 | `#####` |
| images | 6 | `######` |
| subtitles | 3 | `###` |
| metadata | 1 | `#` |
| inspect | 3 | `###` |
| help | 4 | `####` |

## What the counts mean

Aliases are alternate terminal spellings, not separate operations.
A test function may contain several assertions or parameter cases.
Documented command lines count lines beginning with `flowmpeg` after
leading spaces are removed. The report does not claim a count of all
possible FFmpeg operations.
