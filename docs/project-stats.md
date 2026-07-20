# Flowmpeg project statistics

This file is generated from the command catalog, tests, documentation,
and roadmap. Run `python scripts/project_stats.py --check` before a
release, or `python scripts/project_stats.py --write` after an intended
source change.

## Current surface

| Measure | Count | Source |
|---|---:|---|
| Canonical terminal commands | 63 | `COMMAND_CATALOG` |
| Command aliases | 59 | `COMMAND_CATALOG` |
| Python shortcut functions | 55 | `shortcuts.__all__` |
| One-line terminal examples | 64 | CLI example catalog |
| Stable error identifiers | 16 | CLI error guide |
| Doctor feature groups | 13 | Doctor requirements |
| Test function definitions | 315 | `tests/test_*.py` |
| FFmpeg integration tests | 27 | Pytest markers |
| Documentation pages | 15 | `docs/*.md` |
| Documented command lines | 325 | Markdown code lines |
| Completed roadmap items | 90 | `ROADMAP.md` |
| Open roadmap items | 0 | `ROADMAP.md` |

## Category matrix

The command bar uses one `#` per canonical command. Example coverage
counts distinct canonical commands with at least one built-in example.

| Category | Commands | Aliases | Examples | Coverage | Python | Bar |
|---|---:|---:|---:|---:|---:|---|
| video | 17 | 18 | 18 | 17/17 (100%) | 17 | `#################` |
| audio | 13 | 14 | 13 | 13/13 (100%) | 13 | `#############` |
| composition | 9 | 9 | 9 | 9/9 (100%) | 9 | `#########` |
| effects | 5 | 4 | 5 | 5/5 (100%) | 5 | `#####` |
| images | 6 | 7 | 6 | 6/6 (100%) | 6 | `######` |
| subtitles | 4 | 5 | 4 | 4/4 (100%) | 4 | `####` |
| metadata | 1 | 1 | 1 | 1/1 (100%) | 1 | `#` |
| inspect | 4 | 1 | 4 | 4/4 (100%) | 0 | `####` |
| help | 4 | 0 | 4 | 4/4 (100%) | 0 | `####` |

## Use-case coverage

The bar uses one `#` per canonical command carrying the tag.

| Tag | Commands | Examples | Bar |
|---|---:|---:|---|
| accessibility | 4 | 4 | `####` |
| archive | 9 | 9 | `#########` |
| copy | 5 | 5 | `#####` |
| creator | 39 | 40 | `#######################################` |
| delivery | 17 | 18 | `#################` |
| discover | 4 | 4 | `####` |
| inspect | 4 | 4 | `####` |
| podcast | 13 | 13 | `#############` |
| privacy | 4 | 4 | `####` |
| silent-input | 30 | 31 | `##############################` |

## What the counts mean

Aliases are alternate terminal spellings, not separate operations.
Python counts catalog commands with a shortcut that has the same
canonical or alias spelling after hyphens become underscores.
A test function may contain several assertions or parameter cases.
Documented command lines count lines beginning with `flowmpeg` after
leading spaces are removed. The report does not claim a count of all
possible FFmpeg operations.
