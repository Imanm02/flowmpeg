# Flowmpeg

Readable media jobs with inspectable FFmpeg commands.

I started Flowmpeg because FFmpeg commands become difficult to review once a
job has several inputs, stream maps, or filters. I want the Python code to show
the media operation first while keeping the generated command available for
inspection.

Flowmpeg is in early development. The first release will focus on immutable
media graphs, deterministic command compilation, probing, progress reporting,
and common composition recipes. Running a plan will always be explicit.

## Development

Flowmpeg requires Python 3.10 or newer. FFmpeg and FFprobe are required for
integration tests, but command compilation tests do not call either binary.

```console
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m mypy src tests
```

## License

Flowmpeg is available under the MIT License.

