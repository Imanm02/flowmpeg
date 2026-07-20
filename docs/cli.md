# One-line commands

The installed `flowmpeg` program is the shortest way to run a Flowmpeg job.
I can use it directly in CMD, PowerShell, Bash, or another terminal without
writing a Python file.

```console
flowmpeg cut input.mp4 --start 10 --duration 20 -o clip.mp4
```

That command reads `input.mp4`, keeps 20 seconds starting at second 10, and
writes `clip.mp4` with H.264 video and AAC audio.

Editing commands run immediately. Add `--dry-run` when the goal is to inspect
the FFmpeg command without starting a process.

## Install and check the tools

Flowmpeg needs Python 3.10 or newer. FFmpeg and FFprobe are separate programs.
The defaults use `PATH`, while setup, doctor, probe, and editing commands also
accept explicit executable paths.

```console
python -m pip install "git+https://github.com/Imanm02/flowmpeg.git"
flowmpeg --version
flowmpeg setup
flowmpeg doctor
```

`setup` checks both executables without changing the machine. If a tool is
missing, it prints the supported package manager command. Installation only
runs with `flowmpeg setup --install` and confirmation. See the
[installation guide](installation.md) for each supported system.

`doctor` checks both executables and every capability named by the command
catalog, then groups the results by the kind of job they support.

Use `--require` when a script depends on one group. A limited or unknown
requested group returns exit code 3:

```console
flowmpeg doctor --require web-video
flowmpeg doctor --command gif
```

`--command` accepts canonical names and shortcuts. It checks the encoder,
muxer, and filters used by the canonical command's default recipe. It cannot
be combined with `--require`.

The module form runs the same program:

```console
python -m flowmpeg doctor
python -m flowmpeg cut input.mp4 --duration 5 -o clip.mp4
```

## The four command rules

1. Editing commands execute unless `--dry-run` is present.
2. Existing local outputs are protected. Add `--overwrite` to replace one.
3. `-o` and `--output` mean the same thing.
4. Execution options belong after the command name.

For example, this is a preview:

```console
flowmpeg resize input.mp4 --width 1280 -o smaller.mp4 --dry-run
```

This runs the job and allows replacement:

```console
flowmpeg resize input.mp4 --width 1280 -o smaller.mp4 --overwrite
```

## Command map

The [generated command reference](command-reference.md) is the source-backed
map of every editing, inspection, and help command. It includes aliases, tags,
input and output kinds, and doctor groups. The installed catalog exposes the
same fields:

```console
flowmpeg commands
flowmpeg commands --tag archive
flowmpeg commands --json
```

The table below is a compact editing index for scanning this longer guide.

