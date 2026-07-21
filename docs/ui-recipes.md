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
