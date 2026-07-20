# Flowmpeg

[![CI](https://github.com/Imanm02/flowmpeg/actions/workflows/ci.yml/badge.svg)](https://github.com/Imanm02/flowmpeg/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Readable media jobs with inspectable FFmpeg commands.

I wrote Flowmpeg because a useful FFmpeg command can become difficult to
review once it has several inputs, filter labels, and stream maps. Flowmpeg
keeps those details in a typed media graph, then gives me the exact command
before I choose to run it.

Nothing starts while a plan is being built. I can inspect the command, read a
plain explanation, validate the graph, or pass the plan to the process runner.

## One plan from several inputs

```python
from flowmpeg import Progress, media


def report(event: Progress) -> None:
    if event.percent is not None:
        print(f"{event.percent:.1f}%")


logo = media("logo.png", "-loop", "1", audio=False)
music = media("music.mp3", video=False)

plan = (
    media("talk.mp4")
    .trim(start=5, end=60)
    .scale(width=1080)
    .overlay(logo, position="top-right", opacity=0.8)
    .mix_audio(music, addition_volume=0.15)
    .output("short.mp4", preset="web")
)

print(plan.command())
print(plan.explain())

result = plan.run(
    expected_duration=55,
    on_progress=report,
)
print(result.elapsed)
```

The clip API keeps the original audio attached while video filters are added.
Each method expands into ordinary graph nodes, so the result can still be
combined with lower-level filters.

## Install from GitHub

Flowmpeg needs Python 3.10 or newer. FFmpeg and FFprobe must be installed
separately and available on `PATH`.

```console
python -m pip install "git+https://github.com/Imanm02/flowmpeg.git"
ffmpeg -version
ffprobe -version
```

The package has no required Python dependencies.

## Start with a task

The [example guide](docs/examples.md) shows complete inputs and expected
outputs for common jobs:

- Trim a clip or change its size
- Remove video audio or extract it as MP3
- Add a logo, music, fades, or speech ducking
- Join clips or arrange four videos in a grid
- Copy subtitles and call raw FFmpeg filters
- Produce multiple outputs, inspect metadata, and report progress

## What works today

- Immutable audio, video, and subtitle stream references
- Deterministic `filter_complex` labels and argv compilation
- Typed FFprobe container and stream results
- Synchronous execution with progress callbacks and timeouts
- Audio gain, delay, fades, mixing, and sidechain ducking
- Video trim, scale, overlays, grids, and compatible clip concatenation
- Paired `Clip` operations that keep audio with video
- A web MP4 preset and ordered raw argument escape hatches

The low-level API is available when a recipe is not the right fit:

```python
from flowmpeg import input, output

source = input("input.mp4")
video = source.video().filter("unsharp", 5, 5, 1.0)

plan = output(
    video,
    source.audio(),
    to="output.mp4",
    args=("-c:v", "libx264", "-c:a", "aac"),
)

print(plan.filter_graph())
print(plan.raw_argv())
```

`raw_argv()` is intentionally explicit because it may contain input URLs or
headers. `command()` redacts common credential locations before formatting the
command for display.

## How a plan is built

Flowmpeg has three public levels:

1. `Clip` methods and recipe functions describe media intent.
2. Typed streams form an immutable directed graph.
3. The compiler produces an argv tuple for one FFmpeg process.

Compilation does not read input files, create temporary files, or start a
process. Probing and execution are separate operations. More detail is in the
[design notes](docs/design.md).

Filter outputs have one consumer. Use `split()` or `asplit()` when one filtered
stream needs more than one destination. The compiler reports unused outputs and
fanout before starting FFmpeg.

## Safety defaults

- Existing local outputs are not replaced unless `.overwrite()` is used.
- Commands run as argv with `shell=False`.
- Displayed commands and captured errors redact URL user information and known
  secret-bearing headers.
- The synchronous runner reserves process pipes for progress and logs.
- Partial outputs are left in place after a failed job.

## Project status

Flowmpeg is pre-alpha. The graph, compiler, and runner contracts are tested,
but the public API may change before the first stable release. Current work is
tracked in [CHANGELOG.md](CHANGELOG.md).

## Development

```console
git clone https://github.com/Imanm02/flowmpeg.git
cd flowmpeg
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests examples
python -m pytest
```

Integration tests create short media files from FFmpeg `lavfi` sources. No
binary test assets are stored in the repository.

See [CONTRIBUTING.md](CONTRIBUTING.md) before preparing a change. Security
reports follow [SECURITY.md](SECURITY.md).

Flowmpeg is available under the [MIT License](LICENSE).
