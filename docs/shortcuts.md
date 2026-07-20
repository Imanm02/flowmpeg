# One-line shortcuts

Flowmpeg shortcuts turn common file-to-file jobs into one Python call. Each
shortcut returns a `Plan`, so the command can still be inspected before FFmpeg
starts.

```python
from flowmpeg import shortcuts as ff

ff.trim("input.mp4", "clip.mp4", start=10, end=30).run()
```

That line reads `input.mp4`, keeps seconds 10 through 30, encodes an MP4, and
writes `clip.mp4`.

## The five rules

1. A shortcut builds a plan. It does not start a process until `.run()`.
2. Existing outputs are protected unless `overwrite=True` is explicit.
3. Video shortcuts use the tested `web` MP4 preset.
4. Stream selection is explicit. Most shortcuts select the first stream of the
   required kind.
5. A missing stream is reported by FFmpeg at execution time. Building a plan
   does not probe the input.

The examples below assume this import:

```python
from flowmpeg import shortcuts as ff
```

## Video conversion and timing

### Encode a MOV as web MP4

**Input:** `recording.mov`

**Output:** `recording.mp4` with H.264 video and AAC audio.

```python
ff.transcode("recording.mov", "recording.mp4").run()
```

### Encode a video that has no audio

**Input:** `animation.mov`, containing video only.

**Output:** `animation.mp4`, without an audio stream.

```python
ff.transcode("animation.mov", "animation.mp4", include_audio=False).run()
```

### Keep an exact time range

**Input:** `interview.mp4`

**Output:** `answer.mp4`, containing seconds 42 through 68.

```python
ff.trim("interview.mp4", "answer.mp4", start=42, end=68).run()
```

Video and audio timestamps are reset to zero after trimming.

### Keep a duration from a start time

**Input:** `meeting.mp4`

**Output:** `moment.mp4`, containing 15 seconds beginning at 90 seconds.

```python
ff.trim("meeting.mp4", "moment.mp4", start=90, duration=15).run()
```

### Trim a silent video

**Input:** `timelapse.mp4`, without audio.

**Output:** `short-timelapse.mp4`, containing its first eight seconds.

```python
ff.trim("timelapse.mp4", "short-timelapse.mp4", duration=8, include_audio=False).run()
```

### Resize by width

**Input:** `camera.mp4`

**Output:** `camera-720p.mp4`, 1280 pixels wide with a calculated even height.

```python
ff.resize("camera.mp4", "camera-720p.mp4", width=1280).run()
```

### Resize by height

**Input:** `portrait.mp4`

**Output:** `portrait-1080.mp4`, 1080 pixels high with a calculated even width.

```python
ff.resize("portrait.mp4", "portrait-1080.mp4", height=1080).run()
```

The shortcut accepts one dimension because setting both could stretch the
image. Use the stream API when stretching is intended.

### Slow video and audio to half speed

**Input:** `action.mp4`

**Output:** `slow.mp4`, expected to last about twice as long.

```python
ff.change_speed("action.mp4", "slow.mp4", factor=0.5).run()
```

### Speed up by 50 percent

**Input:** `lesson.mp4`

**Output:** `faster.mp4`, with paired video and audio at 1.5 times speed.

```python
ff.change_speed("lesson.mp4", "faster.mp4", factor=1.5).run()
```

### Speed up by four times

**Input:** `process.mp4`

**Output:** `fast.mp4`. Audio uses two compatible `atempo=2` stages.

```python
ff.change_speed("process.mp4", "fast.mp4", factor=4).run()
```

### Rotate clockwise

**Input:** `sideways.mp4`

**Output:** `upright.mp4`, rotated 90 degrees clockwise.

```python
ff.rotate("sideways.mp4", "upright.mp4", degrees=90).run()
```

### Rotate by a half turn

```python
ff.rotate("upside-down.mp4", "fixed.mp4", degrees=180).run()
```

### Rotate counterclockwise

