# Visual guide to Flowmpeg behavior

This page turns stream choices and output behavior into small tables and
diagrams. I use it before a job when a short command name does not make the
mapping or encoding choice obvious.

## Copy, encode, or filter

These are different kinds of work. Copying keeps encoded packet data and is
usually quick. Encoding creates new packet data. A filter first works on
decoded frames or samples, so its stream must be encoded again.

| Command | Video path | Audio path | Filter graph | Main reason to use it |
|---|---|---|---|---|
| `convert` | H.264 encode | AAC encode | No | Make a web MP4 |
| `mute` | Packet copy | Dropped | No | Remove audio without changing video packets |
| `audio` | Dropped | Encode or copy by selected codec | No | Save one audio-only track index |
| `join` | Encode | Encode | `concat` | Join matching decoded formats |
| `clean-metadata` | Packet copy | Packet copy | No | Drop mapped metadata and chapters |
| `captions` | Packet copy | Packet copy | No | Add a selectable MP4 text track |
| `resize` | H.264 encode | AAC encode | `scale` | Change frame dimensions |
| `voice` | Dropped | Encode | Voice filters | Prepare spoken audio |

```mermaid
flowchart LR
    A["Input packets"] --> B{"Does the selected stream use a filter?"}
    B -->|"No, codec copy"| C["Copy packets"]
    B -->|"No, new codec"| D["Decode then encode"]
    B -->|"Yes"| E["Decode"]
    E --> F["Run filters"]
    F --> G["Encode"]
    C --> H["Output container"]
    D --> H
    G --> H
```

For example, this command uses `scale`, so video is encoded again:

```console
flowmpeg resize input.mp4 --width 1280 -o smaller.mp4
```

This command maps video directly with `-c:v copy` and drops audio:

```console
flowmpeg mute input.mp4 -o silent.mp4
```

Use `--dry-run` to inspect the actual FFmpeg command when packet preservation
matters.

## Stream retention and track selection

Flowmpeg selectors use an index within one stream kind. `--track 1` on an
audio command means the second audio stream, not the stream whose absolute
FFprobe index is 1.

Imagine this input:

```text
video-only index 0      V0
audio-only index 0      A0
audio-only index 1      A1
subtitle-only index 0   S0
```

| Command | V0 | A0 | A1 | S0 | Notes |
|---|:---:|:---:|:---:|:---:|---|
| `convert input.mkv -o out.mp4` | Keep | Keep | Drop | Drop | First video and first audio |
| `convert input.mkv --no-audio -o out.mp4` | Keep | Drop | Drop | Drop | Silent output |
| `audio input.mkv --track 1 -o out.mp3` | Drop | Drop | Keep | Drop | Second audio-only index |
| `subtitles input.mkv -o out.srt` | Drop | Drop | Drop | Keep | First subtitle-only index |
| `strip-subtitles input.mkv -o out.mp4` | Keep | Keep | Drop | Drop | Re-encodes the first pair |
| `clean-metadata input.mkv -o out.mkv` | Keep | Keep | Drop | Drop | Copies selected packets |
| `clean-metadata input.mkv --subtitles -o out.mkv` | Keep | Keep | Drop | Keep | Copies the first subtitle too |

Probe before selecting a secondary track:

```console
flowmpeg probe input.mkv
flowmpeg audio input.mkv --track 1 -o second-track.mp3
```

The human probe view prints absolute stream numbers for reference. The typed
Python result also separates `video_streams`, `audio_streams`, and
`subtitle_streams`, which makes audio-only indexing explicit.

## Social frame sizes and fill modes

The `social` command names fixed even dimensions. This makes the output size
predictable before FFmpeg reads the input.

| Target | Width | Height | Ratio | Common placement |
|---|---:|---:|---:|---|
| `vertical` | 1080 | 1920 | 9:16 | Full-screen phone video |
| `portrait` | 1080 | 1350 | 4:5 | Tall feed post |
| `square` | 1080 | 1080 | 1:1 | Square feed post |
| `landscape` | 1920 | 1080 | 16:9 | Standard wide video |

