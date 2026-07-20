# Real-world one-line workflows

These examples start with a concrete result. Each one shows the input, output,
terminal command, matching Python call, and the part of FFmpeg that does the
work.

The terminal command runs immediately. Add `--dry-run` to inspect it first.
The Python call returns a plan and runs it with `.run()`.

```python
from flowmpeg import shortcuts as ff
```

## Video delivery and social formats

### 1. Make a smaller upload copy

**Input:** `camera-master.mov`, a large camera export.

**Output:** `upload.mp4`, H.264 at CRF 30, no wider than 1920 pixels, with
96 kbit/s AAC audio.

```console
flowmpeg compress camera-master.mov --crf 30 --max-width 1920 --audio-bitrate 96k -o upload.mp4
```

```python
ff.compress_video(
    "camera-master.mov",
    "upload.mp4",
    crf=30,
    max_width=1920,
    audio_bitrate="96k",
).run()
```

CRF controls H.264 quality. A larger CRF usually produces a smaller file and
more visible loss. The maximum width never enlarges a narrower source.

### 2. Fit a landscape clip into a square

**Input:** `demo.mp4`, in landscape orientation.

**Output:** `square.mp4`, 1080 by 1080 with the whole picture visible and black
padding where needed.

```console
flowmpeg social demo.mp4 --target square --fill fit -o square.mp4
```

```python
ff.social_video("demo.mp4", "square.mp4", target="square", fill="fit").run()
```

The `fit` mode scales down to fit, pads the unused area, and sets square
pixels. It does not stretch the image.

### 3. Put landscape video in a vertical blurred frame

**Input:** `talk.mp4`, a 16:9 recording.

**Output:** `vertical.mp4`, 1080 by 1920 with a sharp center image over a
blurred copy.

```console
flowmpeg social talk.mp4 --target vertical --fill blur --blur 24 -o vertical.mp4
```

```python
ff.social_video(
    "talk.mp4",
    "vertical.mp4",
    target="vertical",
    fill="blur",
    blur=24,
).run()
```

The video stream is split. One copy fills and blurs the frame, then the fitted
copy is overlaid in the center.

### 4. Fill a portrait frame by cropping

**Input:** `wide-shot.mp4`.

**Output:** `portrait.mp4`, 1080 by 1350 with no padding.

```console
flowmpeg social wide-shot.mp4 --target portrait --fill crop -o portrait.mp4
```

```python
ff.social_video(
    "wide-shot.mp4",
    "portrait.mp4",
    target="portrait",
    fill="crop",
).run()
```

Crop mode scales until the frame is filled, then takes a centered crop. Content
near the left or right edge may be removed.

### 5. Make a custom vertical crop

**Input:** `screen-recording.mp4`.

**Output:** `short.mp4`, exactly 720 by 1280.

```console
flowmpeg reframe screen-recording.mp4 --width 720 --height 1280 -o short.mp4
```

```python
ff.reframe(
    "screen-recording.mp4",
    "short.mp4",
    width=720,
    height=1280,
).run()
```

Use `reframe` when the dimensions are not one of the four social presets.

### 6. Convert variable timing to 30 fps

**Input:** `phone-capture.mp4`, which may have uneven frame timing.

**Output:** `constant-30.mp4`, encoded at a constant 30 frames per second.

```console
flowmpeg fps phone-capture.mp4 --fps 30 -o constant-30.mp4
```

```python
ff.set_frame_rate("phone-capture.mp4", "constant-30.mp4", fps=30).run()
```

The `fps` filter drops or duplicates frames to reach the requested rate. It
does not create motion-interpolated frames.

### 7. Clean an interlaced archive clip

**Input:** `tape-capture.mpg`, known to contain interlaced video.

**Output:** `progressive.mp4`, one progressive frame for each input frame.

```console
flowmpeg deinterlace tape-capture.mpg --mode bwdif -o progressive.mp4
```

```python
ff.deinterlace("tape-capture.mpg", "progressive.mp4", mode="bwdif").run()
```

Only use this on interlaced material. Deinterlacing progressive video can
remove detail without improving motion.

### 8. Correct a mirrored camera recording

