# Flowmpeg project statistics

This file is generated from the command catalog, tests, documentation,
and roadmap. Run `python scripts/project_stats.py --check` before a
release, or `python scripts/project_stats.py --write` after an intended
source change.

## Current surface

| Measure | Count | Source |
|---|---:|---|
| Canonical terminal commands | 88 | `COMMAND_CATALOG` |
| Generated UI command forms | 88 | UI schema builder |
| Command aliases | 108 | `COMMAND_CATALOG` |
| Python shortcut functions | 68 | `shortcuts.__all__` |
| One-line terminal examples | 89 | CLI example catalog |
| Stable error identifiers | 16 | CLI error guide |
| Stable audit findings | 20 | Media audit |
| Doctor feature groups | 18 | Doctor requirements |
| Test function definitions | 588 | `tests/test_*.py` |
| UI test function definitions | 133 | `tests/test_ui_*.py` |
| FFmpeg integration tests | 42 | Pytest markers |
| Documentation pages | 20 | `docs/*.md` |
| Documented command lines | 491 | Markdown code lines |
| Completed roadmap items | 136 | `ROADMAP.md` |
| Open roadmap items | 2 | `ROADMAP.md` |

## Category matrix

The command bar uses one `#` per canonical command. Example coverage
counts distinct canonical commands with at least one built-in example.

| Category | Commands | Aliases | Examples | Coverage | Python | Bar |
|---|---:|---:|---:|---:|---:|---|
| video | 23 | 30 | 24 | 23/23 (100%) | 20 | `#######################` |
| audio | 21 | 29 | 21 | 21/21 (100%) | 14 | `#####################` |
| composition | 9 | 9 | 9 | 9/9 (100%) | 9 | `#########` |
| effects | 5 | 4 | 5 | 5/5 (100%) | 5 | `#####` |
| images | 7 | 9 | 7 | 7/7 (100%) | 6 | `#######` |
| subtitles | 4 | 5 | 4 | 4/4 (100%) | 4 | `####` |
| metadata | 3 | 4 | 3 | 3/3 (100%) | 2 | `###` |
| inspect | 11 | 16 | 11 | 11/11 (100%) | 0 | `###########` |
| help | 5 | 2 | 5 | 5/5 (100%) | 0 | `#####` |

## Use-case coverage

The bar uses one `#` per canonical command carrying the tag.

| Tag | Commands | Examples | Bar |
|---|---:|---:|---|
| accessibility | 4 | 4 | `####` |
| archive | 21 | 21 | `#####################` |
| copy | 7 | 7 | `#######` |
| creator | 49 | 50 | `#################################################` |
| delivery | 26 | 27 | `##########################` |
| discover | 5 | 5 | `#####` |
| inspect | 11 | 11 | `###########` |
| podcast | 21 | 21 | `#####################` |
| privacy | 4 | 4 | `####` |
| silent-input | 37 | 38 | `#####################################` |

## What the counts mean

Aliases are alternate terminal spellings, not separate operations.
Python counts catalog commands with a shortcut that has the same
canonical or alias spelling after hyphens become underscores.
A test function may contain several assertions or parameter cases.
Documented command lines count lines beginning with `flowmpeg` after
leading spaces are removed. The report does not claim a count of all
possible FFmpeg operations.
