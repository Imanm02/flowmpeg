# Reduce video file size

This is the Flowmpeg guide I wanted for phone videos, screen recordings, and
large MOV files that are too heavy to send. The common job is simple to say:
make the file much smaller while keeping it close enough that nobody notices
the difference in normal playback.

The honest target is same-looking, not mathematically identical. If FFmpeg
re-encodes the video with CRF, the file is lossy. The point is to spend bits
where the eye cares and stop spending bits where the source is bigger than the
delivery need.

## The one-liner I use first

```console
flowmpeg shrink IMG_9357.MOV -o IMG_9357.mp4
```

That creates a small MP4 using:

| Setting | Default | Why |
| --- | --- | --- |
| Video codec | HEVC | Usually smaller than H.264 at the same visible quality |
| Max height | 720 | Good for chat apps, notes, and quick sharing |
| Frame rate | 30 fps | Cuts 60 fps phone footage in half |
| CRF | 28 | A sane starting point for size reduction |
| Audio | AAC 96k | Safer MP4 playback than Opus |

Use a dry run when you want to see the FFmpeg command without creating the
file:

```console
flowmpeg shrink IMG_9357.MOV -o IMG_9357.mp4 --dry-run
```

## Your exact tiny MOV command

Your FFmpeg command:

```console
ffmpeg -i "IMG_9357.MOV" -r 30 -vf "scale=-2:720" -c:v libx265 -crf 28 -c:a libopus -b:a 32K -strict experimental -max_muxing_queue_size 1024 "IMG_9357.mp4"
```

The Flowmpeg version is:

```console
flowmpeg shrink "IMG_9357.MOV" --codec hevc --max-height 720 --fps 30 --crf 28 --audio-codec opus --audio-bitrate 32k -o "IMG_9357.mp4"
```

Expected output:

| Output part | Result |
| --- | --- |
| Container | MP4 |
| Video | HEVC, CRF 28 |
| Size | Height capped at 720 pixels, width kept proportional and even |
| Timing | 30 fps |
| Audio | Opus at 32k |
| Extra muxing guard | `-max_muxing_queue_size 1024` |

Opus at 32k is very small, but not every MP4 player likes Opus. For a safer
MP4 that opens in more places, keep AAC:

```console
flowmpeg shrink "IMG_9357.MOV" --codec hevc --max-height 720 --fps 30 --crf 28 --audio-codec aac --audio-bitrate 64k -o "IMG_9357-small.mp4"
```

## What each control really does

| Control | More shrink | More quality | Notes |
| --- | --- | --- | --- |
| `--max-height` | Use 540 or 720 | Use 1080 or keep size | Scaling usually saves more than tiny CRF changes |
| `--fps` | Use 24 or 30 | Use 60 or `--keep-fps` | 60 fps to 30 fps can halve video frames |
| `--crf` | Raise it | Lower it | 23 is better quality, 30 is smaller, 34 is aggressive |
| `--codec` | `hevc` | `h264` for older devices | HEVC is smaller, H.264 plays almost everywhere |
| `--audio-bitrate` | 32k or 64k | 96k or 128k | Speech can go lower than music |
| `--encoder-preset` | `slow` for smaller files | `fast` for faster exports | Preset changes encode time, not the CRF meaning |

I usually change only one knob at a time. If the output is too large, I lower
the frame size first. If the output looks rough, I lower CRF before changing
the codec.

## Pixel and frame impact

These are rough shape numbers before codec decisions:

| Source shape | Pixels per frame | Compared with 4K |
| --- | ---: | ---: |
| 3840 by 2160 | 8.29 million | Baseline |
| 1920 by 1080 | 2.07 million | About 75 percent fewer pixels |
| 1280 by 720 | 0.92 million | About 89 percent fewer pixels |
| 960 by 540 | 0.52 million | About 94 percent fewer pixels |

Frame rate has the same kind of effect:

```text
60 fps  ##############################
30 fps  ###############
24 fps  ############
```

That is why the phone-video recipe uses 720p and 30 fps. It attacks the two
largest parts of many camera files before the encoder even starts deciding how
many bits each frame deserves.

## Ready commands for phone videos

Small MP4 with Flowmpeg defaults:

```console
flowmpeg shrink IMG_9357.MOV -o IMG_9357-small.mp4
```