`270` clockwise is the same displayed turn as 90 degrees counterclockwise.

```python
ff.rotate("sideways.mp4", "left-turn.mp4", degrees=270).run()
```

### Crop from the center

**Input:** `wide.mp4`

**Output:** `center.mp4`, with a centered 1080 by 1080 video region.

```python
ff.crop("wide.mp4", "center.mp4", width=1080, height=1080).run()
```

### Crop from fixed coordinates

**Output:** `corner.mp4`, with a 640 by 360 region starting at x 100 and y 50.

```python
ff.crop("wide.mp4", "corner.mp4", width=640, height=360, x=100, y=50).run()
```

## Audio shortcuts

### Remove audio

**Input:** `interview.mp4`

**Output:** `silent.mp4`, with the video stream copied and audio removed.

```python
ff.remove_audio("interview.mp4", "silent.mp4").run()
```

This removes the audio stream. It does not add a silent audio track.

### Extract MP3 audio

**Input:** `interview.mp4`

**Output:** `interview.mp3`, encoded at 192 kbit/s.

```python
ff.extract_audio("interview.mp4", "interview.mp3").run()
```

### Extract MP3 at another bitrate

```python
ff.extract_audio("interview.mp4", "small.mp3", bitrate="96k").run()
```

### Extract AAC audio

```python
ff.extract_audio("movie.mkv", "soundtrack.m4a", codec="aac").run()
```

### Extract uncompressed WAV audio

```python
ff.extract_audio("lesson.mp4", "lesson.wav", codec="wav").run()
```

### Extract FLAC audio

```python
ff.extract_audio("concert.mkv", "concert.flac", codec="flac").run()
```

### Copy an audio stream without encoding

**Input:** `source.mkv`

**Output:** `track.mka`, containing the source audio packets.

```python
ff.extract_audio("source.mkv", "track.mka", codec="copy").run()
```

The destination container must accept the source codec.

### Select another audio track

`track=1` selects the second audio stream because stream indexes start at zero.

```python
ff.extract_audio("movie.mkv", "commentary.mp3", track=1).run()
```

### Replace a video's audio

**Inputs:** `video.mp4` and `narration.wav`.

**Output:** `narrated.mp4`. Video is copied, narration becomes AAC, and short
narration is padded to the video duration.

```python
ff.replace_audio("video.mp4", "narration.wav", "narrated.mp4").run()
```

### Replace audio and stop at the shorter stream

```python
ff.replace_audio("video.mp4", "music.m4a", "shortest.mp4", duration="shortest", audio_codec="copy").run()
```

This copy mode requires replacement audio that is accepted by MP4.

### Add quiet background music

**Inputs:** `talk.mp4` with audio and `music.mp3`.

**Output:** `scored.mp4`, with music at 15 percent of its input level.

```python
ff.add_music("talk.mp4", "music.mp3", "scored.mp4").run()
```

### Use a different music level

```python
ff.add_music("talk.mp4", "music.mp3", "louder-music.mp4", music_volume=0.3).run()
```

### Lower the source while adding music

```python
ff.add_music("talk.mp4", "music.mp3", "balanced.mp4", source_volume=0.8, music_volume=0.2).run()
```

### Loop short music under the full source

```python
ff.add_music("long-talk.mp4", "short-music.mp3", "looped.mp4", loop_music=True).run()
```

The music input receives `-stream_loop -1`, and the final mix follows the
source audio duration.

### Add music to a video with no audio

**Input:** `silent.mp4`, containing only video.

**Output:** `with-music.mp4`. Short music is padded, and long music stops with
the video.

```python
ff.add_music("silent.mp4", "music.mp3", "with-music.mp4", source_has_audio=False).run()
```

### Mix two WAV files

```python
ff.mix_audio_files(["host.wav", "guest.wav"], "conversation.wav").run()
```

### Mix three files with visible volume settings