| Job | Main command | Short form |
| --- | --- | --- |
| Convert to web MP4 | `transcode` | `convert` |
| Convert to VP9 WebM | `transcode-webm` | `webm`, `vp9` |
| Cut a time range | `trim` | `cut` |
| Resize by one side | `resize` | `scale` |
| Remove the audio stream | `remove-audio` | `mute`, `strip-audio` |
| Save one audio track | `extract-audio` | `audio` |
| Replace video audio | `replace-audio` | `swap-audio` |
| Add an image mark | `watermark` | `mark` |
| Mix music under video | `add-music` | `music` |
| Join matching clips | `join-matching` | `join` |
| Normalize and join clips | `join-normalized` | `join-any`, `normalize-join` |
| Mix audio files | `mix-audio` | `mix`, `mix-audio-files` |
| Arrange video cells | `grid` | - |
| Save one frame | `thumbnail` | `thumb` |
| Create an animated GIF | `make-gif` | `gif` |
| Rotate displayed video | `rotate` | - |
| Crop a rectangle | `crop` | - |
| Change playback speed | `change-speed` | `speed` |
| Normalize loudness | `normalize-loudness` | `normalize` |
| Fit a fixed canvas | `fit-canvas` | `fit` |
| Add an inset video | `picture-in-picture` | `pip` |
| Draw a waveform | `waveform-image` | `waveform` |
| Draw a spectrum | `spectrum-image` | `spectrum` |
| Pair an image with audio | `still-image-video` | `still-video` |
| Build a contact sheet | `contact-sheet` | `sheet` |
| Lower music under speech | `duck-music` | `duck` |
| Trim and fade a clip | `fade-edges` | `fade` |
| Fill a wide canvas with blur | `blurred-background` | `blur-bg` |
| Reverse a bounded clip | `reverse-clip` | `reverse` |
| Compress a web video | `compress-video` | `compress`, `smaller` |
| Fill a custom frame | `reframe` | `fill-frame` |
| Prepare a social frame | `social-video` | `social` |
| Set a constant frame rate | `set-frame-rate` | `fps` |
| Deinterlace video | `deinterlace` | - |
| Mirror video | `flip-video` | `flip`, `mirror` |
| Adjust color levels | `adjust-colors` | `color` |
| Sharpen video | `sharpen` | - |
| Hold the last frame | `freeze-end` | `freeze` |
| Mute one time range | `mute-section` | `silence-section` |
| Blur a fixed rectangle | `blur-region` | `privacy-blur` |
| Play forward and backward | `boomerang` | `bounce` |
| Reduce background noise | `denoise-audio` | `denoise` |
| Compress audio dynamics | `compress-audio` | `dynamics` |
| Finish spoken audio | `podcast-voice` | `voice` |
| Trim silence from both ends | `trim-silence` | `desilence` |
| Downmix to mono | `mono-audio` | `mono` |
| Crossfade two audio files | `crossfade-audio` | `crossfade` |
| Extract a subtitle track | `extract-subtitles` | `subtitles` |
| Add selectable subtitles | `add-subtitles` | `captions` |
| Burn subtitles into video | `burn-subtitles` | `burn-captions`, `hardcode-subtitles` |
| Remove subtitle tracks | `remove-subtitles` | `strip-subtitles` |
| Encode numbered images | `image-sequence-video` | `timelapse`, `image-sequence` |
| Make a podcast audiogram | `podcast-audiogram` | `audiogram` |
| Remove metadata | `strip-metadata` | `clean-metadata` |
| Tag an audio file | `tag-audio` | `tag` |

Run help for the full option list and current defaults:

```console
flowmpeg --help
flowmpeg cut --help
flowmpeg waveform --help
```

## Conversion and timing

### Convert MOV to web MP4

**Input:** `recording.mov`

**Output:** `recording.mp4` with H.264 video and AAC audio.

```console
flowmpeg convert recording.mov -o recording.mp4
```

Use `--no-audio` for a source with no audio stream:

```console
flowmpeg convert animation.mov --no-audio -o animation.mp4
```

### Convert to VP9 and Opus WebM

**Input:** `recording.mov`

**Output:** `recording.webm` with VP9 video and optional Opus audio.

```console
flowmpeg webm recording.mov --crf 30 --cpu-used 2 -o recording.webm
```

VP9 CRF accepts 0 through 63. Lower values retain more detail. `--cpu-used`
accepts 0 through 8, where higher values trade compression work for speed.
Use `--audio-bitrate 96k` to change the Opus bitrate or `--no-audio` for a
video-only result.

Commands that change audio timing inspect their sources when they run. `cut`,
`join`, `speed`, `fade`, `freeze`, `reverse`, and `bounce` select a video-only
plan when any required audio track is absent. Use `--no-audio` to request a
video-only plan without inspection.

```console
flowmpeg speed silent-demo.mp4 --factor 2 -o fast.mp4
```

### Cut by start and duration

**Input:** `meeting.mp4`

**Output:** `answer.mp4`, containing 15 seconds beginning at second 90.

```console
flowmpeg cut meeting.mp4 --start 90 --duration 15 -o answer.mp4
```

The command resets the video and audio timelines to zero.

### Cut between two timestamps

**Output:** `scene.mp4`, containing seconds 42 through 68.

```console
flowmpeg trim interview.mp4 --start 42 --end 68 -o scene.mp4
```

Use `--start` alone to keep everything after that point:

```console
flowmpeg trim lecture.mp4 --start 120 -o final-section.mp4
```

### Resize by width

**Input:** `camera.mp4`

**Output:** `camera-720p.mp4`, 1280 pixels wide with an even calculated
height.

```console
flowmpeg scale camera.mp4 --width 1280 -o camera-720p.mp4
```

### Resize by height

**Output:** `portrait-1080.mp4`, 1080 pixels tall with a calculated width.

