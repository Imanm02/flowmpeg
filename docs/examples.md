# Flowmpeg by example

## Create small inputs for these examples

The repository includes a generator based on FFmpeg test sources. It creates a
small fixture set for single-input and multi-input jobs. Run it from a cloned
repository checkout:

```console
git clone https://github.com/Imanm02/flowmpeg.git
cd flowmpeg
python scripts/make_demo_media.py demo-media
```

The command refuses to replace any known output unless `--overwrite` is set.
It also verifies `sample.mp4` with FFprobe and prints a JSON summary.

| Fixture | Media | What it helps test |
|---|---|---|
| `sample.mp4` | Tagged 320 by 180 video with 440 Hz audio | Single-input video and metadata jobs |
| `second.mp4` | 320 by 180 bars with 660 Hz audio | Joins, grids, and transitions |
| `silent.mp4` | 320 by 180 video without audio | Optional audio handling |
| `voice.wav` | 220 Hz WAV | Voice and waveform jobs |
| `music.wav` | 330 Hz WAV | Mixing and crossfades |
| `cover.jpg` | 640 by 360 image | Thumbnails and audiograms |
| `logo.png` | 96 by 96 image with transparency | Watermarks and overlays |
| `captions.srt` | One subtitle cue | Selectable caption jobs |
| `frame-001.png` to `frame-004.png` | Four numbered frames | Sequence input jobs |

Try the generated files with these one-liners:

```console
flowmpeg probe demo-media/sample.mp4
flowmpeg audit demo-media/sample.mp4 --expect av
flowmpeg loudness demo-media/voice.wav
flowmpeg find-silence demo-media/voice.wav --noise-db -45 --minimum 0.2
flowmpeg cut demo-media/sample.mp4 --duration 1 -o demo-media/clip.mp4
flowmpeg loop demo-media/sample.mp4 --duration 3 -o demo-media/looped.mp4
flowmpeg webm demo-media/sample.mp4 -o demo-media/sample.webm
flowmpeg hevc demo-media/sample.mp4 -o demo-media/sample-hevc.mp4
flowmpeg av1 demo-media/sample.mp4 --speed 10 -o demo-media/sample-av1.webm
flowmpeg waveform demo-media/voice.wav -o demo-media/waveform.png
flowmpeg audio demo-media/sample.mp4 --codec opus -o demo-media/audio.opus
flowmpeg resample demo-media/voice.wav --sample-rate 48000 --layout mono -o demo-media/voice-standard.wav
flowmpeg cut-audio demo-media/voice.wav --start 0.1 --duration 0.2 -o demo-media/voice-clip.wav
flowmpeg gain demo-media/voice.wav --gain-db 4 -o demo-media/voice-louder.wav
flowmpeg audio-fade demo-media/music.wav --duration 2 --fade-in 0.2 --fade-out 0.4 -o demo-media/music-faded.wav
flowmpeg sync-audio demo-media/voice.wav --seconds 0.25 -o demo-media/voice-delayed.wav
flowmpeg tempo demo-media/voice.wav --factor 1.5 -o demo-media/voice-fast.wav
flowmpeg audio-join demo-media/voice.wav demo-media/music.wav -o demo-media/program.wav
flowmpeg captions demo-media/sample.mp4 demo-media/captions.srt -o demo-media/captioned.mp4
flowmpeg burn-captions demo-media/sample.mp4 demo-media/captions.srt -o demo-media/open-captioned.mp4
flowmpeg label-media demo-media/sample.mp4 --title "Camera master" -o demo-media/tagged.mp4
flowmpeg remux demo-media/sample.mp4 -o demo-media/archive.mkv
flowmpeg audiogram demo-media/voice.wav demo-media/cover.jpg -o demo-media/audiogram.mp4
flowmpeg join demo-media/sample.mp4 demo-media/second.mp4 -o demo-media/joined.mp4
flowmpeg join-any phone.mp4 camera.mp4 --width 1280 --height 720 -o joined.mp4
flowmpeg mark demo-media/sample.mp4 demo-media/logo.png -o demo-media/branded.mp4
flowmpeg crossfade demo-media/voice.wav demo-media/music.wav --duration 0.5 -o demo-media/blend.wav
```

This guide starts with files and results instead of FFmpeg syntax. Every
example answers the same questions: what files go in, what Python builds the
job, what file comes out, and which FFmpeg operation does the work.

Building a plan does not start FFmpeg. A file is written only after
`plan.run()` is called.

