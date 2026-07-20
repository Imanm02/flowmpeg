# Generated command reference

This file is generated from `COMMAND_CATALOG`. Run
`python scripts/command_reference.py --check` before a release.

Tags describe use cases. Capability groups provide broad doctor checks.
Exact needs are checked by `flowmpeg doctor --command NAME`.

## Video (20)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `transcode` | `convert` | media | media | `creator`, `delivery`, `silent-input` | `web-video` | `encoder:aac`, `encoder:libx264`, `muxer:mp4` |
| `transcode-webm` | `webm`, `vp9` | media | media | `creator`, `delivery`, `silent-input` | `webm-video` | `encoder:libopus`, `encoder:libvpx-vp9`, `muxer:webm` |
| `transcode-hevc` | `hevc`, `h265` | media | media | `creator`, `archive`, `delivery`, `silent-input` | `hevc-video` | `encoder:aac`, `encoder:libx265`, `muxer:mp4` |
| `transcode-av1` | `av1`, `svt-av1` | media | media | `creator`, `archive`, `delivery`, `silent-input` | `av1-video` | `encoder:libopus`, `encoder:libsvtav1`, `muxer:webm` |
| `trim` | `cut` | media | media | `creator`, `delivery`, `silent-input` | `web-video` | `encoder:aac`, `encoder:libx264`, `filter:asetpts`, `filter:atrim`, `filter:setpts`, `filter:trim`, `muxer:mp4` |
| `loop-video` | `loop`, `repeat-video` | media | media | `creator`, `silent-input` | `web-video` | `encoder:aac`, `encoder:libx264`, `filter:asetpts`, `filter:atrim`, `filter:setpts`, `filter:trim`, `muxer:mp4` |
| `resize` | `scale` | media | media | `creator`, `delivery`, `silent-input` | `web-video` | `encoder:aac`, `encoder:libx264`, `filter:scale`, `muxer:mp4` |
| `remove-audio` | `mute`, `strip-audio` | media | video | `creator`, `copy`, `privacy`, `silent-input` | none | `muxer:mp4` |
| `compress-video` | `compress`, `smaller` | media | media | `creator`, `delivery`, `silent-input` | `web-video` | `encoder:aac`, `encoder:libx264`, `filter:scale`, `muxer:mp4` |
| `reframe` | `fill-frame` | media | media | `creator`, `delivery`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:crop`, `filter:scale`, `filter:setsar`, `muxer:mp4` |
| `social-video` | `social` | media | media | `creator`, `delivery`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:crop`, `filter:gblur`, `filter:overlay`, `filter:scale`, `filter:split`, `muxer:mp4` |
| `set-frame-rate` | `fps` | media | media | `creator`, `archive`, `silent-input` | `creator-video` | `encoder:aac`, `encoder:libx264`, `filter:fps`, `muxer:mp4` |
| `deinterlace` | none | media | media | `creator`, `archive`, `silent-input` | `creator-video` | `encoder:aac`, `encoder:libx264`, `filter:bwdif`, `muxer:mp4` |
| `flip-video` | `flip`, `mirror` | media | media | `creator`, `silent-input` | `video-effects` | `encoder:aac`, `encoder:libx264`, `filter:hflip`, `muxer:mp4` |
| `rotate` | none | media | media | `creator`, `silent-input` | `video-effects` | `encoder:aac`, `encoder:libx264`, `filter:transpose`, `muxer:mp4` |
| `crop` | none | media | media | `creator`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:crop`, `muxer:mp4` |
| `change-speed` | `speed` | media | media | `creator`, `silent-input` | `audio-processing` | `encoder:aac`, `encoder:libx264`, `filter:asetpts`, `filter:atempo`, `filter:setpts`, `muxer:mp4` |
| `freeze-end` | `freeze` | media | media | `creator`, `silent-input` | `creator-video` | `encoder:aac`, `encoder:libx264`, `filter:apad`, `filter:tpad`, `muxer:mp4` |
| `mute-section` | `silence-section` | media | media | `creator` | `audio-processing` | `encoder:aac`, `encoder:libx264`, `filter:volume`, `muxer:mp4` |
| `boomerang` | `bounce` | media | media | `creator`, `silent-input` | `reverse` | `encoder:aac`, `encoder:libx264`, `filter:areverse`, `filter:asetpts`, `filter:asplit`, `filter:atrim`, `filter:concat`, `filter:reverse`, `filter:setpts`, `filter:split`, `filter:trim`, `muxer:mp4` |

## Audio (20)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `replace-audio` | `swap-audio` | media | video | `podcast` | `web-video` | `encoder:aac`, `filter:apad`, `muxer:mp4` |
| `extract-audio` | `audio` | media | audio | `podcast`, `copy` | `audio-files` | `encoder:libmp3lame`, `muxer:mp3` |
| `mix-audio` | `mix`, `mix-audio-files` | audio | audio | `podcast`, `creator` | `audio-processing` | `encoder:pcm_s16le`, `filter:amix`, `muxer:wav` |
| `normalize-loudness` | `normalize` | audio | audio | `podcast`, `delivery` | `audio-processing` | `encoder:pcm_s16le`, `filter:aresample`, `filter:loudnorm`, `muxer:wav` |
| `denoise-audio` | `denoise` | audio | audio | `podcast` | `voice-cleanup` | `encoder:pcm_s16le`, `filter:afftdn`, `muxer:wav` |
| `compress-audio` | `dynamics` | audio | audio | `podcast` | `voice-cleanup` | `encoder:pcm_s16le`, `filter:acompressor`, `muxer:wav` |
| `podcast-voice` | `voice` | audio | audio | `podcast`, `delivery` | `voice-cleanup` | `encoder:pcm_s16le`, `filter:acompressor`, `filter:afftdn`, `filter:aresample`, `filter:highpass`, `filter:loudnorm`, `filter:lowpass`, `muxer:wav` |
| `trim-silence` | `desilence` | audio | audio | `podcast`, `delivery` | `voice-cleanup` | `encoder:pcm_s16le`, `filter:areverse`, `filter:asetpts`, `filter:atrim`, `filter:silenceremove`, `muxer:wav` |
| `trim-audio` | `cut-audio`, `audio-clip` | audio | audio | `podcast` | `audio-processing` | `encoder:pcm_s16le`, `filter:asetpts`, `filter:atrim`, `muxer:wav` |
| `mono-audio` | `mono` | audio | audio | `podcast` | `voice-cleanup` | `encoder:pcm_s16le`, `filter:aformat`, `muxer:wav` |
| `resample-audio` | `resample`, `audio-standard` | audio | audio | `podcast` | `audio-processing` | `encoder:pcm_s16le`, `filter:aformat`, `filter:aresample`, `muxer:wav` |
| `volume-audio` | `gain`, `volume` | audio | audio | `podcast` | `audio-processing` | `encoder:pcm_s16le`, `filter:volume`, `muxer:wav` |
| `fade-audio` | `audio-fade` | audio | audio | `podcast` | `audio-processing` | `encoder:pcm_s16le`, `filter:afade`, `muxer:wav` |
| `delay-audio` | `audio-delay`, `sync-audio` | audio | audio | `podcast` | `audio-processing` | `encoder:pcm_s16le`, `filter:adelay`, `muxer:wav` |
| `speed-audio` | `audio-speed`, `tempo` | audio | audio | `podcast` | `audio-processing` | `encoder:pcm_s16le`, `filter:atempo`, `muxer:wav` |
| `crossfade-audio` | `crossfade` | audio | audio | `podcast`, `creator` | `audio-processing` | `encoder:pcm_s16le`, `filter:acrossfade`, `muxer:wav` |
| `join-audio` | `concat-audio`, `audio-join` | audio files | audio | `podcast`, `creator`, `delivery` | `audio-processing` | `encoder:pcm_s16le`, `filter:aformat`, `filter:aresample`, `filter:asetpts`, `filter:concat`, `muxer:wav` |
| `add-music` | `music` | media | video | `podcast` | `audio-processing` | `encoder:aac`, `encoder:libx264`, `filter:amix`, `filter:volume`, `muxer:mp4` |
| `duck-music` | `duck` | media | video | `podcast` | `audio-processing` | `encoder:aac`, `encoder:libx264`, `filter:amix`, `filter:asplit`, `filter:sidechaincompress`, `filter:volume`, `muxer:mp4` |
| `tag-audio` | `tag` | audio | audio | `podcast`, `archive` | `audio-files` | `muxer:ipod` |

## Composition (9)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `watermark` | `mark` | media | video | `creator`, `delivery`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:overlay`, `muxer:mp4` |
| `join-matching` | `join` | media | media | `creator`, `archive` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:asetpts`, `filter:concat`, `filter:setpts`, `muxer:mp4` |
| `join-normalized` | `join-any`, `normalize-join` | two or more media files | media | `creator`, `delivery`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:aformat`, `filter:aresample`, `filter:asetpts`, `filter:concat`, `filter:fps`, `filter:pad`, `filter:scale`, `filter:setpts`, `filter:setsar`, `muxer:mp4` |
| `grid` | none | media | video | `creator`, `silent-input` | `composition` | `encoder:libx264`, `filter:scale`, `filter:xstack`, `muxer:mp4` |
| `fit-canvas` | `fit` | media | video | `creator`, `delivery`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:pad`, `filter:scale`, `filter:setsar`, `muxer:mp4` |
| `picture-in-picture` | `pip` | media | video | `creator`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:overlay`, `filter:scale`, `filter:setpts`, `muxer:mp4` |
| `blurred-background` | `blur-bg` | media | video | `creator`, `delivery`, `silent-input` | `composition` | `encoder:aac`, `encoder:libx264`, `filter:crop`, `filter:gblur`, `filter:overlay`, `filter:scale`, `filter:split`, `muxer:mp4` |
| `still-image-video` | `still-video` | image and audio | video | `creator` | `web-video` | `encoder:aac`, `encoder:libx264`, `filter:pad`, `filter:scale`, `filter:setsar`, `muxer:mp4` |
| `podcast-audiogram` | `audiogram` | image and audio | video | `creator` | `audiogram` | `encoder:aac`, `encoder:libx264`, `filter:asplit`, `filter:colorkey`, `filter:overlay`, `filter:pad`, `filter:scale`, `filter:setsar`, `filter:showwaves`, `muxer:mp4` |