```console
flowmpeg resize portrait.mp4 --height 1080 -o portrait-1080.mp4
```

`resize` requires exactly one dimension so it does not stretch the source.

### Change playback speed

**Input:** `lesson.mp4`

**Output:** `faster.mp4`, with video and audio at 1.5 times the source speed.

```console
flowmpeg speed lesson.mp4 --factor 1.5 -o faster.mp4
```

Use a factor below one for slow motion:

```console
flowmpeg speed action.mp4 --factor 0.5 -o slow.mp4
```

### Rotate clockwise

**Output:** `upright.mp4`, rotated 90 degrees clockwise.

```console
flowmpeg rotate sideways.mp4 --degrees 90 -o upright.mp4
```

The accepted values are 90, 180, and 270. A 270 degree clockwise turn has the
same displayed result as a 90 degree counterclockwise turn.

```console
flowmpeg rotate sideways.mp4 --degrees 270 -o left-turn.mp4
```

### Crop a fixed rectangle

**Output:** `square.mp4`, a 1080 by 1080 region from the source center.

```console
flowmpeg crop wide.mp4 --width 1080 --height 1080 -o square.mp4
```

Set nonnegative coordinates when the crop should begin at a fixed point:

```console
flowmpeg crop wide.mp4 --width 640 --height 360 --x 100 --y 50 -o corner.mp4
```

### Reverse a short clip

**Input:** `action.mp4`

**Output:** `reverse.mp4`, containing a reversed six-second section beginning
at second 12.

```console
flowmpeg reverse action.mp4 --start 12 --duration 6 -o reverse.mp4
```

Reverse filters buffer their selected section in memory. Flowmpeg limits this
command to 60 seconds.

## Audio jobs

### Remove audio without re-encoding video

**Input:** `interview.mp4`

**Output:** `silent.mp4`, containing copied video and no audio stream.

```console
flowmpeg strip-audio interview.mp4 -o silent.mp4
```

This removes audio. It does not add a silent audio track.

### Extract MP3 audio

**Output:** `voice.mp3`, made from the first audio stream at 192 kbit/s.

```console
flowmpeg audio interview.mp4 -o voice.mp3
```

Set another bitrate when file size matters:

```console
flowmpeg audio interview.mp4 --bitrate 96k -o voice-small.mp3
```

### Extract AAC, Opus, WAV, or FLAC

```console
flowmpeg extract-audio movie.mkv --codec aac -o soundtrack.m4a
flowmpeg extract-audio interview.mp4 --codec opus --bitrate 96k -o voice.opus
flowmpeg extract-audio lesson.mp4 --codec wav -o lesson.wav
flowmpeg extract-audio concert.mkv --codec flac -o concert.flac
```

The output suffix must match the selected codec.

### Select another audio track

`--track 1` selects the second audio stream because track indexes begin at
zero.

```console
flowmpeg audio movie.mkv --track 1 -o commentary.mp3
```

### Copy audio packets

**Output:** `track.mka`, containing source audio without encoding.

```console
flowmpeg extract-audio source.mkv --codec copy -o track.mka
```

The destination container must accept the source audio codec.

### Replace a video's audio

**Inputs:** `video.mp4` and `narration.wav`

**Output:** `narrated.mp4`, with copied video and AAC narration. Short
narration is padded to the video duration.

```console
flowmpeg swap-audio video.mp4 narration.wav -o narrated.mp4
```

Stop at the shorter stream and copy compatible AAC audio like this:

```console
flowmpeg replace-audio video.mp4 music.m4a --duration shortest --audio-codec copy -o shortest.mp4
```

### Add background music

**Inputs:** `talk.mp4` and `music.mp3`

**Output:** `scored.mp4`, with music at 15 percent of its source level.

```console
flowmpeg music talk.mp4 music.mp3 -o scored.mp4
```

Set both levels explicitly:

```console
flowmpeg add-music talk.mp4 music.mp3 --source-volume 0.85 --music-volume 0.2 -o balanced.mp4
```

Loop a short music file beneath a longer talk:

```console
flowmpeg add-music long-talk.mp4 short-music.mp3 --loop-music -o looped.mp4
```

For video without a source audio track, use `--silent-source`:

```console
flowmpeg add-music animation.mp4 music.mp3 --silent-source -o scored-animation.mp4
```