Same idea, but safer audio for more players:

```console
flowmpeg shrink IMG_9357.MOV --audio-codec aac --audio-bitrate 64k -o IMG_9357-aac.mp4
```

Tiny audio, close to your original command:

```console
flowmpeg shrink IMG_9357.MOV --audio-codec opus --audio-bitrate 32k -o IMG_9357-tiny-audio.mp4
```

Better quality 720p:

```console
flowmpeg shrink IMG_9357.MOV --crf 24 --max-height 720 --audio-bitrate 96k -o IMG_9357-better.mp4
```

More aggressive 720p:

```console
flowmpeg shrink IMG_9357.MOV --crf 32 --max-height 720 --audio-bitrate 64k -o IMG_9357-smaller.mp4
```

Very small 540p for chat:

```console
flowmpeg shrink IMG_9357.MOV --max-height 540 --crf 32 --audio-codec opus --audio-bitrate 32k -o IMG_9357-chat.mp4
```

Keep 1080p but use HEVC and 30 fps:

```console
flowmpeg shrink IMG_9357.MOV --max-height 1080 --fps 30 --crf 28 -o IMG_9357-1080.mp4
```

Keep source dimensions and only re-encode:

```console
flowmpeg shrink IMG_9357.MOV --keep-size --keep-fps --crf 28 -o IMG_9357-hevc.mp4
```

Keep source size but reduce 60 fps to 30 fps:

```console
flowmpeg shrink IMG_9357.MOV --keep-size --fps 30 --crf 28 -o IMG_9357-30fps.mp4
```

Keep timing but make a smaller frame:

```console
flowmpeg shrink IMG_9357.MOV --keep-fps --max-height 720 --crf 28 -o IMG_9357-720-keep-fps.mp4
```

## Compatibility presets

HEVC is great when the receiver uses a newer phone, browser, or operating
system:

```console
flowmpeg shrink clip.mov --codec hevc --crf 28 --max-height 720 -o clip-hevc.mp4
```

H.264 is safer for older devices, uploads, support desks, and projectors:

```console
flowmpeg shrink clip.mov --codec h264 --crf 27 --max-height 720 --audio-codec aac --audio-bitrate 96k -o clip-h264.mp4
```

If a website accepts WebM, VP9 can be a good delivery choice:

```console
flowmpeg webm clip.mov --crf 34 --audio-bitrate 64k -o clip.webm
```

If file size matters more than encode time and WebM is accepted, try AV1:

```console
flowmpeg av1 clip.mov --crf 38 --speed 8 --audio-bitrate 64k -o clip-av1.webm
```

## Audio choices

For speech notes:

```console
flowmpeg shrink meeting.mov --audio-codec opus --audio-bitrate 32k -o meeting-small.mp4
```

For normal phone video:

```console
flowmpeg shrink family.mov --audio-codec aac --audio-bitrate 96k -o family-small.mp4
```

For music clips:

```console
flowmpeg shrink rehearsal.mov --audio-codec aac --audio-bitrate 128k -o rehearsal-small.mp4
```

For silent video:

```console
flowmpeg shrink screen.mov --no-audio -o screen-small.mp4
```

To extract just the audio as a tiny Opus file:

```console
flowmpeg audio lecture.mov --codec opus --bitrate 32k -o lecture.opus
```

## Screen recordings

Most screen recordings have flat regions, sharp text, and sometimes a high
frame rate. Try H.264 first if the file must open everywhere:

```console
flowmpeg shrink screen-recording.mov --codec h264 --max-height 1080 --fps 30 --crf 26 --audio-bitrate 64k -o screen-share.mp4
```

For a smaller personal archive:

```console
flowmpeg shrink screen-recording.mov --codec hevc --max-height 1080 --fps 30 --crf 28 --audio-bitrate 64k -o screen-archive.mp4
```

For a tiny bug report attachment:

```console
flowmpeg shrink screen-recording.mov --codec h264 --max-height 720 --fps 15 --crf 30 --no-audio -o screen-bug.mp4
```

## Archive copies

If the source matters, do not throw away too much on the first pass. Start with
1080p or keep the original size:

```console
flowmpeg shrink camera.mov --codec hevc --max-height 1080 --fps 30 --crf 24 --audio-bitrate 128k -o camera-archive.mp4
```

