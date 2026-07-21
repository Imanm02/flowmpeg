# UI recipe book

I use this page as a practical map for the local browser UI. Each recipe names
the input files, the Flowmpeg command to preview or run, the output to expect,
and the reason I would reach for it.

The UI runs the same `flowmpeg` command shown in each block. Open it with:

```console
flowmpeg ui
```

## Recipes

### Create demo media

Input: an empty folder such as `flowmpeg-demo`.

```console
flowmpeg demo-media flowmpeg-demo --overwrite
```

Output: small video, audio, image, subtitle, and image-sequence files in that
folder.

Why I use it: it gives me safe local files for testing the UI before I touch a
real project.

### Check local tools

Input: the current computer.

```console
flowmpeg doctor --smoke-test
```

Output: a capability report with the FFmpeg and FFprobe paths, feature groups,
and a tiny encode-and-probe test result.

Why I use it: I want setup problems to appear before a long encode starts.

### Inspect a media file

Input: `sample.mp4`.

```console
flowmpeg probe sample.mp4
```

Output: container duration, size, streams, codecs, dimensions, and audio layout.

Why I use it: I can confirm track shape before choosing trim, audio extraction,
captions, or delivery settings.

### Convert to a browser MP4

Input: `recording.mov`.

```console
flowmpeg convert recording.mov -o recording.mp4
```

Output: an MP4 with H.264 video and AAC audio.

Why I use it: this is the plain delivery file I can send to a browser, chat
app, or video review tool.

### Cut an exact clip

Input: `sample.mp4`.

```console
flowmpeg cut sample.mp4 --start 5 --duration 10 -o clip.mp4
```

Output: a new MP4 containing the 10 second range that starts at 5 seconds.

Why I use it: previewing the command makes the time math visible before the
edit runs.

### Resize for review

Input: `sample.mp4`.

```console
flowmpeg resize sample.mp4 --width 1280 -o review.mp4
```

Output: a smaller MP4 whose width is 1280 pixels while the height follows the
source aspect ratio.

Why I use it: I can make a review copy without typing filter syntax.

### Compress a delivery copy

Input: `master.mov`.

```console
flowmpeg compress master.mov --crf 24 --width 1280 -o delivery.mp4
```

Output: an H.264 MP4 with a smaller review size and AAC audio.

Why I use it: the CRF and width controls are easier to compare in a form than
inside a long command line.

### Make a vertical social clip

Input: `demo.mp4`.

```console
flowmpeg social demo.mp4 --target vertical -o vertical.mp4
```

Output: a 1080 by 1920 MP4 with the source placed into a vertical frame.

Why I use it: the UI exposes the target choice without asking me to remember
the canvas dimensions.

### Extract audio from video

Input: `interview.mp4`.

```console
flowmpeg audio interview.mp4 -o interview.mp3
```

Output: an audio-only MP3 file from the selected media track.

Why I use it: this is a quick way to prepare transcripts, voice cleanup, or
podcast editing.

### Normalize speech loudness

Input: `voice.wav`.

```console
flowmpeg normalize-exact voice.wav --target-integrated -16 -o voice-ready.wav
```

Output: a measured, normalized audio file aimed at the selected integrated LUFS
target.

Why I use it: the UI keeps the target visible while Flowmpeg handles the
measure-then-encode workflow.

### Clean a voice recording

Input: `recording.wav`.

```console
flowmpeg voice recording.wav -o finished.wav
```

Output: a speech-focused audio file with the voice chain applied.

Why I use it: one form collects the common voice cleanup settings I would
otherwise repeat by hand.

### Mix two audio tracks

Input: `host.wav` and `guest.wav`.

```console
flowmpeg mix host.wav guest.wav -o conversation.wav
```

Output: one mixed audio file containing both inputs.

Why I use it: the UI makes source order obvious before FFmpeg combines the
tracks.

### Duck music under speech

Input: `talk.mp4` and `music.mp3`.

```console
flowmpeg duck talk.mp4 music.mp3 -o ducked.mp4
```

Output: an MP4 where the music lowers under the spoken track.

Why I use it: sidechain-style audio work is easier to trust when the form names
the speech and music sources separately.

### Burn open captions

Input: `lesson.mp4` and `captions.srt`.

```console
flowmpeg burn-captions lesson.mp4 captions.srt -o lesson-open.mp4
```

Output: an MP4 where caption text is rendered into the video frames.

Why I use it: open captions survive players that ignore selectable subtitle
tracks.

### Add selectable captions

Input: `movie.mp4` and `subtitles.srt`.

```console
flowmpeg captions movie.mp4 subtitles.srt -o captioned.mp4
```

Output: an MP4 with a selectable subtitle track.

Why I use it: this keeps the video image unchanged while still carrying text
for players that support captions.
