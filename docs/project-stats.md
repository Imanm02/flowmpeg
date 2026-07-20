# Flowmpeg project statistics

This file is generated from the command catalog, tests, documentation,
and roadmap. Run `python scripts/project_stats.py --check` before a
release, or `python scripts/project_stats.py --write` after an intended
source change.

## Current surface

| Measure | Count | Source |
|---|---:|---|
| Canonical terminal commands | 60 | `COMMAND_CATALOG` |
| Command aliases | 53 | `COMMAND_CATALOG` |
| Python shortcut functions | 52 | `shortcuts.__all__` |
| One-line terminal examples | 61 | CLI example catalog |
| Stable error identifiers | 16 | CLI error guide |
| Doctor feature groups | 12 | Doctor requirements |
| Test function definitions | 284 | `tests/test_*.py` |
| FFmpeg integration tests | 24 | Pytest markers |
| Documentation pages | 14 | `docs/*.md` |
| Documented command lines | 276 | Markdown code lines |
| Completed roadmap items | 72 | `ROADMAP.md` |
| Open roadmap items | 11 | `ROADMAP.md` |

## Category matrix

The command bar uses one `#` per canonical command. Example coverage
counts distinct canonical commands with at least one built-in example.

| Category | Commands | Aliases | Examples | Coverage | Python | Bar |
|---|---:|---:|---:|---:|---:|---|
| video | 16 | 16 | 17 | 16/16 (100%) | 16 | `################` |
| audio | 13 | 14 | 13 | 13/13 (100%) | 13 | `#############` |
| composition | 8 | 7 | 8 | 8/8 (100%) | 8 | `########` |
| effects | 5 | 4 | 5 | 5/5 (100%) | 5 | `#####` |
| images | 6 | 7 | 6 | 6/6 (100%) | 6 | `######` |
| subtitles | 3 | 3 | 3 | 3/3 (100%) | 3 | `###` |
| metadata | 1 | 1 | 1 | 1/1 (100%) | 1 | `#` |
| inspect | 4 | 1 | 4 | 4/4 (100%) | 0 | `####` |
| help | 4 | 0 | 4 | 4/4 (100%) | 0 | `####` |

## Use-case coverage

The bar uses one `#` per canonical command carrying the tag.

| Tag | Commands | Examples | Bar |
|---|---:|---:|---|
| accessibility | 3 | 3 | `###` |
| archive | 9 | 9 | `#########` |
| copy | 5 | 5 | `#####` |
| creator | 37 | 38 | `#####################################` |
| delivery | 14 | 15 | `##############` |
| discover | 4 | 4 | `####` |
| inspect | 4 | 4 | `####` |
| podcast | 13 | 13 | `#############` |
| privacy | 4 | 4 | `####` |
| silent-input | 27 | 28 | `###########################` |

## What the counts mean

Aliases are alternate terminal spellings, not separate operations.
Python counts catalog commands with a shortcut that has the same
canonical or alias spelling after hyphens become underscores.
A test function may contain several assertions or parameter cases.
Documented command lines count lines beginning with `flowmpeg` after
leading spaces are removed. The report does not claim a count of all
possible FFmpeg operations.