For compact path-to-path calls, the [Python shortcut guide](shortcuts.md)
contains more than 100 variants. The [command guide](cli.md) covers installed
`flowmpeg` calls for CMD and other terminals.

The [real-world workflow guide](workflows.md) adds 30 terminal and Python pairs
for social video, privacy edits, voice cleanup, subtitles, metadata, image
sequences, and podcast audiograms.

The [runnable demo lab](demo-lab.md) applies multi-input and delivery commands
to the generated fixtures, then lists the output shape to check.

```text
input files -> media graph -> plan -> FFmpeg process -> output files
```

## Before running the examples

Install Flowmpeg from GitHub and make sure FFmpeg is on `PATH`:

```console
python -m pip install "git+https://github.com/Imanm02/flowmpeg.git"
flowmpeg doctor
```

The examples use short filenames so the generated commands stay readable.
Paths can also be `pathlib.Path` objects.

## Find an example by result

| I want to create | Input | Output |
| --- | --- | --- |
| A selected time range | `interview.mp4` | `clip.mp4` |
| A repeated motion background | `motion.mp4` | `background.mp4` |
| A smaller video | `interview.mp4` | `small.mp4` |
| An open-codec web video | `interview.mp4` | `delivery.webm` |
| A compact HEVC delivery file | `camera-master.mov` | `camera-hevc.mp4` |
| An AV1 delivery file | `camera-master.mov` | `camera-av1.webm` |
| A silent video | `interview.mp4` | `silent.mp4` |
| An MP3 from a video | `interview.mp4` | `voice.mp3` |
| Standard-rate mono audio | `field.wav` | `field-standard.wav` |
| One exact audio excerpt | `interview.wav` | `answer.wav` |
| A fixed audio gain change | `quiet.wav` | `louder.wav` |
| Music with edge fades | `music.wav` | `music-faded.wav` |
| Audio shifted later | `narration.wav` | `narration-synced.wav` |
| Faster speech with stable pitch | `lesson.wav` | `lesson-fast.wav` |
| Several recordings in sequence | WAV files | `show.wav` |
| A loudness measurement report | `episode.wav` | Terminal text or JSON |
| A silence interval report | `interview.wav` | Terminal text or JSON |
| A video with a logo | `interview.mp4`, `logo.png` | `branded.mp4` |
| A video with background music | `interview.mp4`, `music.mp3` | `with-music.mp4` |
| One podcast mix | Two WAV files | `podcast.wav` |
| Music that lowers under speech | `music.mp3`, `narration.wav` | `ducked.wav` |
| Music with fades | `music.mp3` | `faded.mp3` |
| One joined video | Two MP4 files | `joined.mp4` |
| One timeline from different cameras | Two different video files | `normalized-join.mp4` |
| A 2 by 2 camera grid | Four MP4 files | `grid.mp4` |
| A file that keeps subtitles | `film.mkv` | `film-copy.mkv` |
| A grayscale video | `scene.mp4` | `grayscale.mp4` |
| A video and cover image | `source.mp4` | `web.mp4`, `cover.jpg` |
| A vertical social video | `talk.mp4` | `vertical.mp4` |
| A smaller upload copy | `camera-master.mov` | `upload.mp4` |
| A muted private sentence | `meeting.mp4` | `redacted.mp4` |
| A fixed privacy blur | `driveway.mp4` | `private-driveway.mp4` |
| A finished voice recording | `raw-episode.wav` | `episode.wav` |
| Two tracks with a crossfade | Two WAV files | `program.wav` |
| Selectable MP4 subtitles | MP4 and SRT | `lesson-captioned.mp4` |
| Captions visible in every player | MP4 and SRT | `lesson-open.mp4` |
| A numbered-frame animation | PNG sequence | `animation.mp4` |
| A podcast audiogram | WAV and cover image | `audiogram.mp4` |
| A tagged media copy | `camera.mp4` | `camera-tagged.mp4` |
| The same streams in MKV | `camera.mp4` | `camera.mkv` |

## 1. Inspect a plan before running it

**Input:** `interview.mp4`

**Output:** Nothing until `run()` is called. The code prints the planned job.

```python
from flowmpeg import media

plan = media("interview.mp4").scale(width=1280).output(
    "small.mp4",
    preset="web",
)

plan.validate()
print(plan.explain())
print(plan.filter_graph())
print(plan.command())
```

`explain()` prints:

```text
Inputs:
  0: interview.mp4
Filters:
  scale
Outputs:
  small.mp4: 2 mapped stream(s)
Overwrite: no
```