```python
ff.mix_audio_files(["host.wav", "guest.wav", "music.wav"], "show.wav", volumes=[1, 0.9, 0.12]).run()
```

### Mix directly to MP3

```python
ff.mix_audio_files(["left.wav", "right.wav"], "mix.mp3", codec="mp3", bitrate="256k").run()
```

### Follow the shortest audio input

```python
ff.mix_audio_files(["one.wav", "two.wav"], "short.wav", duration="shortest").run()
```

### Normalize spoken audio to minus 16 LUFS

**Input:** `voice.wav`

**Output:** `normalized.wav` at 48 kHz.

```python
ff.normalize_loudness("voice.wav", "normalized.wav").run()
```

### Normalize to MP3

```python
ff.normalize_loudness("voice.wav", "normalized.mp3", codec="mp3").run()
```

### Use a broadcast loudness target

```python
ff.normalize_loudness("program.wav", "broadcast.wav", integrated=-23, true_peak=-2).run()
```

This shortcut uses one-pass FFmpeg `loudnorm`. Measured two-pass normalization
will require a multi-plan workflow.

## Composition and images

### Place a logo in the top-right corner

**Inputs:** `video.mp4` and `logo.png`.

**Output:** `branded.mp4`, with 24 pixels of padding.

```python
ff.watermark("video.mp4", "logo.png", "branded.mp4").run()
```

### Place a logo in the bottom-right corner

```python
ff.watermark("video.mp4", "logo.png", "bottom-right.mp4", position="bottom-right").run()
```

### Center a transparent watermark

```python
ff.watermark("video.mp4", "mark.png", "centered.mp4", position="center", opacity=0.4).run()
```

### Resize a large logo before overlaying it

```python
ff.watermark("video.mp4", "large-logo.png", "small-logo.mp4", width=180).run()
```

### Watermark a video without audio

```python
ff.watermark("silent.mp4", "logo.png", "marked-silent.mp4", include_audio=False).run()
```

The still image is not looped as an input. FFmpeg's overlay filter repeats its
final frame until the main video ends.

### Join two matching clips

**Inputs:** `part-1.mp4` and `part-2.mp4` with matching decoded formats.

**Output:** `joined.mp4`, with both video and audio joined.

```python
ff.join_matching(["part-1.mp4", "part-2.mp4"], "joined.mp4").run()
```

### Join three matching silent clips

```python
ff.join_matching(["one.mp4", "two.mp4", "three.mp4"], "joined.mp4", include_audio=False).run()
```

`join_matching` does not probe or repair different resolutions, frame rates,
pixel formats, sample rates, or channel layouts. Its name keeps that rule
visible.

### Place two videos side by side

**Inputs:** `left.mp4` and `right.mp4`.

**Output:** `side-by-side.mp4`, with two 640 by 360 cells and no audio.

```python
ff.grid(["left.mp4", "right.mp4"], "side-by-side.mp4", columns=2).run()
```

### Build a 2 by 2 grid

```python
ff.grid(["one.mp4", "two.mp4", "three.mp4", "four.mp4"], "grid.mp4").run()
```

### Build smaller grid cells

```python
ff.grid(["one.mp4", "two.mp4", "three.mp4"], "small-grid.mp4", columns=3, cell_width=320, cell_height=180).run()
```

### Continue until the longest grid input ends

The default grid stops when its shortest input ends. Set `shortest=False` to
use FFmpeg's normal framesync ending behavior.

```python
ff.grid(["short.mp4", "long.mp4"], "long-grid.mp4", shortest=False).run()
```

### Save the first frame as JPEG

```python
ff.thumbnail("video.mp4", "cover.jpg").run()
```

### Save a frame at 12.5 seconds

```python
ff.thumbnail("video.mp4", "moment.jpg", at=12.5).run()
```

### Save a resized PNG frame

```python
ff.thumbnail("video.mp4", "moment.png", at=8, width=640).run()
```

### Change JPEG quality

FFmpeg JPEG quality uses smaller numbers for higher quality.