**Input:** `selfie.mp4`.

**Output:** `normal-view.mp4`, flipped horizontally with audio retained.

```console
flowmpeg mirror selfie.mp4 -o normal-view.mp4
```

```python
ff.flip_video("selfie.mp4", "normal-view.mp4").run()
```

Set `--direction vertical` for an upside-down axis or `both` for a half-turn by
two flips.

### 9. Adjust a flat camera image

**Input:** `flat.mp4`.

**Output:** `graded.mp4`, with a small contrast and saturation increase.

```console
flowmpeg color flat.mp4 --contrast 1.12 --saturation 1.18 --gamma 1.03 -o graded.mp4
```

```python
ff.adjust_colors(
    "flat.mp4",
    "graded.mp4",
    contrast=1.12,
    saturation=1.18,
    gamma=1.03,
).run()
```

This uses FFmpeg's `eq` filter. Values are validated before the command is
built, but visual review is still needed.

### 10. Sharpen a soft screen capture

**Input:** `soft-demo.mp4`.

**Output:** `sharp-demo.mp4`, with moderate luma sharpening.

```console
flowmpeg sharpen soft-demo.mp4 --amount 1.2 --matrix-size 5 -o sharp-demo.mp4
```

```python
ff.sharpen("soft-demo.mp4", "sharp-demo.mp4", amount=1.2).run()
```

The matrix size must be an odd number from 3 through 23. Large values can
produce halos around text and edges.

## Timeline edits and privacy

### 11. Hold the last frame for an end card

**Input:** `announcement.mp4`.

**Output:** `announcement-end.mp4`, with the final frame held for three seconds
and audio padded with silence.

```console
flowmpeg freeze announcement.mp4 --seconds 3 -o announcement-end.mp4
```

```python
ff.freeze_end("announcement.mp4", "announcement-end.mp4", seconds=3).run()
```

The hold is limited to 60 seconds. No extra graphic or title is added.

### 12. Mute a private sentence

**Input:** `meeting.mp4`.

**Output:** `redacted.mp4`, silent from 73.2 through 81.5 seconds.

```console
flowmpeg silence-section meeting.mp4 --start 73.2 --end 81.5 -o redacted.mp4
```

```python
ff.mute_section("meeting.mp4", "redacted.mp4", start=73.2, end=81.5).run()
```

Only the selected range is muted. The stream length and the rest of the audio
remain unchanged.

### 13. Blur a fixed license plate area

**Input:** `driveway.mp4`, where the plate remains at the same coordinates.

**Output:** `private-driveway.mp4`, with a 260 by 90 blurred rectangle.

```console
flowmpeg privacy-blur driveway.mp4 --x 820 --y 700 --width 260 --height 90 --radius 18 -o private-driveway.mp4
```

```python
ff.blur_region(
    "driveway.mp4",
    "private-driveway.mp4",
    x=820,
    y=700,
    width=260,
    height=90,
    radius=18,
).run()
```

This is a fixed rectangle. It does not track a moving face or plate. Preview
the full output before treating it as a privacy edit.

### 14. Make a short boomerang loop

**Input:** `jump.mp4`.

**Output:** `jump-bounce.mp4`, containing seconds 2 through 4.5 forward and
then backward. Its expected duration is about five seconds.

```console
flowmpeg bounce jump.mp4 --start 2 --duration 2.5 -o jump-bounce.mp4
```

```python
ff.boomerang("jump.mp4", "jump-bounce.mp4", start=2, duration=2.5).run()
```

Forward and reverse processing buffers the selected range, so the shortcut
limits it to 15 seconds.

## Voice, podcast, and music

### 15. Reduce steady room noise

**Input:** `room-recording.wav`.

**Output:** `clean.wav`, with frequency-domain noise reduction.

```console
flowmpeg denoise room-recording.wav --reduction 10 --noise-floor -52 -o clean.wav
```

```python
ff.denoise_audio(
    "room-recording.wav",
    "clean.wav",
    reduction=10,
    noise_floor=-52,
).run()
```

This is intended for steady background noise. Strong settings can make speech
sound metallic, so compare the result with the input.