`filter_graph()` prints:

```text
[0:v:0]scale=1280:-2[v0]
```

The `-2` asks FFmpeg to calculate an even height that preserves the source
aspect ratio. `command()` is intended for logs and review. `raw_argv()` returns
the exact argument tuple when another process API needs it.

## 2. Keep one time range

**Input:** `interview.mp4`, with video and audio.

**Output:** `clip.mp4`, containing seconds 30 through 90. Its timeline starts
at zero and its expected duration is 60 seconds.

```python
from flowmpeg import media

plan = (
    media("interview.mp4")
    .trim(start=30, end=90)
    .output("clip.mp4", preset="web")
)

print(plan.command())
plan.run(expected_duration=60)
```

Flowmpeg trims both streams and resets both timestamps. The generated filter
graph contains:

```text
[0:v:0]trim=start=30:end=90[v0];[v0]setpts=PTS-STARTPTS[v1];[0:a:0]atrim=start=30:end=90[a0];[a0]asetpts=PTS-STARTPTS[a1]
```

Keeping the two timestamp resets visible makes later overlays and concatenation
easier to reason about.

## 3. Resize while keeping the original aspect ratio

**Input:** `interview.mp4`

**Output:** `small.mp4`, 1280 pixels wide. The height is calculated by FFmpeg.
The source audio is retained.

```python
from flowmpeg import media

plan = media("interview.mp4").scale(width=1280).output(
    "small.mp4",
    preset="web",
)
plan.run()
```

Set only `height` to calculate the width instead:

```python
plan = media("portrait.mp4").scale(height=1080).output(
    "portrait-1080.mp4",
    preset="web",
)
```

Set both values when the exact dimensions matter. This may change the aspect
ratio:

```python
plan = media("source.mp4").scale(width=1920, height=1080).output(
    "fixed-size.mp4",
    preset="web",
)
```

## 4. Remove audio without re-encoding video

**Input:** `interview.mp4`

**Output:** `silent.mp4`, containing only the first video stream. The video
packets are copied, so this operation avoids a video quality change.

```python
from flowmpeg import media

plan = media("interview.mp4", audio=False).output(
    "silent.mp4",
    args=("-c:v", "copy"),
)

print(plan.command())
plan.run()
```

The important command arguments are:

```text
-map 0:v:0 -c:v copy silent.mp4
```

`audio=False` controls stream selection. `-c:v copy` controls encoding.

## 5. Extract audio as MP3

**Input:** `interview.mp4`

**Output:** `voice.mp3`, made from the first audio stream. No video stream is
mapped.

```python
from flowmpeg import input, output

source = input("interview.mp4")
plan = output(
    source.audio(),
    to="voice.mp3",
    args=("-c:a", "libmp3lame", "-q:a", "2"),
)

print(plan.command())
plan.run()
```

The important command arguments are:

```text
-map 0:a:0 -c:a libmp3lame -q:a 2 voice.mp3
```

Use `source.audio(1)` when the required track is the second audio stream.

## 6. Add a logo

**Inputs:** `interview.mp4` and a transparent `logo.png`.

**Output:** `branded.mp4`, with the logo placed 32 pixels from the bottom-right
corner at 85 percent opacity. The interview audio is retained.

```python
from flowmpeg import media

logo = media("logo.png", "-loop", "1", audio=False)

plan = (
    media("interview.mp4")
    .overlay(
        logo,
        position="bottom-right",
        padding=32,
        opacity=0.85,
    )
    .output("branded.mp4", preset="web")
)

plan.run()
```

`-loop 1` is an input argument for the image. It appears before the image's
`-i` argument. The generated graph contains:

```text
[1:v:0]format=pix_fmts=rgba[v0];[v0]colorchannelmixer=aa=0.85[v1];[0:v:0][v1]overlay=x=W-w-32:y=H-h-32:shortest=0:eof_action=repeat[v2]
```

The named positions are `top-left`, `top-right`, `bottom-left`,
`bottom-right`, and `center`.

## 7. Add quiet background music

**Inputs:** `interview.mp4` and `music.mp3`.

**Output:** `with-music.mp4`, with the original interview audio mixed with music
at 12 percent of its source level. The mix follows the interview audio length.

```python
from flowmpeg import media

music = media("music.mp3", video=False)

plan = (
    media("interview.mp4")
    .mix_audio(
        music,
        addition_volume=0.12,
        duration="first",
    )
    .output("with-music.mp4", preset="web")
)

plan.run()
```