```python
ff.thumbnail("video.mp4", "high-quality.jpg", at=3, quality=1).run()
```

### Create a five-second GIF

**Input:** `demo.mp4`

**Output:** `preview.gif`, using the first five seconds at 12 frames per second
and 480 pixels wide.

```python
ff.make_gif("demo.mp4", "preview.gif").run()
```

### Create a GIF from another time range

```python
ff.make_gif("demo.mp4", "feature.gif", start=20, duration=3).run()
```

### Create a smaller low-frame-rate GIF

```python
ff.make_gif("demo.mp4", "small.gif", width=320, fps=8).run()
```

### Convert the full video to GIF

```python
ff.make_gif("short-demo.mp4", "complete.gif", duration=None).run()
```

### Create a GIF that does not loop

For the FFmpeg GIF muxer, `-1` means no loop and `0` means infinite looping.

```python
ff.make_gif("demo.mp4", "once.gif", loop=-1).run()
```

## Canvas, analysis, and finishing shortcuts

### Fit portrait video inside a wide canvas

**Input:** `portrait.mp4`

**Output:** `portrait-wide.mp4`, a 1920 by 1080 video with the source centered
over black padding. The source aspect ratio is kept.

```python
ff.fit_canvas("portrait.mp4", "portrait-wide.mp4").run()
```

### Fit a smaller white canvas

```python
ff.fit_canvas(
    "square.mp4",
    "square-wide.mp4",
    width=1280,
    height=720,
    color="white",
).run()
```

Canvas dimensions must be positive even integers because the web preset uses
the YUV 4:2:0 pixel format.

### Fit a silent source

```python
ff.fit_canvas(
    "animation.mp4",
    "animation-wide.mp4",
    include_audio=False,
).run()
```

### Add picture in picture

**Inputs:** `main.mp4` and `camera.mp4`.

**Output:** `with-camera.mp4`, with a 480 pixel wide inset at the bottom-right.
The main video's audio is retained.

```python
ff.picture_in_picture("main.mp4", "camera.mp4", "with-camera.mp4").run()
```

### Move and resize the inset

```python
ff.picture_in_picture(
    "main.mp4",
    "camera.mp4",
    "top-camera.mp4",
    inset_width=320,
    position="top-left",
    padding=16,
).run()
```

### Make the inset translucent

```python
ff.picture_in_picture(
    "main.mp4",
    "camera.mp4",
    "soft-camera.mp4",
    opacity=0.75,
).run()
```

When the inset ends first, the main video continues without a frozen inset.

### Draw a waveform image

**Input:** `song.mp3`

**Output:** `waveform.png`, a 1200 by 400 peak waveform from the first audio
track.

```python
ff.waveform_image("song.mp3", "waveform.png").run()
```

### Choose waveform size and color

```python
ff.waveform_image(
    "song.mp3",
    "wide-waveform.png",
    width=1600,
    height=500,
    color="yellow",
).run()
```

### Split channels and use logarithmic scale

```python
ff.waveform_image(
    "movie.mkv",
    "commentary-waveform.png",
    track=1,
    split_channels=True,
    scale_mode="log",
).run()
```

The output may be JPEG, PNG, or WebP.

### Draw a frequency spectrum

**Input:** `song.mp3`

**Output:** `spectrum.png`, a 1600 by 900 combined-channel spectrum with a
legend.

```python
ff.spectrum_image("song.mp3", "spectrum.png").run()
```

### Draw separate spectrum channels

```python
ff.spectrum_image(
    "song.mp3",
    "separate-spectrum.png",
    mode="separate",
    color="magma",
    legend=False,
).run()
```

### Draw a compact spectrum

```python
ff.spectrum_image(
    "voice.wav",
    "voice-spectrum.jpg",
    width=1000,
    height=400,
    color="viridis",
).run()
```

### Create video from one image and audio

**Inputs:** `cover.jpg` and `episode.mp3`.