### 16. Control uneven speech levels

**Input:** `uneven.wav`.

**Output:** `controlled.wav`, with loud sections reduced by a 4:1 compressor.

```console
flowmpeg dynamics uneven.wav --threshold 0.1 --ratio 4 --attack 15 --release 220 -o controlled.wav
```

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

Compression changes dynamic range. It is different from output loudness
normalization.

### 17. Finish a spoken-word recording

**Input:** `raw-episode.wav`.

**Output:** `episode.wav`, with rumble filtering, a high-frequency limit,
noise reduction, compression, and minus 16 LUFS one-pass normalization.

```console
flowmpeg voice raw-episode.wav -o episode.wav
```

```python
ff.podcast_voice("raw-episode.wav", "episode.wav").run()
```

Turn off stages when the source was already processed:

```console
flowmpeg voice mastered.wav --no-denoise --no-compress -o level.wav
```

### 18. Remove silence only from the edges

**Input:** `take.wav`, with a pause before and after speech.

**Output:** `tight.wav`, with leading and trailing silence removed while pauses
inside the recording remain.

```console
flowmpeg desilence take.wav --duration 120 --threshold-db -45 --minimum 0.3 -o tight.wav
```

```python
ff.trim_silence(
    "take.wav",
    "tight.wav",
    duration=120,
    threshold_db=-45,
    minimum=0.3,
).run()
```

The audio is processed forward and in reverse so the same leading-silence rule
can trim both ends. The explicit duration keeps reverse-filter memory bounded.

### 19. Downmix an interview to mono MP3

**Input:** `stereo-interview.wav`.

**Output:** `interview.mp3`, one channel at 128 kbit/s.

```console
flowmpeg mono stereo-interview.wav --codec mp3 --bitrate 128k -o interview.mp3
```

```python
ff.mono_audio(
    "stereo-interview.wav",
    "interview.mp3",
    codec="mp3",
    bitrate="128k",
).run()
```

This selects one input audio track and converts its channel layout to mono.

### 20. Join songs with a crossfade

**Inputs:** `intro.wav` and `main.wav`.

**Output:** `program.wav`, with a two-second equal-power style transition.

```console
flowmpeg crossfade intro.wav main.wav --duration 2 --curve qsin -o program.wav
```

```python
ff.crossfade_audio(
    "intro.wav",
    "main.wav",
    "program.wav",
    duration=2,
    curve="qsin",
).run()
```

Both inputs must be longer than the crossfade duration. Available curves are
`tri`, `qsin`, and `exp`.

## Subtitles and metadata

### 21. Extract subtitles for editing

**Input:** `film.mkv`, with at least one text subtitle stream.

**Output:** `captions.srt` from the first subtitle track.

```console
flowmpeg subtitles film.mkv -o captions.srt
```

```python
ff.extract_subtitles("film.mkv", "captions.srt").run()
```

Set `--track 1` or `track=1` for the second subtitle stream. Bitmap subtitle
formats cannot be converted to text by this shortcut.

### 22. Add selectable subtitles to MP4

**Inputs:** `lesson.mp4` and `captions.srt`.

**Output:** `lesson-captioned.mp4`, with a selectable English subtitle track.

```console
flowmpeg captions lesson.mp4 captions.srt --language eng -o lesson-captioned.mp4
```

```python
ff.add_subtitles(
    "lesson.mp4",
    "captions.srt",
    "lesson-captioned.mp4",
    language="eng",
).run()
```

The subtitles are stored as `mov_text`. They are not burned into the picture,
so a player can turn them on or off.

### 23. Remove subtitle tracks

**Input:** `screening.mkv`.

**Output:** `screening-clean.mp4`, containing the first video and first audio
stream, with no subtitle mapping.

```console
flowmpeg strip-subtitles screening.mkv -o screening-clean.mp4
```

```python
ff.remove_subtitles("screening.mkv", "screening-clean.mp4").run()
```

Other audio tracks, attachments, and data streams are not selected by this
shortcut.

### 24. Remove metadata before sharing

**Input:** `camera.mkv`.

**Output:** `share.mkv`, with the first video and audio streams copied, and
container metadata and chapters removed.

