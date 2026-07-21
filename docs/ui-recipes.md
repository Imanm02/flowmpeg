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

### Add a corner logo

Input: `video.mp4` and `logo.png`.

```console
flowmpeg mark video.mp4 logo.png -o branded.mp4
```

Output: an MP4 with the image overlaid on the video.

Why I use it: choosing the two inputs in the UI makes it clear which file is
the video and which file is the mark.

### Add picture in picture

Input: `screen.mp4` and `camera.mp4`.

```console
flowmpeg pip screen.mp4 camera.mp4 -o with-camera.mp4
```

Output: an MP4 with the second video placed over the first.

Why I use it: this is a common tutorial layout, and the UI keeps the base and
inset clips separate.

### Compare clips in a grid

Input: `cam-1.mp4`, `cam-2.mp4`, `cam-3.mp4`, and `cam-4.mp4`.

```console
flowmpeg grid cam-1.mp4 cam-2.mp4 cam-3.mp4 cam-4.mp4 --columns 2 -o grid.mp4
```

Output: a two-column MP4 grid built from the selected videos.

Why I use it: the multi-input field is easier to review than a hand-built
filter graph.

### Make a short GIF

Input: `sample.mp4`.

```console
flowmpeg gif sample.mp4 --start 3 --duration 4 -o preview.gif
```

Output: a palette-based animated GIF for a short selected range.

Why I use it: the UI keeps the start time and duration visible while the
palette work happens behind the command.

### Save a thumbnail

Input: `video.mp4`.

```console
flowmpeg thumb video.mp4 --at 12 -o moment.jpg
```

Output: one JPG image from the selected timestamp.

Why I use it: I can pick a review frame without typing a seek command.

### Extract review frames

Input: `video.mp4`.

```console
flowmpeg frames video.mp4 --interval 5 -o review-frames
```

Output: a marked folder containing numbered image files sampled every 5
seconds.

Why I use it: the UI makes the output folder explicit, which matters because
this command creates several files.

### Build a contact sheet

Input: `video.mp4`.

```console
flowmpeg sheet video.mp4 --interval 8 -o sheet.jpg
```

Output: one JPG contact sheet with sampled frames laid out in a grid.

Why I use it: a single image is often faster to scan than scrubbing through the
whole file.

### Draw an audio waveform

Input: `song.mp3`.

```console
flowmpeg waveform song.mp3 -o waveform.png
```

Output: a PNG waveform image for the audio.

Why I use it: it gives a quick visual check of silence, loud sections, and
rough pacing.

### Package HLS delivery

Input: `movie.mp4`.

```console
flowmpeg hls movie.mp4 --segment-duration 4 -o movie-hls
```

Output: an owned HLS folder with a playlist and media segments.

Why I use it: the UI makes the artifact folder clear before a multi-file
delivery package is created.

### Package DASH delivery

Input: `movie.mp4`.

```console
flowmpeg dash movie.mp4 --segment-duration 2 -o movie-dash
```

Output: an owned MPEG-DASH folder with a manifest and segments.

Why I use it: the UI keeps the destination folder and segment length visible
for a package with several files.

### Audit delivery shape

Input: `delivery.mp4`.

```console
flowmpeg audit delivery.mp4 --expect av --max-duration 60 --width 1920 --height 1080
```

Output: a pass or finding report with stable finding codes.

Why I use it: I can check the file against a delivery policy before I send it.

### Compare before and after

Input: `original.mp4` and `compressed.mp4`.

```console
flowmpeg compare original.mp4 compressed.mp4
```

Output: a report comparing stream counts, codecs, dimensions, duration, and
container size.

Why I use it: I can see what changed after a conversion without opening two
separate probe reports.

### Measure visual quality

Input: `reference.mp4` and `candidate.mp4`.

```console
flowmpeg quality reference.mp4 candidate.mp4 --duration 30
```

Output: PSNR and SSIM values for the compared range.

