# HLS and DASH packages

HLS and DASH produce a manifest plus several media files. Flowmpeg treats that
group as one owned artifact set instead of pretending the manifest is the only
output.

## Create HLS in one line

```console
flowmpeg hls input.mp4 -o delivery-hls
```

The output argument is a dedicated directory. A successful package looks like:

```text
delivery-hls/
|-- .flowmpeg-artifacts.json
|-- index.m3u8
|-- segment-00000.ts
|-- segment-00001.ts
`-- segment-00002.ts
```

The command prints the manifest and number of media artifacts:

```text
Created 4 HLS artifacts: delivery-hls/index.m3u8
```

The default segment target is six seconds. H.264 video and optional AAC audio
are encoded with forced keyframes at segment boundaries.

```console
flowmpeg hls lecture.mp4 --segment-duration 4 --crf 21 --audio-bitrate 160k -o lecture-hls
flowmpeg hls silent-animation.mp4 --no-audio -o animation-hls
```

## Create MPEG-DASH in one line

```console
flowmpeg dash input.mp4 -o delivery-dash
```

A DASH package uses an MPD manifest and fragmented MP4 media:

```text
delivery-dash/
|-- .flowmpeg-artifacts.json
|-- manifest.mpd
|-- init-0.m4s
|-- init-1.m4s
|-- chunk-0-00001.m4s
`-- chunk-1-00001.m4s
```

The default DASH segment target is four seconds:

```console
flowmpeg mpeg-dash lesson.mp4 --segment-duration 2 -o lesson-dash
flowmpeg dash animation.mp4 --no-audio --crf 18 -o animation-dash
```

## Pick a package format

| Need | HLS | DASH |
|---|---|---|
| Manifest | `index.m3u8` | `manifest.mpd` |
| Media files | MPEG-TS segments | Fragmented MP4 segments |
| Default segment target | 6 seconds | 4 seconds |
| Video | H.264 | H.264 |
| Audio | Optional AAC | Optional AAC |
| Flowmpeg ownership marker | Yes | Yes |

Without rendition settings, the package has one video representation and one
optional audio representation. A ladder creates several video representations
for a player to switch between as available bandwidth changes.

## Package several quality levels

```console
flowmpeg hls lesson.mp4 --rendition hd:1280:720:2500 sd:640:360:800 -o lesson-adaptive
flowmpeg dash lesson.mp4 --rendition hd:1280:720:2500 sd:640:360:800 -o lesson-dash-adaptive
```

Each entry is `NAME:WIDTH:HEIGHT:KBPS`. Names identify the HLS variant files.
Dimensions are upper bounds, preserve aspect ratio, and never enlarge a small
source. The last value is the video target bitrate in kilobits per second.
Rate control uses that target, the same maximum rate, and a two-second buffer.
`--crf` applies only when no renditions are provided.

| Entry | Maximum frame | Video target | Typical use |
|---|---|---|---|
| `hd:1280:720:2500` | 1280 by 720 | 2500 kbps | Main playback |
| `sd:640:360:800` | 640 by 360 | 800 kbps | Slower connection |

HLS creates `index.m3u8`, `variant-hd.m3u8`, `variant-sd.m3u8`, and separately
named segment files. DASH creates an MPD with one video adaptation set holding
both representations and an optional audio adaptation set. HLS muxes a copy
of the selected audio into each variant; DASH shares one audio representation.

The encoder forces segment-boundary keyframes and disables scene-cut
keyframes. HLS segment targets must be at least one second. An HLS master
missing a requested variant is rejected before the artifact set is published.
FFprobe detects silent sources during execution and removes audio mappings
from the entire ladder. Dry runs do not probe and display the requested audio
policy; use `--no-audio` for an exact video-only preview.

```python
from flowmpeg import VideoRendition, hls_package

workflow = hls_package(
    "lesson.mp4",
    "lesson-adaptive",
    renditions=(
        VideoRendition("hd", 1280, 720, 2500),
        VideoRendition("sd", 640, 360, 800),
    ),
)
print(workflow.explain())
result = workflow.run(timeout=600)
```

In the local UI, choose Package HLS or Package DASH and enter one rendition
per line in the Renditions field. Input paths, overwrite confirmation, command
previews, and cancellation work through the same local job controls.

The model accepts up to eight uniquely named renditions. Width and height must
be even integers from 2 through 8192. Bitrates must be positive integers. This
is a VOD ladder; it does not add a live server, DRM, or alternate-language
audio groups. The [FFmpeg muxer reference](https://ffmpeg.org/ffmpeg-formats.html)
documents the HLS variant and DASH adaptation-set options used here.

## Inspect without writing

```console
flowmpeg hls input.mp4 -o delivery-hls --dry-run --explain
flowmpeg dash input.mp4 -o delivery-dash --dry-run --explain
```

Dry runs do not create the destination directory. The explanation names the
owned directory, manifest, segment length, and exact FFmpeg command.

Check the default command requirements before a deployment:

```console
flowmpeg doctor --command hls
flowmpeg doctor --command dash
flowmpeg doctor --require segmented-video
```

The exact checks require the H.264 and AAC encoders plus the selected muxer.

## How directory ownership works

Flowmpeg writes `.flowmpeg-artifacts.json` only after FFmpeg succeeds and the
manifest exists. The marker records the package kind, manifest name, and
relative artifact list.

```text
new directory
     |
     v
encode in owned directory -- failure --> remove created partial directory
     |
     v
verify manifest --> write marker --> publish result
```

An existing directory without that marker is never cleared:

```console
flowmpeg hls input.mp4 -o my-existing-folder --overwrite
```

That command returns an output-exists error if `my-existing-folder` is not a
matching Flowmpeg-owned HLS package. Personal files remain untouched.

## Replace an owned package

```console
flowmpeg hls updated.mp4 -o delivery-hls --overwrite
```

Replacement does not encode over the live package. Flowmpeg creates a sibling
staging directory first:

```text
delivery-hls                    current package
.delivery-hls.flowmpeg-stage-*  new package being encoded
```

After the staged manifest and marker are ready, the directories are swapped.
If encoding fails, the current package stays in place and the created stage is
removed. An HLS-owned directory cannot be replaced by a DASH workflow, or the
other way around.

## Use package workflows in Python

```python
from flowmpeg import hls_package

workflow = hls_package(
    "input.mp4",
    "delivery-hls",
    segment_duration=4,
    crf=21,
)

print(workflow.explain())
result = workflow.run(timeout=300)
print(result.manifest)
print(result.files)
```

DASH uses the same result model:

```python
from flowmpeg import dash_package

workflow = dash_package("input.mp4", "delivery-dash", segment_duration=2)
result = workflow.run(timeout=300)
print(result.kind)
```

`ArtifactSet.files` contains final paths after a staged replacement. The
embedded `RunResult` points at the final manifest instead of the temporary
staging path.

## Current package boundary

The workflows own files under one dedicated directory. They do not upload the
package, start a web server, or change cache headers. Those actions depend on a
deployment target and should stay separate from media encoding.