### Mix audio files

**Inputs:** `host.wav` and `guest.wav`

**Output:** `conversation.wav`, following the longest input.

```console
flowmpeg mix host.wav guest.wav -o conversation.wav
```

Set an input level for each file:

```console
flowmpeg mix-audio host.wav guest.wav music.wav --volumes 1 0.9 0.12 -o show.wav
```

Write the mix as MP3:

```console
flowmpeg mix-audio-files left.wav right.wav --codec mp3 --bitrate 256k -o mix.mp3
```

Stop with the shortest input:

```console
flowmpeg mix one.wav two.wav --duration shortest -o short.wav
```

### Normalize spoken audio

**Input:** `voice.wav`

**Output:** `normalized.wav` at a minus 16 LUFS target and 48 kHz sample rate.

```console
flowmpeg normalize voice.wav -o normalized.wav
```

Use a broadcast target or write MP3:

```console
flowmpeg normalize voice.wav --integrated -23 --true-peak -2 -o broadcast.wav
flowmpeg normalize voice.wav --codec mp3 -o normalized.mp3
```

The command performs one-pass FFmpeg `loudnorm` processing.

### Duck music beneath speech

**Inputs:** `talk.mp4` with speech and `music.mp3`

**Output:** `ducked.mp4`, with music lowered while speech crosses the
compression threshold.

```console
flowmpeg duck talk.mp4 music.mp3 -o ducked.mp4
```

Tune the response for a louder music bed:

```console
flowmpeg duck-music talk.mp4 music.mp3 --music-volume 0.4 --threshold 0.08 --ratio 10 --attack 15 --release 300 -o tuned-duck.mp4
```

Music loops by default. Add `--no-loop-music` when the source music length
should be kept.

## Composition and layout

### Add a logo

**Inputs:** `video.mp4` and `logo.png`

**Output:** `branded.mp4`, with the image at the top-right and 24 pixels of
padding.

```console
flowmpeg mark video.mp4 logo.png -o branded.mp4
```

Place a resized translucent mark in the center:

```console
flowmpeg watermark video.mp4 mark.png --position center --width 240 --opacity 0.4 -o centered.mp4
```

The position choices are `top-left`, `top-right`, `bottom-left`,
`bottom-right`, and `center`.

### Add picture in picture

**Inputs:** `main.mp4` and `camera.mp4`

**Output:** `with-camera.mp4`, with a 480 pixel wide inset at the bottom-right.
The main video's audio is retained.

```console
flowmpeg pip main.mp4 camera.mp4 -o with-camera.mp4
```

Move the inset and change its size:

```console
flowmpeg picture-in-picture main.mp4 camera.mp4 --inset-width 320 --position top-left --padding 16 -o top-camera.mp4
```

### Join matching clips

**Inputs:** `part-1.mp4` and `part-2.mp4` with matching decoded formats.

**Output:** `joined.mp4`, with the second clip after the first.

```console
flowmpeg join part-1.mp4 part-2.mp4 -o joined.mp4
```

Three silent clips can be joined with:

```console
flowmpeg join-matching one.mp4 two.mp4 three.mp4 --no-audio -o joined-silent.mp4
```

The command does not repair different resolutions, frame rates, pixel
formats, sample rates, or channel layouts.

### Normalize and join different clips

**Inputs:** `phone.mp4` and `camera.mp4` with different media formats.

**Output:** `joined.mp4`, normalized to a 1280 by 720 canvas, 30 fps, 48 kHz
stereo audio, then joined in input order.

```console
flowmpeg join-any phone.mp4 camera.mp4 --width 1280 --height 720 -o joined.mp4
```

Each video is fitted without stretching and padded with black by default.
Change the padding with `--color`. Use `--fps` and `--sample-rate` when the
delivery format calls for other values. If any input has no audio,
`join-any` automatically creates a video-only result.

### Arrange a video grid

**Inputs:** four camera videos

**Output:** `grid.mp4`, a 2 by 2 grid with 640 by 360 cells and no audio.

```console
flowmpeg grid camera-1.mp4 camera-2.mp4 camera-3.mp4 camera-4.mp4 -o grid.mp4
```

Build a one-row grid with smaller cells:

```console
flowmpeg grid one.mp4 two.mp4 three.mp4 --columns 3 --cell-width 320 --cell-height 180 -o row.mp4
```

