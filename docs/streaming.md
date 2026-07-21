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

These first package workflows create one video representation and one optional
audio representation. An adaptive bitrate ladder needs a representation model
before it can claim to describe several renditions correctly.

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