**Output:** `episode.mp4`, a 1920 by 1080 video that ends with the audio.

```python
ff.still_image_video("cover.jpg", "episode.mp3", "episode.mp4").run()
```

### Use another canvas and track

```python
ff.still_image_video(
    "cover.png",
    "album.mka",
    "track-video.mp4",
    track=1,
    width=1280,
    height=720,
    color="white",
).run()
```

### Set the image frame rate

```python
ff.still_image_video(
    "cover.jpg",
    "speech.wav",
    "speech-video.mp4",
    frame_rate=30,
).run()
```

The still image input is looped, while `-shortest` ends the result with the
selected audio stream.

### Build a contact sheet

**Input:** `movie.mp4`

**Output:** `sheet.jpg`, a 4 by 4 image sampled every five seconds.

```python
ff.contact_sheet("movie.mp4", "sheet.jpg").run()
```

### Change the contact sheet layout

```python
ff.contact_sheet(
    "movie.mp4",
    "overview.jpg",
    columns=5,
    rows=3,
    interval=10,
    cell_width=240,
    cell_height=135,
).run()
```

### Change spacing and background color

```python
ff.contact_sheet(
    "movie.mp4",
    "spaced-sheet.png",
    columns=3,
    rows=3,
    padding=8,
    margin=16,
    color="white",
).run()
```

The shortcut samples from the beginning. If the source ends before every cell
is filled, FFmpeg may produce fewer populated cells.

### Lower music while speech is active

**Inputs:** `talk.mp4` and `music.mp3`.

**Output:** `ducked.mp4`, with music lowered while source speech crosses the
compression threshold.

```python
ff.duck_music("talk.mp4", "music.mp3", "ducked.mp4").run()
```

### Tune ducking response

```python
ff.duck_music(
    "talk.mp4",
    "music.mp3",
    "tuned-duck.mp4",
    music_volume=0.4,
    threshold=0.08,
    ratio=10,
    attack=15,
    release=300,
).run()
```

### Keep the original music length

Music loops by default. Disable looping when that is not wanted.

```python
ff.duck_music(
    "talk.mp4",
    "music.mp3",
    "one-pass-music.mp4",
    loop_music=False,
).run()
```

The speech track is split because it controls the compressor and remains in
the final mix.

### Trim and fade both clip edges

**Input:** `source.mp4`

**Output:** `faded.mp4`, a ten-second clip beginning at second 20 with matched
one-second video and audio fades.

```python
ff.fade_edges(
    "source.mp4",
    "faded.mp4",
    start=20,
    duration=10,
).run()
```

### Set different fade lengths

```python
ff.fade_edges(
    "source.mp4",
    "custom-fades.mp4",
    duration=12,
    fade_in=0.5,
    fade_out=2,
).run()
```

### Fade a silent video

```python
ff.fade_edges(
    "animation.mp4",
    "faded-animation.mp4",
    duration=8,
    include_audio=False,
).run()
```

The combined fade lengths cannot exceed the selected duration.

### Fill a wide canvas with a blurred copy

**Input:** `portrait.mp4`

**Output:** `blurred-wide.mp4`, with the full portrait video over a blurred
1920 by 1080 background made from the same frames.

```python
ff.blurred_background("portrait.mp4", "blurred-wide.mp4").run()
```

### Set another canvas and blur strength

```python
ff.blurred_background(
    "portrait.mp4",
    "soft-background.mp4",
    width=1280,
    height=720,
    blur=12,
).run()
```

### Blur a silent source

```python
ff.blurred_background(
    "animation.mp4",
    "blurred-animation.mp4",
    include_audio=False,
).run()
```

### Reverse a bounded clip

**Input:** `action.mp4`

**Output:** `reverse.mp4`, containing six reversed seconds beginning at second
12.

```python
ff.reverse_clip(
    "action.mp4",
    "reverse.mp4",
    start=12,
    duration=6,
).run()
```

### Reverse video without audio