The default stops with the shortest input. Continue until the longest input
ends with:

```console
flowmpeg grid short.mp4 long.mp4 --keep-longest -o long-grid.mp4
```

### Fit a fixed canvas

**Input:** `portrait.mp4`

**Output:** `portrait-wide.mp4`, a 1920 by 1080 video with the portrait source
centered and black padding. The source is not stretched.

```console
flowmpeg fit portrait.mp4 -o portrait-wide.mp4
```

Use another even canvas size and color:

```console
flowmpeg fit-canvas square.mp4 --width 1280 --height 720 --color white -o square-wide.mp4
```

### Fill a canvas with a blurred copy

**Input:** `portrait.mp4`

**Output:** `blurred-wide.mp4`, with the full portrait video over a blurred
wide background made from the same frames.

```console
flowmpeg blur-bg portrait.mp4 -o blurred-wide.mp4
```

Set a smaller canvas and softer blur:

```console
flowmpeg blurred-background portrait.mp4 --width 1280 --height 720 --blur 12 -o soft-background.mp4
```

### Trim and fade both edges

**Input:** `source.mp4`

**Output:** `faded.mp4`, a ten-second clip with one-second video and audio
fades at both ends.

```console
flowmpeg fade source.mp4 --start 20 --duration 10 -o faded.mp4
```

Set different fade lengths:

```console
flowmpeg fade-edges source.mp4 --duration 12 --fade-in 0.5 --fade-out 2 -o custom-fades.mp4
```

The combined fade lengths cannot exceed the selected clip duration.

## Images and previews

### Save a thumbnail

**Input:** `video.mp4`

**Output:** `cover.jpg`, made from the first frame.

```console
flowmpeg thumb video.mp4 -o cover.jpg
```

Save a resized PNG from second 12.5:

```console
flowmpeg thumbnail video.mp4 --at 12.5 --width 640 -o moment.png
```

For JPEG output, quality values range from 1 through 31. Smaller values mean
higher quality.

```console
flowmpeg thumb video.mp4 --at 3 --quality 1 -o high-quality.jpg
```

### Create an animated GIF

**Input:** `demo.mp4`

**Output:** `preview.gif`, using the first five seconds at 12 frames per
second and 480 pixels wide.

```console
flowmpeg gif demo.mp4 -o preview.gif
```

Choose another range and size:

```console
flowmpeg gif demo.mp4 --start 20 --duration 3 --width 320 --fps 8 -o feature.gif
```

Use the full source length and original width:

```console
flowmpeg gif short-demo.mp4 --full-length --original-width -o complete.gif
```

Set `--loop -1` for a GIF that does not repeat:

```console
flowmpeg gif demo.mp4 --loop -1 -o once.gif
```

### Draw a waveform

**Input:** `song.mp3`

**Output:** `waveform.png`, a 1200 by 400 peak waveform.

```console
flowmpeg waveform song.mp3 -o waveform.png
```

Choose dimensions, color, and logarithmic scale:

```console
flowmpeg waveform-image song.mp3 --width 1600 --height 500 --color yellow --scale-mode log -o wide-waveform.png
```

Draw channels separately or select another audio track:

```console
flowmpeg waveform movie.mkv --track 1 --split-channels -o commentary-waveform.png
```

### Draw a frequency spectrum

**Input:** `song.mp3`

**Output:** `spectrum.png`, a 1600 by 900 combined-channel spectrum with a
legend.

```console
flowmpeg spectrum song.mp3 -o spectrum.png
```

Draw separate channels with another color map and no legend:

```console
flowmpeg spectrum-image song.mp3 --mode separate --color magma --no-legend --width 1200 --height 600 -o separate-spectrum.png
```

### Build a contact sheet

**Input:** `movie.mp4`

**Output:** `sheet.jpg`, a 4 by 4 image made from frames sampled every five
seconds.

```console
flowmpeg sheet movie.mp4 -o sheet.jpg
```

Build a 5 by 3 sheet sampled every ten seconds:

```console
flowmpeg contact-sheet movie.mp4 --columns 5 --rows 3 --interval 10 --cell-width 240 --cell-height 135 -o overview.jpg
```

### Create video from one image and audio

**Inputs:** `cover.jpg` and `episode.mp3`