```console
flowmpeg shrink camera.mov --keep-size --keep-fps --codec hevc --crf 24 --audio-bitrate 128k -o camera-archive-full.mp4
```

If the goal is only to change the container without saving size, remux instead:

```console
flowmpeg remux camera.mp4 -o camera.mkv
```

## Quick before and after checks

Check that the output has audio and video:

```console
flowmpeg audit IMG_9357.mp4 --expect av
```

Check the delivery shape:

```console
flowmpeg audit IMG_9357.mp4 --expect av --width 1280 --height 720
```

Compare source and output file size, duration, codecs, and dimensions:

```console
flowmpeg compare IMG_9357.MOV IMG_9357.mp4
```

Measure PSNR and SSIM on a short section:

```console
flowmpeg quality IMG_9357.MOV IMG_9357.mp4 --duration 30
```

Probe exact stream details:

```console
flowmpeg probe IMG_9357.mp4
```

## Pick by goal

| Goal | Command |
| --- | --- |
| Send to a friend | `flowmpeg shrink input.mov -o output.mp4` |
| Keep more detail | `flowmpeg shrink input.mov --crf 24 --max-height 1080 -o output.mp4` |
| Make it tiny | `flowmpeg shrink input.mov --max-height 540 --crf 32 --audio-codec opus --audio-bitrate 32k -o output.mp4` |
| Older devices | `flowmpeg shrink input.mov --codec h264 --audio-codec aac -o output.mp4` |
| No audio | `flowmpeg shrink input.mov --no-audio -o output.mp4` |
| Keep original size | `flowmpeg shrink input.mov --keep-size --keep-fps -o output.mp4` |
| Shrink a folder | `flowmpeg shrink-batch "clips/*.MOV" -o small-clips` |
| Shrink folders recursively | `flowmpeg shrink-batch clips -o small-clips --recursive` |

## Copy-paste command matrix

These are the commands I would try first before tuning anything.

| Job | Single file | Whole folder or pattern |
| --- | --- | --- |
| Normal share copy | `flowmpeg shrink input.mov -o output.mp4` | `flowmpeg shrink-batch "clips/*.MOV" -o small-clips` |
| Tiny chat copy | `flowmpeg shrink input.mov --max-height 540 --fps 24 --crf 34 --audio-codec opus --audio-bitrate 32k -o output.mp4` | `flowmpeg shrink-batch "clips/*.MOV" --max-height 540 --fps 24 --crf 34 --audio-codec opus --audio-bitrate 32k -o chat-clips` |
| Safer older-device copy | `flowmpeg shrink input.mov --codec h264 --audio-codec aac --crf 27 -o output.mp4` | `flowmpeg shrink-batch "clips/*.MOV" --codec h264 --audio-codec aac --crf 27 -o safe-clips` |
| Better 1080p copy | `flowmpeg shrink input.mov --max-height 1080 --crf 24 --audio-bitrate 128k -o output.mp4` | `flowmpeg shrink-batch "clips/*.MOV" --max-height 1080 --crf 24 --audio-bitrate 128k -o archive-clips` |
| Screen recording | `flowmpeg shrink screen.mov --codec h264 --max-height 1080 --fps 30 --crf 26 --audio-bitrate 64k -o screen.mp4` | `flowmpeg shrink-batch "screens/*.mov" --codec h264 --max-height 1080 --fps 30 --crf 26 --audio-bitrate 64k -o small-screens` |
| Silent screen recording | `flowmpeg shrink screen.mov --codec h264 --max-height 720 --fps 15 --crf 30 --no-audio -o screen.mp4` | `flowmpeg shrink-batch "screens/*.mov" --codec h264 --max-height 720 --fps 15 --crf 30 --no-audio -o tiny-screens` |
| Keep source shape | `flowmpeg shrink input.mov --keep-size --keep-fps --crf 28 -o output.mp4` | `flowmpeg shrink-batch "masters/*.MOV" --keep-size --keep-fps --crf 28 -o master-copies` |
| Speech notes | `flowmpeg shrink note.mov --audio-codec opus --audio-bitrate 32k -o note.mp4` | `flowmpeg shrink-batch "notes/*.MOV" --audio-codec opus --audio-bitrate 32k -o small-notes` |

For an unknown folder, I would start here:

```console
flowmpeg doctor --require size-video
flowmpeg shrink-batch "clips/*" -o small-clips --dry-run --json
flowmpeg shrink-batch "clips/*" -o small-clips
```

For a folder that must play almost anywhere:

```console
flowmpeg shrink-batch "clips/*" --codec h264 --audio-codec aac --crf 27 -o safe-clips
```

For a folder where size matters more than compatibility:

```console
flowmpeg shrink-batch "clips/*" --max-height 540 --fps 24 --crf 34 --audio-codec opus --audio-bitrate 32k -o tiny-clips
```

## Shrink many files

Use `shrink-batch` when a folder or quoted pattern needs the same settings on
every supported local video:

```console
flowmpeg shrink-batch "clips/*.MOV" -o small-clips
```

Expected output names use `-small` by default:

| Source | Output |
| --- | --- |
| `IMG_9357.MOV` | `small-clips/IMG_9357-small.mp4` |
| `screen.mov` | `small-clips/screen-small.mp4` |
| `meeting.mkv` | `small-clips/meeting-small.mp4` |

Preview every FFmpeg command without creating files:

```console
flowmpeg shrink-batch "clips/*.MOV" -o small-clips --dry-run
flowmpeg shrink-batch "clips/*.MOV" -o small-clips --dry-run --json
```

Shrink every video under a folder:

```console
flowmpeg shrink-batch clips -o small-clips --recursive
```

Use tiny audio for speech-heavy folders:

```console
flowmpeg shrink-batch "meetings/*.MOV" --audio-codec opus --audio-bitrate 32k -o small-meetings
```

Use H.264 and AAC for the safest batch:

```console
flowmpeg shrink-batch "client/*.MOV" --codec h264 --audio-codec aac --crf 27 -o client-small
```

Use a higher quality archive batch:

```console
flowmpeg shrink-batch "camera/*.MOV" --max-height 1080 --crf 24 --audio-bitrate 128k -o camera-archive
```

Keep the original frame size and frame rate while changing codec:

```console
flowmpeg shrink-batch "masters/*.MOV" --keep-size --keep-fps --crf 24 -o masters-hevc
```

Let later files continue after one bad source:

```console
flowmpeg shrink-batch clips -o small-clips --continue-on-error
```

If you need a one-off command that `shrink-batch` does not expose yet,
PowerShell can still call `shrink` once per file:

```powershell
Get-ChildItem . -Filter *.MOV | ForEach-Object {
    flowmpeg shrink $_.FullName -o "$($_.BaseName)-small.mp4"
}
```

And Bash can do the same:

```bash
for file in *.MOV; do
  flowmpeg shrink "$file" -o "${file%.*}-small.mp4"
done
```

## Python shortcut

```python
from flowmpeg import shortcuts as ff

ff.shrink_video(
    "IMG_9357.MOV",
    "IMG_9357.mp4",
    codec="hevc",
    max_height=720,
    fps=30,
    crf=28,
    audio_codec="opus",
    audio_bitrate="32k",
).run()
```

Build the plan first if an app needs to show the exact command:

```python
from flowmpeg import shortcuts as ff

plan = ff.shrink_video(
    "IMG_9357.MOV",
    "IMG_9357.mp4",
    codec="hevc",
    max_height=720,
    fps=30,
    crf=28,
)

print(plan.command())
print(plan.explain())
```

## Tool checks and install help

Flowmpeg is the front door. FFmpeg and FFprobe are still the media engine. Check
them before a long shrink job:

```console
flowmpeg setup
flowmpeg doctor --require size-video
flowmpeg shrink IMG_9357.MOV -o IMG_9357.mp4 --dry-run
```

If the tools are missing and a supported package manager is available,
Flowmpeg can print the install command. Installation only runs when requested:

```console
flowmpeg setup --install
```

Common failures:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `libx265` missing | FFmpeg build lacks HEVC encoder | Use `--codec h264` or install a fuller FFmpeg build |
| Output will not open | Receiver dislikes HEVC or Opus in MP4 | Use `--codec h264 --audio-codec aac` |
| File still too large | Resolution or CRF is still generous | Try `--max-height 540` or raise `--crf` |
| Video looks rough | CRF too high or frame too small | Lower `--crf` or use `--max-height 1080` |
| Destination exists | Flowmpeg protects outputs | Add `--overwrite` after checking the old file |