## Effects (5)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `fade-edges` | `fade` | media | video | `creator`, `silent-input` | `video-effects` | `encoder:aac`, `encoder:libx264`, `filter:afade`, `filter:asetpts`, `filter:atrim`, `filter:fade`, `filter:setpts`, `filter:trim`, `muxer:mp4` |
| `adjust-colors` | `color` | media | video | `creator` | `creator-video` | `encoder:aac`, `encoder:libx264`, `filter:eq`, `muxer:mp4` |
| `sharpen` | none | media | video | `creator` | `creator-video` | `encoder:aac`, `encoder:libx264`, `filter:unsharp`, `muxer:mp4` |
| `blur-region` | `privacy-blur` | media | video | `creator`, `privacy`, `silent-input` | `creator-video` | `encoder:aac`, `encoder:libx264`, `filter:boxblur`, `filter:crop`, `filter:overlay`, `filter:split`, `muxer:mp4` |
| `reverse-clip` | `reverse` | media | video | `creator`, `silent-input` | `reverse` | `encoder:aac`, `encoder:libx264`, `filter:areverse`, `filter:asetpts`, `filter:atrim`, `filter:reverse`, `filter:setpts`, `filter:trim`, `muxer:mp4` |

## Images (6)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `thumbnail` | `thumb` | media | image | `creator`, `archive`, `silent-input` | `analysis-images` | `encoder:mjpeg`, `muxer:image2` |
| `make-gif` | `gif` | media | image | `creator`, `delivery`, `silent-input` | `animated-gif` | `encoder:gif`, `filter:fps`, `filter:palettegen`, `filter:paletteuse`, `filter:scale`, `filter:setpts`, `filter:split`, `filter:trim`, `muxer:gif` |
| `waveform-image` | `waveform` | audio | image | `creator` | `analysis-images` | `encoder:png`, `filter:showwavespic`, `muxer:image2` |
| `spectrum-image` | `spectrum` | audio | image | `creator` | `analysis-images` | `encoder:png`, `filter:scale`, `filter:showspectrumpic`, `muxer:image2` |
| `contact-sheet` | `sheet` | media | image | `creator`, `archive`, `silent-input` | `analysis-images` | `encoder:mjpeg`, `filter:fps`, `filter:pad`, `filter:scale`, `filter:setsar`, `filter:tile`, `muxer:image2` |
| `image-sequence-video` | `timelapse`, `image-sequence` | image sequence | video | `creator`, `silent-input` | `web-video` | `encoder:libx264`, `filter:pad`, `filter:scale`, `filter:setsar`, `muxer:mp4` |