**Output:** `episode.mp4`, a 1920 by 1080 video that ends with the audio.

```console
flowmpeg still-video cover.jpg episode.mp3 -o episode.mp4
```

Choose another canvas or audio track:

```console
flowmpeg still-image-video cover.png album.mka --track 1 --width 1280 --height 720 --color white -o track-video.mp4
```

## Creator and delivery jobs

### Compress an upload copy

**Input:** `master.mov`

**Output:** `upload.mp4`, no wider than 1920 pixels at CRF 30.

```console
flowmpeg compress master.mov --crf 30 --max-width 1920 -o upload.mp4
```

Use a lower CRF for more retained quality or a higher CRF for a smaller file.
The accepted range is 0 through 51.

### Prepare common social frames

```console
flowmpeg social input.mp4 --target vertical --fill blur -o vertical.mp4
flowmpeg social input.mp4 --target portrait --fill crop -o portrait.mp4
flowmpeg social input.mp4 --target square --fill fit -o square.mp4
flowmpeg social input.mp4 --target landscape --fill fit -o landscape.mp4
```

Targets are 1080 by 1920, 1080 by 1350, 1080 by 1080, and 1920 by 1080.
Fill modes use a blurred copy, centered crop, or padded fit.

### Reframe to another size

```console
flowmpeg reframe input.mp4 --width 720 --height 1280 -o custom.mp4
```

The image fills the frame and is cropped in the center. Both dimensions must
be even for the web output preset.

### Set frame rate or deinterlace

```console
flowmpeg fps phone.mp4 --fps 30 -o constant.mp4
flowmpeg deinterlace tape.mpg --mode bwdif -o progressive.mp4
```

Frame-rate conversion can drop or repeat frames. Deinterlacing should only be
used on material known to be interlaced.

### Flip, color, or sharpen video

```console
flowmpeg mirror selfie.mp4 -o corrected.mp4
flowmpeg color flat.mp4 --contrast 1.1 --saturation 1.2 -o graded.mp4
flowmpeg sharpen soft.mp4 --amount 1.2 --matrix-size 5 -o sharp.mp4
```

These jobs encode H.264 video and retain the first audio track by default.

### Hold the end or mute a section

```console
flowmpeg freeze announcement.mp4 --seconds 3 -o held.mp4
flowmpeg silence-section meeting.mp4 --start 40 --end 47.5 -o redacted.mp4
```

Freeze adds a still-frame tail and silence. Mute changes only the selected
audio time range.

### Blur a fixed rectangle

```console
flowmpeg privacy-blur street.mp4 --x 800 --y 600 --width 240 --height 100 --radius 18 -o private.mp4
```

The rectangle does not follow motion. Check the full output when the job is
used for privacy.

### Build a boomerang

```console
flowmpeg bounce jump.mp4 --start 2 --duration 2.5 -o bounce.mp4
```

The selected section is played forward and backward. The selection is limited
to 15 seconds because reverse filters buffer it.

## Voice and audio finishing

### Reduce steady noise

```console
flowmpeg denoise room.wav --reduction 10 --noise-floor -52 -o clean.wav
```

### Control dynamic range

```console
flowmpeg dynamics uneven.wav --threshold 0.1 --ratio 4 -o controlled.wav
```

### Run the spoken-word chain

```console
flowmpeg voice recording.wav -o finished.wav
flowmpeg voice mastered.wav --no-denoise --no-compress -o level.wav
```

The default chain applies high-pass and low-pass filters, noise reduction,
compression, loudness normalization, and 48 kHz resampling.

### Trim edge silence or create mono output

```console
flowmpeg desilence take.wav --duration 120 --threshold-db -45 --minimum 0.3 -o tight.wav
flowmpeg mono stereo.wav --codec mp3 --bitrate 128k -o mono.mp3
```

Silence trimming keeps pauses inside the recording. Its required duration must
cover the source and cannot exceed 600 seconds, which bounds reverse-filter
memory. Mono accepts MP3, AAC, Opus, WAV, or FLAC output.

### Crossfade two audio files

```console
flowmpeg crossfade intro.wav episode.wav --duration 2 --curve qsin -o program.wav
```

Both inputs must be longer than the crossfade. The supported curves are
`tri`, `qsin`, and `exp`.

