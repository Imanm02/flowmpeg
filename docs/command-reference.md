# Generated command reference

This file is generated from `COMMAND_CATALOG`. Run
`python scripts/command_reference.py --check` before a release.

Tags describe use cases. Capability groups describe the broad doctor
check associated with an editing command.

## Video (16)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `transcode` | `convert` | media | media | `creator`, `delivery`, `silent-input` | `web-video` |
| `trim` | `cut` | media | media | `creator`, `delivery`, `silent-input` | `web-video` |
| `resize` | `scale` | media | media | `creator`, `delivery`, `silent-input` | `web-video` |
| `remove-audio` | `mute`, `strip-audio` | media | video | `creator`, `copy`, `privacy`, `silent-input` | none |
| `compress-video` | `compress`, `smaller` | media | media | `creator`, `delivery`, `silent-input` | `web-video` |
| `reframe` | `fill-frame` | media | media | `creator`, `delivery`, `silent-input` | `composition` |
| `social-video` | `social` | media | media | `creator`, `delivery`, `silent-input` | `composition` |
| `set-frame-rate` | `fps` | media | media | `creator`, `archive`, `silent-input` | `creator-video` |
| `deinterlace` | none | media | media | `creator`, `archive`, `silent-input` | `creator-video` |
| `flip-video` | `flip`, `mirror` | media | media | `creator`, `silent-input` | `video-effects` |
| `rotate` | none | media | media | `creator`, `silent-input` | `video-effects` |
| `crop` | none | media | media | `creator`, `silent-input` | `composition` |
| `change-speed` | `speed` | media | media | `creator`, `silent-input` | `audio-processing` |
| `freeze-end` | `freeze` | media | media | `creator`, `silent-input` | `creator-video` |
| `mute-section` | `silence-section` | media | media | `creator` | `audio-processing` |
| `boomerang` | `bounce` | media | media | `creator`, `silent-input` | `reverse` |

## Audio (13)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `replace-audio` | `swap-audio` | media | video | `podcast` | `web-video` |
| `extract-audio` | `audio` | media | audio | `podcast`, `copy` | `audio-files` |
| `mix-audio` | `mix`, `mix-audio-files` | audio | audio | `podcast`, `creator` | `audio-processing` |
| `normalize-loudness` | `normalize` | audio | audio | `podcast`, `delivery` | `audio-processing` |
| `denoise-audio` | `denoise` | audio | audio | `podcast` | `voice-cleanup` |
| `compress-audio` | `dynamics` | audio | audio | `podcast` | `voice-cleanup` |
| `podcast-voice` | `voice` | audio | audio | `podcast`, `delivery` | `voice-cleanup` |
| `trim-silence` | `desilence` | audio | audio | `podcast`, `delivery` | `voice-cleanup` |
| `mono-audio` | `mono` | audio | audio | `podcast` | `voice-cleanup` |
| `crossfade-audio` | `crossfade` | audio | audio | `podcast`, `creator` | `audio-processing` |
| `add-music` | `music` | media | video | `podcast` | `audio-processing` |
| `duck-music` | `duck` | media | video | `podcast` | `audio-processing` |
| `tag-audio` | `tag` | audio | audio | `podcast`, `archive` | `audio-files` |

## Composition (8)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `watermark` | `mark` | media | video | `creator`, `delivery`, `silent-input` | `composition` |
| `join-matching` | `join` | media | media | `creator`, `archive` | `composition` |
| `grid` | none | media | video | `creator`, `silent-input` | `composition` |
| `fit-canvas` | `fit` | media | video | `creator`, `delivery`, `silent-input` | `composition` |
| `picture-in-picture` | `pip` | media | video | `creator`, `silent-input` | `composition` |
| `blurred-background` | `blur-bg` | media | video | `creator`, `delivery`, `silent-input` | `composition` |
| `still-image-video` | `still-video` | image and audio | video | `creator` | `web-video` |
| `podcast-audiogram` | `audiogram` | image and audio | video | `creator` | `audiogram` |

## Effects (5)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `fade-edges` | `fade` | media | video | `creator`, `silent-input` | `video-effects` |
| `adjust-colors` | `color` | media | video | `creator` | `creator-video` |
| `sharpen` | none | media | video | `creator` | `creator-video` |
| `blur-region` | `privacy-blur` | media | video | `creator`, `privacy`, `silent-input` | `creator-video` |
| `reverse-clip` | `reverse` | media | video | `creator`, `silent-input` | `reverse` |

## Images (6)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `thumbnail` | `thumb` | media | image | `creator`, `archive`, `silent-input` | `analysis-images` |
| `make-gif` | `gif` | media | image | `creator`, `delivery`, `silent-input` | `animated-gif` |
| `waveform-image` | `waveform` | audio | image | `creator` | `analysis-images` |
| `spectrum-image` | `spectrum` | audio | image | `creator` | `analysis-images` |
| `contact-sheet` | `sheet` | media | image | `creator`, `archive`, `silent-input` | `analysis-images` |
| `image-sequence-video` | `timelapse`, `image-sequence` | image sequence | video | `creator`, `silent-input` | `web-video` |

## Subtitles (3)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `extract-subtitles` | `subtitles` | media | subtitle | `accessibility`, `archive`, `copy` | `subtitles` |
| `add-subtitles` | `captions` | media | video | `accessibility`, `delivery` | `subtitles` |
| `remove-subtitles` | `strip-subtitles` | media | video | `accessibility`, `copy`, `privacy` | `web-video` |

## Metadata (1)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `strip-metadata` | `clean-metadata` | media | media | `archive`, `copy`, `privacy` | none |

## Inspect (4)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `probe` | none | media | report | `inspect`, `archive` | none |
| `compare` | none | two media files | report | `inspect` | none |
| `doctor` | none | none | report | `inspect` | none |
| `setup` | `install-tools` | none | report | `inspect` | none |

## Help (4)

| Command | Aliases | Input | Output | Tags | Doctor group |
|---|---|---|---|---|---|
| `errors` | none | none | text | `discover` | none |
| `explain-error` | none | error id | text | `discover` | none |
| `examples` | none | none | text | `discover` | none |
| `commands` | none | none | text | `discover` | none |
