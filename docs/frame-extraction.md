# Owned frame extraction

I use frame sequences for review, visual indexing, animation reference, and
small image datasets. A sequence is one result made of many files, so Flowmpeg
owns a dedicated directory instead of treating each image as an unrelated
output.

## Extract one frame per second

```console
flowmpeg frames input.mp4 -o review-frames
```

The default output is JPEG. Numbering starts at one and uses six digits:

```text
review-frames/
|-- .flowmpeg-artifacts.json
|-- frame-000001.jpg
|-- frame-000002.jpg
|-- frame-000003.jpg
`-- frame-000004.jpg
```

The marker is written only after FFmpeg succeeds and at least one image exists.
It records the `frames` kind, filename pattern, and relative file list.

## Choose a sampling rule

Use an interval when the question is how much source time belongs between
images:

```console
flowmpeg frames lecture.mp4 --interval 10 -o lecture-review
```

Use a rate when the question is how many images should be sampled each second:

```console
flowmpeg frames animation.mp4 --fps 2 -o animation-reference
```

`--interval` and `--fps` cannot be combined.

| Goal | Option | Effective sample rate |
|---|---:|---:|
| One image every minute | `--interval 60` | About 0.0167 fps |
| One image every 10 seconds | `--interval 10` | 0.1 fps |
| One image per second | Default or `--interval 1` | 1 fps |
| Two images per second | `--fps 2` | 2 fps |
| Twelve animation references per second | `--fps 12` | 12 fps |

For a 120-second source, the rough relationship is:

```text
interval 60s  ##                                                    about 2
interval 10s  ############                                          about 12
interval  5s  ########################                              about 24
interval  1s  ####################################################  about 120
```

The actual count can differ by one near a time boundary because FFmpeg applies
its frame-rate filter to source timestamps. Variable-frame-rate inputs can
also place source frames on different timestamp boundaries.

## Extract one bounded section

```console
flowmpeg frames security.mp4 --start 300 --duration 30 --fps 2 -o event-frames
```

This seeks to five minutes, reads a 30-second section, and samples at two
frames per second. Use `--max-frames` as a hard output cap:

```console
flowmpeg frames interview.mp4 --interval 5 --max-frames 20 -o first-20-samples
```

An estimate before the cap is:

```text
estimated count = selected duration * fps
estimated count = selected duration / interval
```

These formulas are planning aids, not a replacement for the reported final
file count.

## Resize the images

```console
flowmpeg frames 4k-source.mp4 --interval 15 --width 640 -o small-review
```

Height follows the source aspect ratio and uses an even value. This is useful
when full-resolution frames would consume unnecessary disk space.

## Choose JPG or PNG

```console
flowmpeg frames input.mp4 --format jpg --quality 3 -o jpg-frames
flowmpeg frames input.mp4 --format png --max-frames 10 -o png-frames
```

JPEG quality uses FFmpeg's 1 through 31 scale. Lower numbers retain more
detail and usually create larger files. `--quality` does not change PNG output,
which is lossless.

| Format | Main tradeoff | Filename pattern |
|---|---|---|
| JPG | Smaller files with lossy encoding | `frame-%06d.jpg` |
| PNG | Lossless images with larger files | `frame-%06d.png` |

## Preview without writing

```console
flowmpeg frames input.mp4 --interval 5 -o review-frames --dry-run
flowmpeg frames input.mp4 --fps 2 --width 960 -o review-frames --dry-run --explain
```

Dry runs do not create the destination directory. The explanation names the
sampling rule, filename pattern, ownership choice, and exact FFmpeg command.

Check the default JPG path before a large job:

```console
flowmpeg doctor --command frames
flowmpeg doctor --require analysis-images
```

The exact command check resolves the alias and checks the default MJPEG
encoder, FPS filter, and image2 muxer. PNG output needs the PNG encoder, which
can be checked in the full doctor capability report.

## Directory safety

An existing directory without a matching marker is never cleared, even when
`--overwrite` is set:

```console
flowmpeg frames input.mp4 -o personal-photos --overwrite
```

That command returns an output-exists error and leaves the directory alone.
An owned replacement uses a sibling stage:

```text
review-frames                     current owned images
.review-frames.flowmpeg-stage-*   new images being extracted
```

The stage replaces the current set only after FFmpeg succeeds, at least one
frame exists, and the new marker is ready. A failure removes the created stage
and keeps the current set. An HLS or DASH directory cannot be replaced by a
frame workflow.

## Use frame extraction in Python

```python
import flowmpeg

workflow = flowmpeg.frame_sequence(
    "input.mp4",
    "review-frames",
    interval=5,
    start=30,
    duration=60,
    width=960,
    max_frames=12,
)

print(workflow.explain())
result = workflow.run(timeout=120)
print(result.pattern)
print(len(result.files))
```

`FrameSet.files` contains final paths after staged replacement. Its embedded
`RunResult.outputs` contains the same final image paths.

## Real-world starting points

| Use case | Starting command | Expected result |
|---|---|---|
| Long lecture review | `frames lecture.mp4 --interval 30` | About two images per minute |
| Animation reference | `frames motion.mp4 --fps 6` | Six sampled images per second |
| Incident window | `frames tape.mp4 --start 600 --duration 20 --fps 2` | About 40 images |
| Small contact dataset | `frames clips.mp4 --interval 5 --width 320 --max-frames 100` | At most 100 small images |
| Lossless inspection | `frames source.mp4 --format png --max-frames 20` | At most 20 PNG files |

Add `-o DIRECTORY` to each abbreviated command in the table.

## Current boundary

This workflow samples frames from one video into one flat directory. It does
not detect scenes, label image contents, create nested class folders, or upload
files. Use `flowmpeg scenes` first when timestamp changes, rather than a fixed
sampling rate, should guide selection.