```python
ff.reverse_clip(
    "animation.mp4",
    "reverse-animation.mp4",
    duration=4,
    include_audio=False,
).run()
```

Reverse filters buffer the selected media. The shortcut requires a duration
and limits it to 60 seconds.

## Inspect or control any shortcut

Every shortcut returns the same `Plan` used by the graph API.

### Print the safe command

```python
print(ff.trim("input.mp4", "clip.mp4", start=5, end=10).command())
```

### Print the generated filter graph

```python
print(ff.watermark("input.mp4", "logo.png", "output.mp4").filter_graph())
```

### Read the job explanation

```python
print(ff.grid(["one.mp4", "two.mp4"], "grid.mp4").explain())
```

### Validate without reading input files

```python
ff.change_speed("input.mp4", "fast.mp4", factor=2).validate()
```

### Allow replacement in the shortcut call

```python
ff.resize("input.mp4", "output.mp4", width=1280, overwrite=True).run()
```

### Allow replacement on the returned plan

```python
ff.resize("input.mp4", "output.mp4", width=1280).overwrite().run()
```

### Stop a long job after 60 seconds

```python
ff.transcode("input.mov", "output.mp4").run(timeout=60)
```

### Add a progress callback

```python
from flowmpeg import Progress


def report(event: Progress) -> None:
    if event.percent is not None:
        print(f"{event.percent:.1f}%")


ff.trim("input.mp4", "clip.mp4", start=5, duration=20).run(
    expected_duration=20,
    on_progress=report,
)
```

## Shortcut reference

| Shortcut | Main result | Stream behavior |
| --- | --- | --- |
| `transcode` | Web MP4 | Encodes selected video and optional audio |
| `trim` | Accurate time range | Filters paired timestamps, then encodes |
| `resize` | New width or height | Encodes video and keeps optional audio |
| `remove_audio` | Video-only file | Copies video and drops other streams |
| `extract_audio` | MP3, AAC, WAV, FLAC, or copy | Maps one audio track |
| `replace_audio` | MP4 with another track | Copies video and replaces original audio |
| `watermark` | Branded MP4 | Encodes overlay video and keeps optional audio |
| `add_music` | MP4 with mixed or new music | Encodes audio and video |
| `join_matching` | Joined MP4 | Filters compatible streams and encodes |
| `mix_audio_files` | One mixed audio file | Encodes the mixed result |
| `grid` | Fixed-cell MP4 grid | Encodes video and drops audio |
| `thumbnail` | JPEG, PNG, or WebP | Maps one decoded video frame |
| `make_gif` | Palette-based GIF | Filters video and drops audio |
| `rotate` | Quarter-turn MP4 | Encodes video and keeps optional audio |
| `crop` | Fixed-size MP4 | Encodes video and keeps optional audio |
| `change_speed` | Faster or slower MP4 | Changes paired video and audio timing |
| `normalize_loudness` | One-pass normalized audio | Filters and encodes one audio track |
| `fit_canvas` | Fixed canvas MP4 | Scales, pads, and keeps optional audio |
| `picture_in_picture` | MP4 with video inset | Keeps the main audio |
| `waveform_image` | JPEG, PNG, or WebP | Renders one selected audio track |
| `spectrum_image` | JPEG, PNG, or WebP | Draws a frequency spectrum |
| `still_image_video` | MP4 from image and audio | Ends with the selected audio track |
| `contact_sheet` | JPEG, PNG, or WebP | Samples frames into one image |
| `duck_music` | MP4 with speech-aware music | Loops and lowers the music input |
| `fade_edges` | Trimmed MP4 with paired fades | Fades selected video and optional audio |
| `blurred_background` | Fixed canvas MP4 | Composes sharp and blurred source copies |
| `reverse_clip` | Reversed MP4 section | Buffers at most 60 seconds |

When a task needs custom stream selection, filter expressions, more than one
output, or another container, use the [full example guide](examples.md) and the
typed graph API.