## Subtitle and metadata jobs

### Extract, add, burn, or remove subtitles

```console
flowmpeg subtitles film.mkv --track 0 -o captions.srt
flowmpeg captions film.mp4 captions.srt --language eng -o captioned.mp4
flowmpeg burn-captions film.mp4 captions.srt --font-size 28 -o open-captioned.mp4
flowmpeg strip-subtitles film.mkv -o plain.mp4
```

Extraction supports SRT, WebVTT, and ASS text outputs. Addition creates a
selectable `mov_text` track in MP4. `burn-captions` renders text into the video
frames through FFmpeg's `subtitles` filter and needs an FFmpeg build with
libass support. `--font-name` and `--font-size` set two ASS style fields.

### Remove metadata or tag audio

```console
flowmpeg clean-metadata camera.mkv -o share.mkv
flowmpeg tag episode.m4a --title "Episode 12" --artist "Example Host" -o tagged.m4a
```

Both commands copy selected streams, so input and output extensions must match.
Metadata removal selects the first video, optional first audio, and optional
first subtitle stream.

## Image sequences and audiograms

### Encode numbered images

```console
flowmpeg timelapse frames/frame-%04d.png --fps 24 --start-number 1 -o animation.mp4
```

The pattern must contain `%d` or a padded form such as `%04d`. In a Windows
batch file, write `%%04d` because the batch parser treats `%` specially.

### Create a podcast audiogram

```console
flowmpeg audiogram episode.wav cover.jpg --wave-color DodgerBlue -o episode.mp4
```

The image loops until the selected audio ends. The waveform is centered near
the bottom of the frame.

The [real-world workflow guide](workflows.md) shows matching Python calls and
more input and output details for every command in these sections.

## Inspection and control

### Preview a command

`--dry-run` builds and compiles the plan, but it does not start FFmpeg or read
the input file.

```console
flowmpeg pip main.mp4 inset.mp4 -o result.mp4 --dry-run
```

The displayed FFmpeg command is redacted and intended for inspection.

### Explain the plan

`--explain` prints inputs, filters, mapped stream counts, outputs, and the
replacement policy.

```console
flowmpeg duck talk.mp4 music.mp3 -o result.mp4 --explain --dry-run
```

### Protect or replace output files

The default policy compiles FFmpeg's `-n` flag and checks local output paths
before starting the process.

```console
flowmpeg cut input.mp4 --duration 5 -o existing.mp4
```

If the output exists, the command exits with code 4. Replacement is explicit:

```console
flowmpeg cut input.mp4 --duration 5 -o existing.mp4 --overwrite
```

### Set a timeout

```console
flowmpeg convert large.mov -o large.mp4 --timeout 300
```

Timeout values must be finite and greater than zero.

### Control progress output

Progress is written to stderr. When stderr is redirected, intermediate updates
are hidden and the final update is kept.

```console
flowmpeg cut source.mp4 --duration 20 -o clip.mp4 --no-progress
```

Commands with a known duration use it for percent progress. An explicit value
can be supplied for another job:

```console
flowmpeg convert source.mov -o output.mp4 --expected-duration 95
```

### Use a specific FFmpeg executable

```console
flowmpeg convert input.mov -o output.mp4 --ffmpeg "C:\Tools\ffmpeg\bin\ffmpeg.exe"
```

Flowmpeg always starts the process with `shell=False`.

## Probe media from the terminal

### Read a short report

```console
flowmpeg probe movie.mp4
```

A representative result is:

```text
File: movie.mp4
Container: QuickTime / MOV
Duration: 42.08 seconds
Size: 18.40 MiB
Streams: 2
  video #0: h264, 1920x1080
  audio #1: aac, 48000 Hz, 2 channel(s)
```

### Read typed JSON

```console
flowmpeg probe movie.mp4 --json
```

Typed JSON follows the Python `MediaInfo` model. Values missing from FFprobe
become `null`. The top-level `schema_version` field identifies the report
shape.

### Read raw FFprobe fields

```console
flowmpeg probe movie.mp4 --raw
```

Raw mode keeps the FFprobe object shape. All three display modes redact URL
user information in string values.

Use a custom executable or timeout when needed:

```console
flowmpeg probe movie.mp4 --ffprobe "C:\Tools\ffmpeg\bin\ffprobe.exe" --timeout 10
```