```text
vertical      portrait       square        landscape
+-------+     +---------+    +---------+   +---------------+
|       |     |         |    |         |   |               |
|       |     |         |    |         |   |               |
|       |     |         |    |         |   +---------------+
|       |     +---------+    +---------+
+-------+
```

The fill mode decides what happens when the input and output ratios differ.

| Fill | Keeps the full source frame | Adds a generated background | Crops source edges | Main control |
|---|:---:|:---:|:---:|---|
| `fit` | Yes | Solid color | No | `--color` |
| `blur` | Yes | Blurred source copy | Background only | `--blur` |
| `crop` | No | No | Yes | Centered crop |

```console
flowmpeg social wide.mp4 --target vertical --fill fit --color black -o fit.mp4
flowmpeg social wide.mp4 --target vertical --fill blur --blur 24 -o blur.mp4
flowmpeg social wide.mp4 --target vertical --fill crop -o crop.mp4
```

Use `fit` when every source pixel must remain visible. Use `crop` when filling
the frame matters more than its outer edges. `blur` keeps the full foreground
and fills unused space with a scaled, blurred copy.

## Plan lifecycle and failure path

Building a Python plan does not start a process. Validation and command
inspection happen before the runner boundary.

```mermaid
flowchart TD
    A["Build immutable inputs and filters"] --> B["Validate graph and outputs"]
    B -->|"Invalid"| C["GraphError, FMG200 in CLI"]
    B -->|"Valid"| D{"Choose an action"}
    D -->|"command()"| E["Compile and print redacted command"]
    D -->|"explain()"| F["Describe inputs, filters, and maps"]
    D -->|"run()"| G["Check output conflicts and reserved pipes"]
    G -->|"Conflict"| H["OutputExistsError, exit 4"]
    G -->|"Ready"| I["Start FFmpeg without a shell"]
    I --> J["Read progress and bounded stderr"]
    J -->|"Exit 0"| K["RunResult with outputs and elapsed time"]
    J -->|"Timeout"| L["JobTimeoutError, exit 7"]
    J -->|"FFmpeg failure"| M["ExecutionError, exit 6"]
```

The CLI maps typed failures to stable exit codes. It prints one bounded reason
from FFmpeg and keeps the bounded stderr text on `ExecutionError` for Python
callers. Displayed commands and explanations hide recognized URL credentials,
signed query values, and sensitive header values.

```python
from flowmpeg import shortcuts as ff

plan = ff.resize("input.mp4", "small.mp4", width=1280)
print(plan.command())
print(plan.explain())
result = plan.run(timeout=120)
print(result.elapsed)
```

## Podcast voice chain

`voice` is a fixed one-pass chain for spoken audio. Each stage has a separate
job, so the order matters.

```mermaid
flowchart LR
    A["Selected audio track"] --> B["highpass, remove low rumble"]
    B --> C["lowpass, limit very high content"]
    C --> D{"Denoise enabled?"}
    D -->|"Yes"| E["afftdn, reduce steady noise"]
    D -->|"No"| F{"Compression enabled?"}
    E --> F
    F -->|"Yes"| G["acompressor, reduce level range"]
    F -->|"No"| H["loudnorm, target minus 16 LUFS"]
    G --> H
    H --> I["Encoded audio output"]
```

| Stage | Default control | What a larger value changes |
|---|---:|---|
| High-pass | 80 Hz | Removes more low-frequency content |
| Low-pass | 12000 Hz | A larger cutoff keeps more high-frequency content |
| Noise reduction | 12 dB | Applies stronger steady-noise reduction |
| Compressor ratio | 3:1 | Pushes loud sections closer to quieter sections |
| Loudness target | -16 LUFS | Fixed delivery target in this shortcut |

```console
flowmpeg voice raw.wav -o finished.wav
flowmpeg voice raw.wav --no-denoise --no-compress -o level-only.wav
```

The chain is meant for a useful first pass, not restoration of clipped or
heavily distorted speech. Run `flowmpeg waveform` or inspect the result in an
audio editor when gain changes are important.
