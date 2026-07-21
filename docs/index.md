# Flowmpeg documentation

I use this page as the shortest route from a media task to the right command,
Python call, or lower-level graph API.

Start by checking the local tools:

```console
flowmpeg setup
flowmpeg doctor
```

Then browse Flowmpeg's command and example catalogs:

```console
flowmpeg commands
flowmpeg commands --category audio
flowmpeg examples --category composition
flowmpeg examples --search subtitle
```

## Pick a guide by task

| I want to | Start here | What it contains |
|---|---|---|
| Install FFmpeg or use custom paths | [Installation](installation.md) | Platform commands, setup states, CI checks |
| Use forms and local file browsing | [Local browser UI](ui.md) | Search, previews, jobs, presets, keyboard controls |
| Follow UI recipes by result | [UI recipe book](ui-recipes.md) | Inputs, outputs, commands, and why each job helps |
| Reduce large video files | [Size reduction](size-reduction.md) | Phone MOV recipes, CRF choices, codec tradeoffs |
| Run a one-line terminal edit | [Command guide](cli.md) | Every editing command, aliases, controls |
| Read the full command matrix | [Generated command reference](command-reference.md) | Aliases, tags, data kinds, doctor groups |
| Call one Python function | [Shortcut guide](shortcuts.md) | Copyable plan builders and arguments |
| See input and expected output | [Example guide](examples.md) | Files, commands, graph output, explanations |
| Follow a real production sequence | [Workflow guide](workflows.md) | Social, podcast, archive, subtitle jobs |
| Build a staged deliverable | [Media playbooks](playbooks.md) | Lesson, podcast, tape review, product demo |
| Process several files | [Batch jobs](batch-jobs.md) | Native batches, cancellation, shell loops |
| Understand a failure | [Error guide](errors.md) | Exit codes, `FMG` identifiers, recovery steps |
| Extend the graph layer | [Design notes](design.md) | Nodes, streams, compilation, runner boundary |
| Practice custom graphs safely | [Graph lab](graph-lab.md) | Compiled layouts without starting FFmpeg |
| Run local synthetic media jobs | [Demo lab](demo-lab.md) | Composition, delivery, audio, and sequence outputs |
| Check current and planned work | [Roadmap](../ROADMAP.md) | Verified bugs, release gates, current limits |
| See source-backed project counts | [Project statistics](project-stats.md) | Commands, examples, tests, task distribution |
| Compare stream and encoding behavior | [Visual guide](visual-guide.md) | Matrices and data-flow diagrams |
| Find cut points from measured media | [Analysis guide](analysis.md) | Silence intervals, JSON reports, timelines |
| Create streaming media packages | [HLS and DASH](streaming.md) | Manifests, segments, owned replacement rules |
| Extract numbered frame images | [Frame extraction](frame-extraction.md) | Sampling, counts, owned directories |
| Compare encoded visual quality | [PSNR and SSIM](quality.md) | Metrics, alignment, JSON reports |

## Pick an interface

Use the browser UI when form labels, local file browsing, and a visible job
list are useful. Use the terminal command when the job fits on one line and
should run now. Use a Python shortcut when paths or options come from an
application. Use the graph API when one output needs a filter layout that no
shortcut describes.

```text
guided local form    -> flowmpeg ui
one edit now          -> flowmpeg cut ...
one edit in Python    -> ff.trim(...)
custom stream graph   -> input(...), filter(...), output(...)
inspect media first   -> flowmpeg probe ...
check media shape     -> flowmpeg audit ...
find quiet ranges     -> flowmpeg find-silence ...
check local support   -> flowmpeg doctor
```

All editing commands protect existing outputs by default. Add `--dry-run` to
inspect a redacted FFmpeg command without running it. `--explain` prints the
inputs, filters, and mapped outputs before the job runs, so combine it with
`--dry-run` for inspection only. Python shortcut calls return a `Plan`, so
building one does not start FFmpeg.

## Browse by media domain

| Domain | Useful starting commands | Python area |
|---|---|---|
| Video delivery | `shrink`, `shrink-batch`, `compress`, `resize`, `social`, `reframe` | `shrink_video`, `compress_video`, `resize`, `social_video` |
| Timeline edits | `cut`, `speed`, `freeze`, `bounce` | `trim`, `change_speed`, `freeze_end` |
| Audio | `audio`, `mix`, `voice`, `crossfade` | `extract_audio`, `mix_audio_files`, `podcast_voice` |
| Composition | `pip`, `grid`, `mark`, `audiogram` | `picture_in_picture`, `grid`, `watermark` |
| Effects and privacy | `fade`, `color`, `sharpen`, `privacy-blur`, `reverse` | `fade_edges`, `adjust_colors`, `blur_region` |
| Images | `thumb`, `gif`, `sheet`, `waveform` | `thumbnail`, `make_gif`, `contact_sheet` |
| Subtitles | `subtitles`, `captions`, `strip-subtitles` | subtitle shortcut functions |
| Metadata | `clean-metadata`, `tag` | `strip_metadata`, `tag_audio` |
| Inspection | `probe`, `audit`, `loudness`, `find-silence` | Typed reports and intervals |

The command catalog is also available as JSON for shell completion, editor
tools, or documentation checks:

```console
flowmpeg commands --json
flowmpeg commands --category images --json
flowmpeg commands --tag privacy
```

Category and tag filters can be combined. The JSON object has a
`schema_version` field and a `commands` array, including each command's tags.