## Audit media against an expected shape

Require both video and audio, then report missing or suspicious fields:

```console
flowmpeg audit movie.mp4 --expect av
```

The report summarizes duration, stream counts, dimensions, frame rate, sample
rate, and channels. Findings have stable `AUD` codes. Errors include a missing
required stream. Warnings include missing probe fields and odd video
dimensions that may fail with common encoders.

Use a stricter threshold in a release script:

```console
flowmpeg check-media delivery.mp4 --expect av --fail-on warning --json
```

`--fail-on error` is the default. `warning` fails on any finding, and `never`
always returns success after a valid probe. A failed audit policy returns exit
code 9. JSON includes the selected policy, `passed`, a summary object, and the
finding list.

The same checks are available in Python:

```python
from flowmpeg import audit_media, probe

result = audit_media(probe("delivery.mp4"), expect="av")
if not result.passes("warning"):
    print(result.findings)
```

## Diagnose an installation

Start with the read-only setup check:

```console
flowmpeg setup
```

It reports tool status, the detected package manager, and its exact suggested
command. No installation runs without `--install` and confirmation.

The human report is suitable for a bug report:

```console
flowmpeg doctor
```

The JSON form is suitable for scripts:

```console
flowmpeg doctor --json
flowmpeg doctor --command podcast-voice --json
flowmpeg doctor --smoke-test --json
```

Doctor and setup JSON include a top-level `schema_version`. Raw probe mode
keeps FFprobe's own object shape and does not add this field.

Core readiness means FFmpeg and FFprobe can both run. Feature groups say which
parts of the command set are supported by the installed FFmpeg build:

- `web-video`
- `webm-video`
- `audio-files`
- `composition`
- `video-effects`
- `animated-gif`
- `analysis-images`
- `audio-processing`
- `reverse`
- `creator-video`
- `voice-cleanup`
- `subtitles`
- `audiogram`

A limited feature group does not make `doctor` fail when both core tools work.
The detailed JSON report contains every tested capability. Command checks add
`required_command`, `command_requirements`, and `command_ready` fields. An
unavailable or unknown command requirement returns exit code 3.

`--smoke-test` encodes one generated frame to a temporary Matroska file and
probes it. The JSON `smoke_test` object reports `ready`, an encode or probe
failure, a timeout, or a skipped test when either executable is unavailable.
The temporary directory is removed after the check.

## Paths in CMD

Quote a path that contains spaces, parentheses, or CMD metacharacters:

```console
flowmpeg cut "C:\Media Files\source (final).mp4" --duration 8 -o "C:\Media Files\clip (final).mp4"
```

Arguments are passed directly to the process. Flowmpeg does not build a shell
string for execution.

Unicode file names can be passed in the same way:

```console
flowmpeg thumb "C:\Media\گفتگو.mp4" --at 5 -o "C:\Media\تصویر.jpg"
```

## Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | The command completed or a preview was printed |
| 1 | Another Flowmpeg error occurred |
| 2 | Arguments or the media plan were invalid |
| 3 | A tool is unavailable, setup is incomplete, or a doctor check is unmet |
| 4 | A local output already exists |
| 5 | FFprobe could not inspect the input |
| 6 | FFmpeg exited with an error |
| 7 | The FFmpeg job reached its timeout |
| 8 | A package manager command failed |
| 9 | A media audit did not meet its selected policy |
| 130 | The command was interrupted |

Argparse also uses code 2 for missing flags and invalid choices.

Failures also include an identifier such as `FMG612`. List or explain them:

```console
flowmpeg errors
flowmpeg explain-error FMG612
```

The [error guide](errors.md) maps every identifier to likely causes and checks.

## Print built-in examples

The installed program carries a small set of commands for quick recall:

```console
flowmpeg examples
flowmpeg examples --category images --json
flowmpeg examples --tag privacy
```

Category, tag, and search filters can be combined. JSON output keeps those
filters and includes each example's category, tags, and command text.

This file is the longer reference. The [Python shortcut guide](shortcuts.md)
shows the same kinds of jobs as one-call `Plan` builders, while the
[graph examples](examples.md) cover custom stream work. The
[workflow guide](workflows.md) pairs 30 terminal commands with Python calls.
