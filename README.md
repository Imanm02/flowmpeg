# Flowmpeg

[![CI](https://github.com/Imanm02/flowmpeg/actions/workflows/ci.yml/badge.svg)](https://github.com/Imanm02/flowmpeg/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Readable media jobs with inspectable FFmpeg commands.

I wrote Flowmpeg because a useful FFmpeg command can become difficult to
review once it has several inputs, filter labels, and stream maps. Flowmpeg
keeps those details in a typed media graph, then gives me the exact command
before I choose to run it.

Python plans do not start work while they are being built. I can inspect a
command, read its explanation, or pass the plan to the process runner. The
installed command is there when I want to run the same kind of job from CMD.

## Install from GitHub

Flowmpeg needs Python 3.10 or newer. FFmpeg and FFprobe can be found through
`PATH`, or passed by executable path to setup, doctor, probe, and editing
commands.

```console
python -m pip install "git+https://github.com/Imanm02/flowmpeg.git"
flowmpeg --version
flowmpeg setup
```

`flowmpeg setup` checks the tools without changing the machine. If either tool
is missing, it prints an exact package manager command when a supported manager
is available. Installation is opt-in with `flowmpeg setup --install` and
requires confirmation. The
[installation guide](docs/installation.md) explains Windows, macOS, Linux, CI,
custom executable paths, and every setup status.

The package has no required Python dependencies. After setup, run the broader
capability report:

```console
flowmpeg doctor
flowmpeg doctor --command cut
flowmpeg doctor --smoke-test
flowmpeg audit input.mp4 --expect av
flowmpeg audit delivery.mp4 --max-duration 60 --width 1920 --height 1080
flowmpeg loudness episode.wav
flowmpeg normalize-exact episode.wav -o episode-exact.wav
flowmpeg find-silence interview.wav
flowmpeg find-black tape.mp4
flowmpeg scenes interview.mp4
flowmpeg crop-report letterboxed.mp4 --duration 30
flowmpeg hls input.mp4 -o delivery-hls
flowmpeg dash input.mp4 -o delivery-dash
```

The second check accepts the `cut` shortcut and verifies the default encoders,
muxer, and filters used by canonical `trim`. It returns exit code 3 when that
exact path is unavailable.

The smoke test creates a temporary 16 by 16 video, encodes one frame, probes
the result, then removes it.

The audit checks stream shape and optional delivery constraints. It reports
stable finding codes for scripts and returns a separate policy-failure code.

The loudness command measures integrated LUFS, true peak, loudness range, and
the offset from a chosen normalization target without writing an output file.
`normalize-exact` uses those measurements in a second FFmpeg pass. Its dry run
starts no process, while `--analyze-only` measures and prints the exact encoding
command without creating the destination.

The analysis commands turn FFmpeg filter output into typed intervals,
scene-change scores, and ranked crop rectangles. The
[analysis guide](docs/analysis.md) shows text reports, JSON fields, visual
timelines, and threshold choices for different recordings.

## One-line terminal jobs

```console
flowmpeg cut input.mp4 --start 10 --duration 20 -o clip.mp4
flowmpeg loop motion.mp4 --duration 30 -o background.mp4
flowmpeg webm input.mov --crf 30 -o delivery.webm
flowmpeg hevc input.mov --crf 28 -o archive.mp4
flowmpeg av1 input.mov --crf 35 --speed 8 -o delivery-av1.webm
flowmpeg hls input.mp4 --segment-duration 4 -o delivery-hls
flowmpeg dash input.mp4 --segment-duration 2 -o delivery-dash
flowmpeg remux input.mp4 -o archive.mkv
flowmpeg scale input.mp4 --width 1280 -o small.mp4
flowmpeg audio input.mp4 -o audio.mp3
flowmpeg normalize-exact voice.wav --target-integrated -16 -o voice-exact.wav
flowmpeg pip input.mp4 camera.mp4 -o with-camera.mp4
flowmpeg join-any phone.mp4 camera.mp4 --width 1280 --height 720 -o joined.mp4
flowmpeg waveform audio.mp3 -o waveform.png
flowmpeg burn-captions lesson.mp4 captions.srt -o lesson-open.mp4
flowmpeg social input.mp4 --target vertical -o vertical.mp4
flowmpeg voice recording.wav -o finished.wav
flowmpeg captions movie.mp4 subtitles.srt -o captioned.mp4
flowmpeg audiogram episode.wav cover.jpg -o episode.mp4
```

Editing commands run immediately, protect existing outputs, and report
progress. `--dry-run` prints the redacted FFmpeg command without starting it.
The [command guide](docs/cli.md) covers the editing and inspection commands,
their short forms, inputs, outputs, and exit codes.

The module form runs the same interface:

```console
python -m flowmpeg cut input.mp4 --duration 5 -o clip.mp4
```

## One-line Python jobs

```python
from flowmpeg import shortcuts as ff

ff.trim("input.mp4", "clip.mp4", start=10, end=30).run()
ff.resize("input.mp4", "small.mp4", width=1280).run()
ff.extract_audio("input.mp4", "audio.mp3").run()
ff.watermark("input.mp4", "logo.png", "branded.mp4").run()
ff.contact_sheet("input.mp4", "sheet.jpg").run()
ff.duck_music("talk.mp4", "music.mp3", "ducked.mp4").run()
ff.social_video("input.mp4", "vertical.mp4", target="vertical").run()
ff.podcast_voice("recording.wav", "finished.wav").run()
ff.add_subtitles("movie.mp4", "subtitles.srt", "captioned.mp4").run()
```

Shortcuts still return normal plans. They support command inspection,
overwrite protection, progress callbacks, and timeouts. The
[Python shortcut guide](docs/shortcuts.md) contains more than 100 copyable calls.

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

## Start with a task

The [documentation index](docs/index.md) groups every guide by the job I am
trying to finish. It also shows the choice between terminal commands, Python
shortcuts, and custom graphs.

The [example guide](docs/examples.md) shows complete inputs and expected
outputs for common jobs:

- Trim a clip or change its size
- Remove video audio or extract it as MP3
- Add a logo, music, fades, or speech ducking
- Join clips or arrange four videos in a grid
- Copy subtitles and call raw FFmpeg filters
- Produce multiple outputs, inspect metadata, and report progress
- Find silent ranges and read analysis reports
- Create owned HLS and DASH artifact directories

The [streaming package guide](docs/streaming.md) explains manifests, segment
files, staged replacement, and the marker that protects unrelated directories.

The [real-world workflow guide](docs/workflows.md) adds 30 paired terminal and
Python examples. It covers social formats, privacy edits, voice cleanup,
subtitles, metadata, image sequences, and podcast audiograms. The
[batch job guide](docs/batch-jobs.md) has folder patterns for CMD, PowerShell,
and Bash, including failure handling and silent inputs. Four staged
[media playbooks](docs/playbooks.md) cover a lesson, podcast, tape review, and
product demo. The
[error guide](docs/errors.md) explains every `FMG` identifier and process exit
code.

For terminal calls, see the [command guide](docs/cli.md). For one-call Python
plans, see the [shortcut guide](docs/shortcuts.md).

## What works today

- Immutable audio, video, and subtitle stream references
- Deterministic `filter_complex` labels and argv compilation
- Typed FFprobe container and stream results
- Owned HLS and DASH artifact sets with failure cleanup
- Synchronous execution with progress callbacks and timeouts
- An installed `flowmpeg` command with editing, inspection, and help groups
- Read-only setup checks with confirmed package manager installation
- Stable CLI error identifiers with bounded failure output
- Audio gain, delay, fades, mixing, and sidechain ducking
- Video trim, canvas fitting, overlays, grids, and compatible concatenation
- Social reframing, privacy blur, boomerang, and frame-rate conversion
- Voice cleanup, audio crossfades, silence trimming, and mono output
- Selectable subtitle extraction, addition, and removal
- Image sequences, podcast audiograms, metadata removal, and audio tags
- Stream-copy tags for video and mixed media files
- Waveform, spectrum, thumbnail, GIF, and contact sheet output
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

Flowmpeg has five public levels:

1. The installed command runs common jobs from a terminal.
2. File shortcuts build plans for the same path-level jobs.
3. `Clip` methods and recipe functions describe media intent.
4. Typed streams form an immutable directed graph.
5. The compiler produces an argv tuple for one FFmpeg process.

Compilation does not read input files, create temporary files, or start a
process. Probing and execution are separate operations. More detail is in the
[design notes](docs/design.md).

Filter outputs have one consumer. Use `split()` or `asplit()` when one filtered
stream needs more than one destination. The compiler reports unused outputs and
fanout before starting FFmpeg.

## Safety defaults

- Existing local outputs are not replaced unless `.overwrite()` or the CLI
  `--overwrite` flag is used.
- Commands run as argv with `shell=False`.
- Tool installation requires `setup --install` and confirmation.
- Displayed commands and captured errors redact URL user information and known
  secret-bearing headers.
- The synchronous runner reserves process pipes for progress and logs.
- Partial outputs are left in place after a failed job.

## Project status

Flowmpeg is pre-alpha. The graph, compiler, and runner contracts are tested,
but the public API may change before the first stable release. Open work and
verified limits are tracked in [ROADMAP.md](ROADMAP.md). Shipped changes are
recorded in [CHANGELOG.md](CHANGELOG.md).

## Development

```console
git clone https://github.com/Imanm02/flowmpeg.git
cd flowmpeg
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests examples
python scripts/content_scan.py
python -m pytest
```

Integration tests create short media files from FFmpeg `lavfi` sources. No
binary test assets are stored in the repository.

See [CONTRIBUTING.md](CONTRIBUTING.md) before preparing a change. Security
reports follow [SECURITY.md](SECURITY.md).

Flowmpeg is available under the [MIT License](LICENSE).
