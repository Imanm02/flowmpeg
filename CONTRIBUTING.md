# Contributing

I want Flowmpeg changes to stay easy to review. A change should solve one
problem, include tests for its behavior, and keep command compilation separate
from process execution.

## Set up the repository

```console
git clone https://github.com/Imanm02/flowmpeg.git
cd flowmpeg
python -m pip install -e ".[dev]"
```

FFmpeg and FFprobe are needed for integration tests. Unit tests for graphs,
compilation, and parsing run without either binary.

## Run the checks

```console
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests examples
python scripts/content_scan.py
python -m pytest
python -m pip wheel . --no-deps --wheel-dir dist
```

Tests that start FFmpeg use the `integration` marker:

```console
python -m pytest -m integration
python -m pytest -m "not integration"
```

## Keep changes focused

- Add exact argv assertions for compiler behavior.
- Generate short media fixtures with `lavfi` when possible.
- Keep new public objects immutable unless process state requires mutation.
- Put high-level behavior in recipes and reusable mechanics in graph modules.
- Keep raw FFmpeg arguments scoped to global, input, or output positions.
- Do not log credentials, authorization headers, or unredacted input URLs.

Commit subjects should be short and state the real change. Documentation must
describe behavior that exists in the same commit.
