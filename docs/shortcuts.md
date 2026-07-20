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
5. Building a plan does not probe the input. Timeline plans inspect audio only
   when `.run()` selects an execution path.

Shortcuts that only pass audio through use an optional map. Timeline shortcuts
build an audio-filtering plan and a video-only fallback. Silent sources work
without a separate probe call. Set `include_audio=False` to skip inspection and
request video-only output directly.

```python
ff.change_speed("silent-demo.mp4", "fast.mp4", factor=2).run()
```

Pass `ffprobe` or `probe_timeout` to `.run()` when the defaults do not match the
local tool path or source response time.

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

### Encode VP9 and Opus WebM

**Input:** `recording.mov`

**Output:** `recording.webm` with VP9 video and optional Opus audio.

```python
ff.transcode_webm(
    "recording.mov",
    "recording.webm",
    crf=30,
    cpu_used=2,
    audio_bitrate="96k",
).run()
```

Set `include_audio=False` for a video-only source. The default VP9 CRF is 32.

### Encode a smaller HEVC delivery file

**Input:** `camera-master.mov`

**Output:** `camera-hevc.mp4` with HEVC video and optional AAC audio.

```python
ff.transcode_hevc(
    "camera-master.mov",
    "camera-hevc.mp4",
    crf=28,
    encoder_preset="medium",
).run()
```

The `hvc1` video tag improves recognition in Apple players. Run
`flowmpeg doctor --command hevc` before a batch to check for `libx265`.

### Encode AV1 and Opus WebM

```python
ff.transcode_av1(
    "camera-master.mov",
    "camera-av1.webm",
    crf=35,
    speed=8,
).run()
```

The shortcut uses SVT-AV1 and optional Opus audio. Speed 0 does more encoding
work; speed 13 is the fastest setting. Use `include_audio=False` for a silent
source.

### Keep an exact time range

**Input:** `interview.mp4`

**Output:** `answer.mp4`, containing seconds 42 through 68.

```python
ff.trim("interview.mp4", "answer.mp4", start=42, end=68).run()
```

Video and audio timestamps are reset to zero after trimming.

### Repeat a short clip to an exact duration

```python
ff.loop_video(
    "logo-motion.mp4",
    "background.mp4",
    duration=30,
).run()
```

The shortcut loops the input, trims both timelines, and handles a silent source
at run time. Durations from 0.01 seconds through 24 hours are accepted.

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

### Extract Opus audio

```python
ff.extract_audio(
    "interview.mp4",
    "voice.opus",
    codec="opus",
    bitrate="96k",
).run()
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

This shortcut uses one-pass FFmpeg `loudnorm`. Use a workflow when the second
pass must receive measured first-pass values:

```python
from flowmpeg import normalize_loudness_two_pass

workflow = normalize_loudness_two_pass(
    "program.wav",
    "program-exact.wav",
    target_integrated=-23,
    target_peak=-2,
)