Why I use it: this gives a numeric check when a smaller file still needs to
look close to the source.

### Find quiet ranges

Input: `interview.wav`.

```console
flowmpeg find-silence interview.wav --threshold-db -45 --min-duration 0.5
```

Output: start, end, and duration values for detected silent intervals.

Why I use it: the report gives edit candidates without changing the original
recording.

### Find black video ranges

Input: `tape.mp4`.

```console
flowmpeg find-black tape.mp4 --picture-threshold 0.98 --min-duration 0.5
```

Output: time ranges where the picture is mostly black.

Why I use it: this helps find slates, gaps, or capture dropouts before cutting.

### Find scene changes

Input: `interview.mp4`.

```console
flowmpeg scenes interview.mp4 --threshold 0.35
```

Output: scene-change times and scores.

Why I use it: strong scene changes are useful thumbnail and chapter candidates.

### Suggest a crop rectangle

Input: `letterboxed.mp4`.

```console
flowmpeg crop-report letterboxed.mp4 --duration 30
```

Output: ranked crop candidates and the recommended FFmpeg crop value.

Why I use it: the report gives a starting rectangle before I commit to a crop
operation.

### Convert a folder batch

Input: local files matching `recordings/*.mov`.

```console
flowmpeg batch "recordings/*.mov" --name-suffix=-web -o converted
```

Output: converted MP4 files in the selected output folder, processed in order.

Why I use it: the UI makes the input pattern, suffix, and output folder easy to
review before a batch starts.

### Remux without re-encoding

Input: `camera.mp4`.

```console
flowmpeg remux camera.mp4 -o camera.mkv
```

Output: a new container file that copies selected streams when compatible.

Why I use it: the UI keeps this separate from transcoding, so I do not choose a
slower encode by mistake.

### Remove shareable metadata

Input: `camera.mkv`.

```console
flowmpeg clean-metadata camera.mkv -o share.mkv
```

Output: a copied media file with standard metadata fields cleared.

Why I use it: I can make a sharing copy without changing the original file.

### Add a title tag

Input: `camera.mp4`.

```console
flowmpeg tag-media camera.mp4 --title "Camera master" -o tagged.mp4
```

Output: a media file with the selected title metadata.

Why I use it: the form keeps metadata text visible and quoted correctly in the
previewed command.

### Turn images into video

Input: numbered files like `frames/frame-0001.png`.

```console
flowmpeg timelapse frames/frame-%04d.png -o timelapse.mp4
```

Output: an MP4 created from the numbered image sequence.

Why I use it: the UI keeps the pattern and output file together, which reduces
mistakes with frame sequence names.

### Make a podcast audiogram

Input: `episode.wav` and `cover.jpg`.

```console
flowmpeg audiogram episode.wav cover.jpg -o episode.mp4
```

Output: a video with cover art and waveform-style motion for the audio.

Why I use it: it turns an audio-only file into a shareable video without a
custom composition graph.

### Fill a wide frame with blur

Input: `portrait.mp4`.

```console
flowmpeg blurred-background portrait.mp4 -o portrait-wide.mp4
```

Output: a wide MP4 where a blurred copy fills the empty frame behind the
original video.

Why I use it: the result looks intentional when a vertical clip must fit a
horizontal layout.

### Blur a private region

Input: `street.mp4`.

```console
flowmpeg privacy-blur street.mp4 --x 20 --y 20 --width 200 --height 80 -o private.mp4
```

Output: an MP4 with one fixed rectangular region blurred.

Why I use it: coordinates are easier to review in named form fields than in a
raw filter string.

### Change clip speed

Input: `lesson.mp4`.

```console
flowmpeg speed lesson.mp4 --factor 1.5 -o lesson-fast.mp4
```

Output: a faster MP4 with matching video timing and audio tempo.

Why I use it: previewing the factor helps avoid accidentally making a clip too
slow or too fast.
