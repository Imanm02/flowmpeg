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