print(workflow.explain())
result = workflow.run(measurement_timeout=60, timeout=120)
print(result.measurement.integrated_lufs)
```

`workflow.measure()` runs only the analysis. Pass that result to
`workflow.plan(measurement)` to inspect or run the exact encoding plan yourself.
The plan builder is also available directly as `normalize_loudness_measured`
when the caller already owns a matching `LoudnessMeasurement`.

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

### Normalize and join different clips

```python
ff.join_normalized(
    ["phone.mp4", "camera.mp4"],
    "joined.mp4",
    width=1280,
    height=720,
    fps=30,
    sample_rate=48000,
).run()
```

Every input is fitted and padded to the chosen canvas, set to one frame rate,
and converted to stereo at one sample rate before `concat`. A missing audio
track switches the whole result to video-only output.

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

## Delivery and creator shortcuts

### Compress a smaller MP4

**Input:** `master.mov`

**Output:** `upload.mp4`, H.264 at CRF 30 with a maximum width of 1920.

```python
ff.compress_video(
    "master.mov",
    "upload.mp4",
    crf=30,
    max_width=1920,
    audio_bitrate="96k",
).run()
```

### Choose a slower encoder preset

```python
ff.compress_video(
    "master.mov",
    "upload.mp4",
    crf=26,
    encoder_preset="slow",
).run()
```

A slower preset can spend more time finding an efficient H.264 representation.
It does not change the meaning of CRF.

### Fill a vertical frame

```python
ff.reframe(
    "wide.mp4",
    "vertical.mp4",
    width=1080,
    height=1920,
).run()
```

The source is scaled until it fills the frame, then cropped in the center.

### Create a square padded version

```python
ff.social_video(
    "wide.mp4",
    "square.mp4",
    target="square",
    fill="fit",
).run()
```

### Create a vertical version with blurred fill

```python
ff.social_video(
    "wide.mp4",
    "vertical.mp4",
    target="vertical",
    fill="blur",
    blur=24,
).run()
```

### Set a constant frame rate

```python
ff.set_frame_rate("phone.mp4", "constant.mp4", fps=30).run()
```

### Deinterlace an archive recording

```python
ff.deinterlace("tape.mpg", "progressive.mp4", mode="bwdif").run()
```

### Mirror a camera image

```python
ff.flip_video("selfie.mp4", "normal.mp4", direction="horizontal").run()
```

### Adjust color levels

```python
ff.adjust_colors(
    "flat.mp4",
    "graded.mp4",
    brightness=0.03,
    contrast=1.12,
    saturation=1.18,
    gamma=1.03,
).run()
```

### Sharpen a soft recording

```python
ff.sharpen("soft.mp4", "sharp.mp4", amount=1.2, matrix_size=5).run()
```

### Hold the final frame

```python
ff.freeze_end("announcement.mp4", "held.mp4", seconds=3).run()
```

Audio is padded with silence when it is included.

### Mute one range

```python
ff.mute_section(
    "meeting.mp4",
    "redacted.mp4",
    start=73.2,
    end=81.5,
).run()
```

### Blur one fixed rectangle

```python
ff.blur_region(
    "street.mp4",
    "private.mp4",
    x=820,
    y=700,
    width=260,
    height=90,
    radius=18,
).run()
```

The rectangle stays at the same coordinates. It does not track objects.

### Play a clip forward and backward

```python
ff.boomerang(
    "jump.mp4",
    "bounce.mp4",
    start=2,
    duration=2.5,
).run()
```

The selected range is limited to 15 seconds because reverse filters buffer it.

## Voice and audio cleanup shortcuts

### Reduce steady background noise

```python
ff.denoise_audio(
    "room.wav",
    "clean.wav",
    reduction=10,
    noise_floor=-52,
).run()
```

### Compress uneven audio

```python
ff.compress_audio(
    "uneven.wav",
    "controlled.wav",
    threshold=0.1,
    ratio=4,
    attack=15,
    release=220,
).run()
```

### Run the podcast voice chain

```python
ff.podcast_voice("raw.wav", "finished.wav").run()
```

### Skip stages on an already processed voice

```python
ff.podcast_voice(
    "mastered.wav",
    "level.wav",
    denoise=False,
    compress=False,
).run()
```

### Trim silence from both ends

```python
ff.trim_silence(
    "take.wav",
    "tight.wav",
    duration=120,
    threshold_db=-45,
    minimum=0.3,
).run()
```

Pauses inside the recording are retained. `duration` bounds the decoded audio
held by FFmpeg's reverse filters. It must cover the source and cannot exceed
600 seconds. Longer recordings should be split into bounded sections first.

### Downmix to mono WAV

```python
ff.mono_audio("stereo.wav", "mono.wav").run()
```

### Cut one audio track

```python
ff.trim_audio_file(
    "interview.wav",
    "answer.wav",
    start=30,
    duration=12,
).run()
```

Set `end` or `duration`, not both. The audio timeline starts at zero in the
output. Track, codec, and bitrate options match the other audio-file shortcuts.

### Downmix directly to MP3

```python
ff.mono_audio(
    "stereo.wav",
    "mono.mp3",
    codec="mp3",
    bitrate="128k",
).run()
```

### Standardize sample rate and channel layout

```python
ff.resample_audio(
    "field-recording.wav",
    "standard.wav",
    sample_rate=48000,
    layout="stereo",
).run()
```

The sample rate can range from 8000 through 192000. The layout can be `mono`
or `stereo`. Output codec choices match the other filtered audio shortcuts.

### Raise or lower one audio track

```python
ff.set_audio_volume(
    "quiet.wav",
    "louder.wav",
    gain_db=6,
).run()
```

Gain accepts -60 through 30 dB. A positive value raises the level and a
negative value lowers it. Use `measure_loudness` or the `loudness` command to
check the result.

### Fade both audio edges

```python
ff.fade_audio_edges(
    "music.wav",
    "music-faded.wav",
    duration=120,
    fade_in=2,
    fade_out=4,
).run()
```

The required duration places the ending fade. Set either fade length to zero
to disable that edge. The combined fades cannot exceed the source duration.

### Delay an audio track for synchronization

```python
ff.delay_audio_file(
    "narration.wav",
    "narration-synced.wav",
    seconds=0.35,
).run()
```

The shortcut inserts silence before every channel. Delays from zero through
3600 seconds are accepted.

### Change audio tempo without shifting pitch

```python
ff.change_audio_speed_file(
    "lesson.wav",
    "lesson-fast.wav",
    factor=1.5,
).run()
```

Factors above 2 or below 0.5 are divided into several FFmpeg `atempo` stages.
This keeps large tempo changes inside each stage's supported range.

### Crossfade two tracks

```python
ff.crossfade_audio(
    "intro.wav",
    "episode.wav",
    "program.wav",
    duration=2,
    curve="qsin",
).run()
```

### Join several audio files end to end

```python
ff.join_audio_files(
    ("intro.wav", "body.wav", "outro.wav"),
    "show.wav",
    sample_rate=48000,
    layout="stereo",
).run()
```

Each input is resampled and given the same channel layout before concatenation.
The shortcut accepts two or more files and resets every input timeline.

## Subtitle, sequence, and metadata shortcuts

### Extract the first subtitle track

```python
ff.extract_subtitles("film.mkv", "captions.srt").run()
```

SRT, WebVTT, and ASS text outputs are supported.

### Extract another subtitle track

```python
ff.extract_subtitles("film.mkv", "commentary.vtt", track=1).run()
```

### Add selectable subtitles

```python
ff.add_subtitles(
    "lesson.mp4",
    "captions.srt",
    "captioned.mp4",
    language="eng",
).run()
```

The subtitle stream is encoded as `mov_text` in MP4. It is not burned into the
video picture.

### Burn subtitles into the picture

```python
ff.burn_subtitles(
    "lesson.mp4",
    "captions.srt",
    "open-captioned.mp4",
    font_name="Arial",
    font_size=28,
).run()
```

This uses FFmpeg's `subtitles` filter, so the installed FFmpeg build needs
libass support. The result has visible text in its video frames and no
selectable subtitle track from this operation.

### Remove subtitle tracks

```python
ff.remove_subtitles("screening.mkv", "plain.mp4").run()
```

### Encode numbered images

```python
ff.image_sequence_video(
    "frames/frame-%04d.png",
    "animation.mp4",
    fps=24,
    start_number=1,
).run()
```

### Change the image-sequence canvas

```python
ff.image_sequence_video(
    "renders/shot-%03d.jpg",
    "shot.mp4",
    fps=30,
    width=1280,
    height=720,
    color="white",
).run()
```

### Create a podcast audiogram

```python
ff.podcast_audiogram(
    "episode.wav",
    "cover.jpg",
    "audiogram.mp4",
    wave_color="DodgerBlue",
).run()
```

### Use a compact audiogram frame

```python
ff.podcast_audiogram(
    "episode.wav",
    "cover.jpg",
    "square-audiogram.mp4",
    width=1080,
    height=1080,
    wave_width=900,
    wave_height=180,
).run()
```

### Remove metadata and chapters

```python
ff.strip_metadata("camera.mkv", "share.mkv").run()
```

The first video and optional first audio streams are copied. Input and output
extensions must match.

### Retain one subtitle while removing metadata

```python
ff.strip_metadata(
    "film.mkv",
    "film-clean.mkv",
    include_subtitles=True,
).run()
```

### Tag an audio file without re-encoding it

```python
ff.tag_audio(
    "episode.m4a",
    "episode-tagged.m4a",
    title="Episode 12",
    artist="Example Host",
    album="Example Show",
    date="2026",
).run()
```

At least one metadata field is required. Input and output extensions must
match.

### Tag a video or mixed media file without re-encoding it

```python
ff.tag_media(
    "camera.mp4",
    "camera-tagged.mp4",
    title="Camera master",
    comment="Approved copy",
).run()
```

The first video and optional first audio streams are copied. Set
`include_subtitles=True` to copy the selected subtitle stream too. The input
and output extensions must match.

### Change the container without re-encoding

```python
ff.remux_media(
    "camera.mp4",
    "camera.mkv",
    include_subtitles=True,
).run()
```

The shortcut copies one selected video, optional audio, and optional subtitle
stream. MKV, MP4, MOV, and WebM outputs are accepted. The destination container
still needs to support the copied codecs.

The [workflow guide](workflows.md) pairs these calls with installed terminal
commands and explains the expected output of each job.

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
| `transcode_webm` | VP9 and Opus WebM | Encodes selected video and optional audio |
| `transcode_hevc` | HEVC and AAC MP4 | Encodes selected video and optional audio |
| `transcode_av1` | AV1 and Opus WebM | Encodes selected video and optional audio |
| `trim` | Accurate time range | Filters paired timestamps, then encodes |
| `loop_video` | Exact-duration repeated video | Loops input and trims paired timelines |
| `resize` | New width or height | Encodes video and keeps optional audio |
| `remove_audio` | Video-only file | Copies video and drops other streams |
| `extract_audio` | MP3, AAC, Opus, WAV, FLAC, or copy | Maps one audio track |
| `replace_audio` | MP4 with another track | Copies video and replaces original audio |
| `watermark` | Branded MP4 | Encodes overlay video and keeps optional audio |
| `add_music` | MP4 with mixed or new music | Encodes audio and video |
| `join_matching` | Joined MP4 | Filters compatible streams and encodes |
| `join_normalized` | Joined MP4 | Aligns canvas, frame rate, and audio format first |
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
| `compress_video` | Smaller H.264 MP4 | Encodes selected video and optional audio |
| `reframe` | Filled custom frame | Scales up and takes a centered crop |
| `social_video` | Common social frame | Uses blur, crop, or padded fit |
| `set_frame_rate` | Constant-rate MP4 | Drops or repeats video frames |
| `deinterlace` | Progressive MP4 | Applies bwdif or yadif |
| `flip_video` | Mirrored MP4 | Flips one axis or both axes |
| `adjust_colors` | Corrected MP4 | Applies one `eq` filter |
| `sharpen` | Sharpened MP4 | Applies bounded luma unsharp filtering |
| `freeze_end` | MP4 with a held ending | Clones the last frame and pads audio |
| `mute_section` | MP4 with a muted range | Applies an enabled audio volume filter |
| `blur_region` | MP4 with a fixed blur | Crops, blurs, and overlays one rectangle |
| `boomerang` | Forward and reverse MP4 | Buffers at most 15 seconds |
| `denoise_audio` | Cleaner audio file | Applies frequency-domain noise reduction |
| `compress_audio` | Controlled audio file | Applies dynamic-range compression |
| `podcast_voice` | Finished voice file | Filters, compresses, and normalizes speech |
| `trim_silence` | Tighter audio file | Removes silence from both edges |
| `trim_audio_file` | Accurate audio clip | Cuts one track and resets timestamps |
| `mono_audio` | Mono audio file | Downmixes one selected track |
| `resample_audio` | Standardized audio file | Sets sample rate and mono or stereo layout |
| `set_audio_volume` | Gain-adjusted audio file | Applies a fixed decibel change |
| `fade_audio_edges` | Faded audio file | Places optional fades at both edges |
| `delay_audio_file` | Delayed audio file | Inserts leading silence on every channel |
| `change_audio_speed_file` | Faster or slower audio | Chains compatible tempo stages |
| `crossfade_audio` | Joined audio file | Transitions between two inputs |
| `join_audio_files` | End-to-end audio file | Aligns formats and concatenates inputs |
| `extract_subtitles` | SRT, WebVTT, or ASS | Maps and encodes one text subtitle track |
| `add_subtitles` | MP4 with selectable text | Adds one `mov_text` subtitle stream |
| `burn_subtitles` | MP4 with visible text | Renders an external subtitle track into video frames |
| `remove_subtitles` | MP4 without subtitles | Selects first video and optional first audio |
| `image_sequence_video` | MP4 from numbered images | Sets input frame rate and fits a canvas |
| `podcast_audiogram` | Cover video with waveform | Loops an image until audio ends |
| `strip_metadata` | Copy without metadata | Copies selected first streams |
| `remux_media` | New media container | Copies selected streams without encoding |
| `tag_media` | Tagged media copy | Copies selected streams and adds container fields |
| `tag_audio` | Tagged audio copy | Copies one track and adds supplied fields |

When a task needs custom stream selection, filter expressions, more than one
output, or another container, use the [full example guide](examples.md) and the
typed graph API.