```console
flowmpeg clean-metadata camera.mkv -o share.mkv
```

```python
ff.strip_metadata("camera.mkv", "share.mkv").run()
```

The input and output extensions must match because streams are copied. This is
not a claim that every private byte in every container has been removed. Probe
and inspect the output before publishing it.

### 25. Keep subtitles while removing metadata

**Input:** `film.mkv`.

**Output:** `film-clean.mkv`, with the first subtitle stream retained.

```console
flowmpeg clean-metadata film.mkv --subtitles -o film-clean.mkv
```

```python
ff.strip_metadata(
    "film.mkv",
    "film-clean.mkv",
    include_subtitles=True,
).run()
```

### 26. Tag a finished audio file

**Input:** `episode.m4a`.

**Output:** `episode-tagged.m4a`, copied without audio encoding and tagged with
the supplied fields.

```console
flowmpeg tag episode.m4a --title "Episode 12" --artist "Example Host" --album "Example Show" --date 2026 -o episode-tagged.m4a
```

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

At least one field is required. Supported fields are title, artist, album,
date, and genre.

## Images and creator assets

### 27. Turn rendered frames into a video

**Inputs:** `frames/frame-0001.png`, `frame-0002.png`, and later numbered
files.

**Output:** `animation.mp4`, 1920 by 1080 at 24 fps.

```console
flowmpeg timelapse frames/frame-%04d.png --fps 24 --start-number 1 -o animation.mp4
```

```python
ff.image_sequence_video(
    "frames/frame-%04d.png",
    "animation.mp4",
    fps=24,
    start_number=1,
).run()
```

The pattern must contain `%d` or a padded form such as `%04d`. The input frame
rate is set before FFmpeg reads the sequence.

In Windows batch files, write `%%04d` because CMD uses `%` for variables. At an
interactive CMD prompt, `%04d` is correct.

### 28. Make a podcast audiogram

**Inputs:** `episode.wav` and `cover.jpg`.

**Output:** `audiogram.mp4`, with the cover image, an animated waveform, and the
episode audio.

```console
flowmpeg audiogram episode.wav cover.jpg --wave-color DodgerBlue -o audiogram.mp4
```

```python
ff.podcast_audiogram(
    "episode.wav",
    "cover.jpg",
    "audiogram.mp4",
    wave_color="DodgerBlue",
).run()
```

The image loops until the selected audio track ends. The waveform must fit
inside the requested video frame.

### 29. Make a contact sheet for review

**Input:** `long-take.mp4`.

**Output:** `review.jpg`, a 5 by 4 sheet sampled every 30 seconds.

```console
flowmpeg sheet long-take.mp4 --columns 5 --rows 4 --interval 30 -o review.jpg
```

```python
ff.contact_sheet(
    "long-take.mp4",
    "review.jpg",
    columns=5,
    rows=4,
    interval=30,
).run()
```

This creates one image. It does not create a directory of separate frames.

### 30. Make a short preview GIF

**Input:** `demo.mp4`.

**Output:** `preview.gif`, four seconds from the 12-second mark, 480 pixels
wide at 12 fps.

```console
flowmpeg gif demo.mp4 --start 12 --duration 4 --width 480 --fps 12 -o preview.gif
```

```python
ff.make_gif(
    "demo.mp4",
    "preview.gif",
    start=12,
    duration=4,
    width=480,
    fps=12,
).run()
```

Flowmpeg builds a palette from the selected clip before creating the GIF.

## Inspect any workflow

Add a dry run to any terminal example:

```console
flowmpeg voice raw-episode.wav -o episode.wav --dry-run
```

Show the graph summary too:

```console
flowmpeg voice raw-episode.wav -o episode.wav --dry-run --explain
```

Inspect the matching Python plan:

```python
plan = ff.podcast_voice("raw-episode.wav", "episode.wav")
print(plan.explain())
print(plan.filter_graph())
print(plan.command())
```

Use `flowmpeg probe input-file` before jobs where track selection, dimensions,
or duration matter. Use `flowmpeg doctor` when an FFmpeg build reports a
missing filter or encoder.