## Subtitles (4)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `extract-subtitles` | `subtitles` | media | subtitle | `accessibility`, `archive`, `copy` | `subtitles` | `encoder:srt`, `muxer:srt` |
| `add-subtitles` | `captions` | media | video | `accessibility`, `delivery` | `subtitles` | `encoder:aac`, `encoder:libx264`, `encoder:mov_text`, `muxer:mp4` |
| `burn-subtitles` | `burn-captions`, `hardcode-subtitles` | video and subtitle | video | `accessibility`, `delivery`, `silent-input` | `subtitles` | `encoder:aac`, `encoder:libx264`, `filter:subtitles`, `muxer:mp4` |
| `remove-subtitles` | `strip-subtitles` | media | video | `accessibility`, `copy`, `privacy` | `web-video` | `encoder:aac`, `encoder:libx264`, `muxer:mp4` |

## Metadata (3)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `strip-metadata` | `clean-metadata` | media | media | `archive`, `copy`, `privacy` | none | `muxer:matroska` |
| `remux` | `rewrap`, `copy-container` | media | media | `archive`, `copy`, `delivery` | none | `muxer:matroska` |
| `tag-media` | `label-media` | media | media | `archive`, `copy` | none | `muxer:mp4` |

## Inspect (6)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `probe` | none | media | report | `inspect`, `archive` | none | none |
| `audit-media` | `audit`, `check-media` | media | report | `inspect` | none | none |
| `compare` | none | two media files | report | `inspect` | none | none |
| `analyze-loudness` | `loudness`, `measure-loudness` | audio | report | `inspect`, `archive` | `audio-processing` | `filter:loudnorm` |
| `doctor` | none | none | report | `inspect` | none | none |
| `setup` | `install-tools` | none | report | `inspect` | none | none |

## Help (4)

| Command | Aliases | Input | Output | Tags | Doctor group | Exact needs |
|---|---|---|---|---|---|---|
| `errors` | none | none | text | `discover` | none | none |
| `explain-error` | none | error id | text | `discover` | none | none |
| `examples` | none | none | text | `discover` | none | none |
| `commands` | none | none | text | `discover` | none | none |