Flowmpeg adds `volume` and `amix` filters. The video is not passed through a
filter because only the audio changes.

## 8. Mix two spoken tracks

**Inputs:** `host.wav` and `guest.wav`. The guest recording starts 400
milliseconds too early and is slightly louder than needed.

**Output:** `podcast.wav`, with the guest delayed and lowered before both tracks
are mixed.

```python
from flowmpeg import delay_audio, input, mix_audio, output, volume

host = input("host.wav").audio()
guest = input("guest.wav").audio()
guest = delay_audio(volume(guest, factor=0.85), seconds=0.4)

mixed = mix_audio(
    host,
    guest,
    weights=(1.0, 0.9),
    duration="longest",
    normalize=False,
)

plan = output(
    mixed,
    to="podcast.wav",
    args=("-c:a", "pcm_s16le"),
)
plan.run()
```

`delay_audio` converts seconds to the millisecond value expected by FFmpeg's
`adelay` filter. The explicit weights make the balance visible in Python.

## 9. Lower music while narration is active

**Inputs:** `music.mp3` as the program and `narration.wav` as the sidechain.

**Output:** `ducked.wav`, containing both tracks. Music level drops when speech
crosses the compression threshold.

```python
from flowmpeg import duck_audio, input, output

music = input("music.mp3").audio()
narration = input("narration.wav").audio()

ducked = duck_audio(
    music,
    narration,
    threshold=0.08,
    ratio=10,
    attack=15,
    release=300,
)

plan = output(
    ducked,
    to="ducked.wav",
    args=("-c:a", "pcm_s16le"),
)
plan.run()
```

The default ducking recipe expands into three stages:

```text
narration -> asplit -> sidechaincompress control
music + control -> compressed music
compressed music + narration -> amix -> output
```

The split is required because the narration feeds both the compressor and the
final mix.

## 10. Add fade-in and fade-out

**Input:** `music.mp3`, expected to be 30 seconds long.

**Output:** `faded.mp3`, with a two-second fade-in and a three-second fade-out.

```python
from flowmpeg import fade_audio, input, output

music = input("music.mp3").audio()
music = fade_audio(music, fade_type="in", start=0, duration=2)
music = fade_audio(music, fade_type="out", start=27, duration=3)

plan = output(
    music,
    to="faded.mp3",
    args=("-c:a", "libmp3lame", "-q:a", "2"),
)
plan.run(expected_duration=30)
```

The fade-out start is an absolute time in the filtered stream. Probe the input
first when its duration is not already known.

## 11. Join compatible clips

**Inputs:** `part-1.mp4` and `part-2.mp4` with matching video dimensions, frame
rate, audio sample rate, and channel layout.

**Output:** `joined.mp4`, with the second clip following the first.

```python
from flowmpeg import concat_clips, media

joined = concat_clips(
    media("part-1.mp4"),
    media("part-2.mp4"),
)

plan = joined.output("joined.mp4", preset="web")
plan.run()
```

The recipe resets every input timeline before creating one FFmpeg `concat`
filter. FFmpeg requires the connected stream formats to match. Probe the files
before joining when they came from different cameras or editors.

## 12. Build a 2 by 2 video grid

**Inputs:** `camera-1.mp4` through `camera-4.mp4`.

**Output:** `grid.mp4`, a 1280 by 720 canvas with four 640 by 360 video cells.
This example does not map audio.

```python
from flowmpeg import input, output, scale, stack_video

cameras = [
    scale(
        input(f"camera-{number}.mp4").video(),
        width=640,
        height=360,
    )
    for number in range(1, 5)
]

grid = stack_video(*cameras, columns=2, fill="black")
plan = output(
    grid,
    to="grid.mp4",
    args=("-c:v", "libx264", "-pix_fmt", "yuv420p"),
)
plan.run()
```

The generated `xstack` layout is:

```text
0_0|w0_0|0_h0|w2_h0
```

Each entry gives the top-left position of one cell. `w0` and `h0` refer to the
width and height of an earlier input.

## 13. Keep a subtitle stream

**Input:** `film.mkv` with video, audio, and at least one subtitle stream.

**Output:** `film-copy.mkv`, containing the first stream of each kind. No stream
is re-encoded.

```python
from flowmpeg import input, output

film = input("film.mkv")
plan = output(
    film.video(),
    film.audio(),
    film.subtitle(),
    to="film-copy.mkv",
    args=("-c", "copy"),
)

print(plan.command())
plan.run()
```

The stream mappings are explicit:

```text
-map 0:v:0 -map 0:a:0 -map 0:s:0 -c copy film-copy.mkv
```

Use `film.subtitle(1)` to select the second subtitle stream.

## 14. Call an FFmpeg filter directly

**Input:** `scene.mp4`

**Output:** `grayscale.mp4`, with grayscale video and the original audio.

```python
from flowmpeg import input, output

scene = input("scene.mp4")
video = scene.video().filter("eq", contrast=1.08, saturation=0)
video = video.filter("unsharp", 5, 5, 1.0)

plan = output(
    video,
    scene.audio(),
    to="grayscale.mp4",
    args=("-c:v", "libx264", "-c:a", "aac"),
)
plan.run()
```

`filter()` is the escape hatch for filters that do not yet have a named
Flowmpeg recipe. Positional values are written before named options, matching
FFmpeg filter syntax.

## 15. Create a video and cover image in one process

**Input:** `source.mp4`

**Outputs:** `web.mp4`, scaled to 1280 pixels wide, and `cover.jpg`, made from
the first scaled frame.

```python
from flowmpeg import input, output, scale

source = input("source.mp4")
scaled = scale(source.video(), width=1280)
web_video, cover_frame = scaled.split()

plan = output(
    web_video,
    source.audio(),
    to="web.mp4",
    args=("-c:v", "libx264", "-c:a", "aac"),
).add_output(
    cover_frame,
    to="cover.jpg",
    args=("-frames:v", "1", "-q:v", "2"),
)

print(plan.explain())
plan.run()
```

The filtered video is split because each filter output has one consumer. The
result is one FFmpeg command with two output declarations:

```text
Outputs:
  web.mp4: 2 mapped stream(s)
  cover.jpg: 1 mapped stream(s)
Overwrite: no
```

## 16. Read media information before building a plan

**Input:** `source.mp4`

**Output:** Python values only. FFprobe reads the file, but FFmpeg is not
started.

```python
from flowmpeg import probe

info = probe("source.mp4", timeout=10)

print(info.duration)
print(len(info.video_streams))
print(len(info.audio_streams))

video = info.video_streams[0]
print(video.codec_name)
print(video.width, video.height)
print(float(video.average_frame_rate) if video.average_frame_rate else None)
```

A representative result could be:

```text
42.08
1
1
h264
1920 1080
29.97002997002997
```

Probe results use typed objects. Missing FFprobe fields become `None`, so code
should check fields that are not guaranteed by the container.

## 17. Show progress and set a timeout

**Input:** `source.mp4`

**Output:** `encoded.mp4` plus progress lines while FFmpeg runs.

```python
from flowmpeg import Progress, media, probe


def report(event: Progress) -> None:
    if event.percent is not None:
        print(f"{event.percent:5.1f}% at {event.speed or 0:.2f}x")


duration = probe("source.mp4").duration
plan = media("source.mp4").output("encoded.mp4", preset="web")

result = plan.run(
    expected_duration=duration,
    on_progress=report,
    timeout=300,
)

print(result.returncode)
print(result.elapsed)
print(result.outputs)
```

Representative progress output:

```text
 12.4% at 2.31x
 48.7% at 2.44x
 93.8% at 2.39x
100.0% at 2.40x
```

Flowmpeg reads FFmpeg's `-progress` protocol. It does not parse the changing
human status line from stderr.

## 18. Choose output replacement behavior

Flowmpeg refuses to replace a local output by default:

```python
from flowmpeg import OutputExistsError, media

plan = media("source.mp4").output("encoded.mp4", preset="web")

try:
    plan.run()
except OutputExistsError as error:
    print(error)
```

Expected message when the file exists:

```text
Output already exists: encoded.mp4
```

Replacement must be selected on the plan:

```python
plan.overwrite().run()
```

This compiles FFmpeg's `-y` flag instead of the default `-n` flag.

## Reading a failed job

Execution errors include the FFmpeg exit code, a bounded stderr tail, and a
display-safe command:

```python
from flowmpeg import ExecutionError, media

plan = media("broken.mp4").output("result.mp4", preset="web")

try:
    plan.run(timeout=60)
except ExecutionError as error:
    print(error.returncode)
    print(error.command)
    print(error.stderr)
```

Credentials in known URL and header locations are hidden in displayed commands
and captured error text. `raw_argv()` is not redacted because it is intended for
direct process execution.
