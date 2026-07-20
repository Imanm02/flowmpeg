"""Metadata for Flowmpeg command discovery."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Discovery data for one command and its shortcuts."""

    name: str
    category: str
    summary: str
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    input_kind: str = "media"
    output_kind: str = "media"
    capability_group: str | None = None
    requirements: tuple[str, ...] = ()


_BASE_COMMAND_CATALOG = (
    CommandSpec(
        "transcode",
        "video",
        "Convert a video to web MP4",
        ("convert",),
        capability_group="web-video",
    ),
    CommandSpec(
        "trim",
        "video",
        "Cut an exact time range",
        ("cut",),
        capability_group="web-video",
    ),
    CommandSpec(
        "resize",
        "video",
        "Resize while keeping aspect ratio",
        ("scale",),
        capability_group="web-video",
    ),
    CommandSpec(
        "remove-audio",
        "video",
        "Copy video without audio",
        ("mute", "strip-audio"),
        output_kind="video",
    ),
    CommandSpec(
        "compress-video",
        "video",
        "Encode an H.264 delivery MP4",
        ("compress", "smaller"),
        capability_group="web-video",
    ),
    CommandSpec(
        "reframe",
        "video",
        "Fill a fixed video frame",
        ("fill-frame",),
        capability_group="composition",
    ),
    CommandSpec(
        "social-video",
        "video",
        "Prepare a social frame size",
        ("social",),
        capability_group="composition",
    ),
    CommandSpec(
        "set-frame-rate",
        "video",
        "Set a constant frame rate",
        ("fps",),
        capability_group="creator-video",
    ),
    CommandSpec(
        "deinterlace",
        "video",
        "Remove interlacing lines",
        capability_group="creator-video",
    ),
    CommandSpec(
        "flip-video",
        "video",
        "Flip video on one axis",
        ("flip", "mirror"),
        capability_group="video-effects",
    ),
    CommandSpec(
        "rotate", "video", "Rotate by a quarter turn", capability_group="video-effects"
    ),
    CommandSpec(
        "crop", "video", "Crop a fixed rectangle", capability_group="composition"
    ),
    CommandSpec(
        "change-speed",
        "video",
        "Change video and audio speed",
        ("speed",),
        capability_group="audio-processing",
    ),
    CommandSpec(
        "freeze-end",
        "video",
        "Hold the last video frame",
        ("freeze",),
        capability_group="creator-video",
    ),
    CommandSpec(
        "mute-section",
        "video",
        "Mute one time range",
        ("silence-section",),
        capability_group="audio-processing",
    ),
    CommandSpec(
        "boomerang",
        "video",
        "Play a clip forward then backward",
        ("bounce",),
        capability_group="reverse",
    ),
    CommandSpec(
        "replace-audio",
        "audio",
        "Replace a video's audio track",
        ("swap-audio",),
        output_kind="video",
        capability_group="web-video",
    ),
    CommandSpec(
        "extract-audio",
        "audio",
        "Save one audio track",
        ("audio",),
        output_kind="audio",
        capability_group="audio-files",
    ),
    CommandSpec(
        "mix-audio",
        "audio",
        "Mix audio files",
        ("mix", "mix-audio-files"),
        input_kind="audio",
        output_kind="audio",
        capability_group="audio-processing",
    ),
    CommandSpec(
        "normalize-loudness",
        "audio",
        "Normalize loudness in one pass",
        ("normalize",),
        input_kind="audio",
        output_kind="audio",
        capability_group="audio-processing",
    ),
    CommandSpec(
        "denoise-audio",
        "audio",
        "Reduce steady audio noise",
        ("denoise",),
        input_kind="audio",
        output_kind="audio",
        capability_group="voice-cleanup",
    ),
    CommandSpec(
        "compress-audio",
        "audio",
        "Reduce audio level range",
        ("dynamics",),
        input_kind="audio",
        output_kind="audio",
        capability_group="voice-cleanup",
    ),
    CommandSpec(
        "podcast-voice",
        "audio",
        "Prepare spoken audio",
        ("voice",),
        input_kind="audio",
        output_kind="audio",
        capability_group="voice-cleanup",
    ),
    CommandSpec(
        "trim-silence",
        "audio",
        "Remove quiet audio edges",
        ("desilence",),
        input_kind="audio",
        output_kind="audio",
        capability_group="voice-cleanup",
    ),
    CommandSpec(
        "mono-audio",
        "audio",
        "Downmix audio to mono",
        ("mono",),
        input_kind="audio",
        output_kind="audio",
        capability_group="voice-cleanup",
    ),
    CommandSpec(
        "crossfade-audio",
        "audio",
        "Crossfade two audio files",
        ("crossfade",),
        input_kind="audio",
        output_kind="audio",
        capability_group="audio-processing",
    ),
    CommandSpec(
        "add-music",
        "audio",
        "Add a music bed to video",
        ("music",),
        output_kind="video",
        capability_group="audio-processing",
    ),
    CommandSpec(
        "duck-music",
        "audio",
        "Lower music under speech",
        ("duck",),
        output_kind="video",
        capability_group="audio-processing",
    ),
    CommandSpec(
        "tag-audio",
        "audio",
        "Write audio metadata",
        ("tag",),
        input_kind="audio",
        output_kind="audio",
        capability_group="audio-files",
    ),
    CommandSpec(
        "watermark",
        "composition",
        "Place an image over video",
        ("mark",),
        output_kind="video",
        capability_group="composition",
    ),
    CommandSpec(
        "join-matching",
        "composition",
        "Join matching media files",
        ("join",),
        output_kind="media",
        capability_group="composition",
    ),
    CommandSpec(
        "grid",
        "composition",
        "Arrange videos in a grid",
        output_kind="video",
        capability_group="composition",
    ),
    CommandSpec(
        "fit-canvas",
        "composition",
        "Fit video inside a fixed canvas",
        ("fit",),
        output_kind="video",
        capability_group="composition",
    ),
    CommandSpec(
        "picture-in-picture",
        "composition",
        "Place one video over another",
        ("pip",),
        output_kind="video",
        capability_group="composition",
    ),
    CommandSpec(
        "blurred-background",
        "composition",
        "Fill a frame with a blurred copy",
        ("blur-bg",),
        output_kind="video",
        capability_group="composition",
    ),
    CommandSpec(
        "still-image-video",
        "composition",
        "Pair a still image with audio",
        ("still-video",),
        input_kind="image and audio",
        output_kind="video",
        capability_group="web-video",
    ),
    CommandSpec(
        "podcast-audiogram",
        "composition",
        "Build an audiogram from audio and art",
        ("audiogram",),
        input_kind="image and audio",
        output_kind="video",
        capability_group="audiogram",
    ),
    CommandSpec(
        "fade-edges",
        "effects",
        "Fade video and audio edges",
        ("fade",),
        output_kind="video",
        capability_group="video-effects",
    ),
    CommandSpec(
        "adjust-colors",
        "effects",
        "Adjust basic video color values",
        ("color",),
        output_kind="video",
        capability_group="creator-video",
    ),
    CommandSpec(
        "sharpen",
        "effects",
        "Sharpen video detail",
        output_kind="video",
        capability_group="creator-video",
    ),
    CommandSpec(
        "blur-region",
        "effects",
        "Blur one fixed video region",
        ("privacy-blur",),
        output_kind="video",
        capability_group="creator-video",
    ),
    CommandSpec(
        "reverse-clip",
        "effects",
        "Reverse a bounded clip",
        ("reverse",),
        output_kind="video",
        capability_group="reverse",
    ),
    CommandSpec(
        "thumbnail",
        "images",
        "Save one video frame",
        ("thumb",),
        output_kind="image",
        capability_group="analysis-images",
    ),
    CommandSpec(
        "make-gif",
        "images",
        "Create a palette based GIF",
        ("gif",),
        output_kind="image",
        capability_group="animated-gif",
    ),
    CommandSpec(
        "waveform-image",
        "images",
        "Draw an audio waveform",
        ("waveform",),
        input_kind="audio",
        output_kind="image",
        capability_group="analysis-images",
    ),
    CommandSpec(
        "spectrum-image",
        "images",
        "Draw an audio spectrum",
        ("spectrum",),
        input_kind="audio",
        output_kind="image",
        capability_group="analysis-images",
    ),
    CommandSpec(
        "contact-sheet",
        "images",
        "Build a video contact sheet",
        ("sheet",),
        output_kind="image",
        capability_group="analysis-images",
    ),
    CommandSpec(
        "image-sequence-video",
        "images",
        "Encode numbered images as video",
        ("timelapse", "image-sequence"),
        input_kind="image sequence",
        output_kind="video",
        capability_group="web-video",
    ),
    CommandSpec(
        "extract-subtitles",
        "subtitles",
        "Save one subtitle track",
        ("subtitles",),
        output_kind="subtitle",
        capability_group="subtitles",
    ),
    CommandSpec(
        "add-subtitles",
        "subtitles",
        "Add a selectable subtitle track",
        ("captions",),
        output_kind="video",
        capability_group="subtitles",
    ),
    CommandSpec(
        "remove-subtitles",
        "subtitles",
        "Create an MP4 without subtitles",
        ("strip-subtitles",),
        output_kind="video",
        capability_group="web-video",
    ),
    CommandSpec(
        "strip-metadata",
        "metadata",
        "Copy media without metadata",
        ("clean-metadata",),
        output_kind="media",
    ),
    CommandSpec(
        "probe",
        "inspect",
        "Inspect streams and container data",
        input_kind="media",
        output_kind="report",
    ),
    CommandSpec(
        "compare",
        "inspect",
        "Compare media values before and after a job",
        input_kind="two media files",
        output_kind="report",
    ),
    CommandSpec(
        "doctor",
        "inspect",
        "Check tools and media capabilities",
        input_kind="none",
        output_kind="report",
    ),
    CommandSpec(
        "setup",
        "inspect",
        "Check or install media tools",
        ("install-tools",),
        input_kind="none",
        output_kind="report",
    ),
    CommandSpec(
        "errors",
        "help",
        "List stable error identifiers",
        input_kind="none",
        output_kind="text",
    ),
    CommandSpec(
        "explain-error",
        "help",
        "Explain one error identifier",
        input_kind="error id",
        output_kind="text",
    ),
    CommandSpec(
        "examples",
        "help",
        "Print ready-to-edit examples",
        input_kind="none",
        output_kind="text",
    ),
    CommandSpec(
        "commands",
        "help",
        "List commands by task category",
        input_kind="none",
        output_kind="text",
    ),
)

TAGS = (
    "accessibility",
    "archive",
    "copy",
    "creator",
    "delivery",
    "discover",
    "inspect",
    "podcast",
    "privacy",
    "silent-input",
)

_CATEGORY_TAGS = {
    "video": ("creator",),
    "audio": ("podcast",),
    "composition": ("creator",),
    "effects": ("creator",),
    "images": ("creator",),
    "subtitles": ("accessibility",),
    "metadata": ("archive",),
    "inspect": ("inspect",),
    "help": ("discover",),
}

_COMMAND_TAGS = {
    "transcode": ("delivery", "silent-input"),
    "trim": ("delivery", "silent-input"),
    "resize": ("delivery", "silent-input"),
    "remove-audio": ("copy", "privacy", "silent-input"),
    "compress-video": ("delivery", "silent-input"),
    "reframe": ("delivery", "silent-input"),
    "social-video": ("delivery", "silent-input"),
    "set-frame-rate": ("archive", "silent-input"),
    "deinterlace": ("archive", "silent-input"),
    "flip-video": ("silent-input",),
    "rotate": ("silent-input",),
    "crop": ("silent-input",),
    "change-speed": ("silent-input",),
    "freeze-end": ("silent-input",),
    "boomerang": ("silent-input",),
    "extract-audio": ("copy",),
    "mix-audio": ("creator",),
    "normalize-loudness": ("delivery",),
    "podcast-voice": ("delivery",),
    "trim-silence": ("delivery",),
    "crossfade-audio": ("creator",),
    "tag-audio": ("archive",),
    "watermark": ("delivery", "silent-input"),
    "join-matching": ("archive",),
    "grid": ("silent-input",),
    "fit-canvas": ("delivery", "silent-input"),
    "picture-in-picture": ("silent-input",),
    "blurred-background": ("delivery", "silent-input"),
    "fade-edges": ("silent-input",),
    "blur-region": ("privacy", "silent-input"),
    "reverse-clip": ("silent-input",),
    "thumbnail": ("archive", "silent-input"),
    "make-gif": ("delivery", "silent-input"),
    "contact-sheet": ("archive", "silent-input"),
    "image-sequence-video": ("silent-input",),
    "extract-subtitles": ("archive", "copy"),
    "add-subtitles": ("delivery",),
    "remove-subtitles": ("copy", "privacy"),
    "strip-metadata": ("copy", "privacy"),
    "probe": ("archive",),
}

_MP4 = ("encoder:aac", "encoder:libx264", "muxer:mp4")
_WAV = ("encoder:pcm_s16le", "muxer:wav")


def _requirements(*names: str) -> tuple[str, ...]:
    return tuple(sorted(names))


_COMMAND_REQUIREMENTS = {
    "transcode": _MP4,
    "trim": _requirements(
        *_MP4,
        "filter:asetpts",
        "filter:atrim",
        "filter:setpts",
        "filter:trim",
    ),
    "resize": _requirements(*_MP4, "filter:scale"),
    "remove-audio": ("muxer:mp4",),
    "compress-video": _requirements(*_MP4, "filter:scale"),
    "reframe": _requirements(*_MP4, "filter:crop", "filter:scale", "filter:setsar"),
    "social-video": _requirements(
        *_MP4,
        "filter:crop",
        "filter:gblur",
        "filter:overlay",
        "filter:scale",
        "filter:split",
    ),
    "set-frame-rate": _requirements(*_MP4, "filter:fps"),
    "deinterlace": _requirements(*_MP4, "filter:bwdif"),
    "flip-video": _requirements(*_MP4, "filter:hflip"),
    "rotate": _requirements(*_MP4, "filter:transpose"),
    "crop": _requirements(*_MP4, "filter:crop"),
    "change-speed": _requirements(
        *_MP4, "filter:asetpts", "filter:atempo", "filter:setpts"
    ),
    "freeze-end": _requirements(*_MP4, "filter:apad", "filter:tpad"),
    "mute-section": _requirements(*_MP4, "filter:volume"),
    "boomerang": _requirements(
        *_MP4,
        "filter:areverse",
        "filter:asetpts",
        "filter:asplit",
        "filter:atrim",
        "filter:concat",
        "filter:reverse",
        "filter:setpts",
        "filter:split",
        "filter:trim",
    ),
    "replace-audio": _requirements("encoder:aac", "filter:apad", "muxer:mp4"),
    "extract-audio": ("encoder:libmp3lame", "muxer:mp3"),
    "mix-audio": _requirements(*_WAV, "filter:amix"),
    "normalize-loudness": _requirements(*_WAV, "filter:aresample", "filter:loudnorm"),
    "denoise-audio": _requirements(*_WAV, "filter:afftdn"),
    "compress-audio": _requirements(*_WAV, "filter:acompressor"),
    "podcast-voice": _requirements(
        *_WAV,
        "filter:acompressor",
        "filter:afftdn",
        "filter:aresample",
        "filter:highpass",
        "filter:loudnorm",
        "filter:lowpass",
    ),
    "trim-silence": _requirements(
        *_WAV,
        "filter:areverse",
        "filter:asetpts",
        "filter:atrim",
        "filter:silenceremove",
    ),
    "mono-audio": _requirements(*_WAV, "filter:aformat"),
    "crossfade-audio": _requirements(*_WAV, "filter:acrossfade"),
    "add-music": _requirements(*_MP4, "filter:amix", "filter:volume"),
    "duck-music": _requirements(
        *_MP4,
        "filter:amix",
        "filter:asplit",
        "filter:sidechaincompress",
        "filter:volume",
    ),
    "tag-audio": ("muxer:ipod",),
    "watermark": _requirements(*_MP4, "filter:overlay"),
    "join-matching": _requirements(
        *_MP4, "filter:asetpts", "filter:concat", "filter:setpts"
    ),
    "grid": _requirements(
        "encoder:libx264", "filter:scale", "filter:xstack", "muxer:mp4"
    ),
    "fit-canvas": _requirements(*_MP4, "filter:pad", "filter:scale", "filter:setsar"),
    "picture-in-picture": _requirements(
        *_MP4, "filter:overlay", "filter:scale", "filter:setpts"
    ),
    "blurred-background": _requirements(
        *_MP4,
        "filter:crop",
        "filter:gblur",
        "filter:overlay",
        "filter:scale",
        "filter:split",
    ),
    "still-image-video": _requirements(
        *_MP4, "filter:pad", "filter:scale", "filter:setsar"
    ),
    "podcast-audiogram": _requirements(
        *_MP4,
        "filter:asplit",
        "filter:colorkey",
        "filter:overlay",
        "filter:pad",
        "filter:scale",
        "filter:setsar",
        "filter:showwaves",
    ),
    "fade-edges": _requirements(
        *_MP4,
        "filter:afade",
        "filter:asetpts",
        "filter:atrim",
        "filter:fade",
        "filter:setpts",
        "filter:trim",
    ),
    "adjust-colors": _requirements(*_MP4, "filter:eq"),
    "sharpen": _requirements(*_MP4, "filter:unsharp"),
    "blur-region": _requirements(
        *_MP4,
        "filter:boxblur",
        "filter:crop",
        "filter:overlay",
        "filter:split",
    ),
    "reverse-clip": _requirements(
        *_MP4,
        "filter:areverse",
        "filter:asetpts",
        "filter:atrim",
        "filter:reverse",
        "filter:setpts",
        "filter:trim",
    ),
    "thumbnail": ("encoder:mjpeg", "muxer:image2"),
    "make-gif": _requirements(
        "encoder:gif",
        "filter:fps",
        "filter:palettegen",
        "filter:paletteuse",
        "filter:scale",
        "filter:setpts",
        "filter:split",
        "filter:trim",
        "muxer:gif",
    ),
    "waveform-image": _requirements(
        "encoder:png", "filter:showwavespic", "muxer:image2"
    ),
    "spectrum-image": _requirements(
        "encoder:png", "filter:scale", "filter:showspectrumpic", "muxer:image2"
    ),
    "contact-sheet": _requirements(
        "encoder:mjpeg",
        "filter:fps",
        "filter:pad",
        "filter:scale",
        "filter:setsar",
        "filter:tile",
        "muxer:image2",
    ),
    "image-sequence-video": _requirements(
        "encoder:libx264",
        "filter:pad",
        "filter:scale",
        "filter:setsar",
        "muxer:mp4",
    ),
    "extract-subtitles": ("encoder:srt", "muxer:srt"),
    "add-subtitles": _requirements(*_MP4, "encoder:mov_text"),
    "remove-subtitles": _MP4,
    "strip-metadata": ("muxer:matroska",),
}

COMMAND_CATALOG = tuple(
    replace(
        spec,
        tags=tuple(
            dict.fromkeys(
                (*_CATEGORY_TAGS[spec.category], *_COMMAND_TAGS.get(spec.name, ()))
            )
        ),
        requirements=_COMMAND_REQUIREMENTS.get(spec.name, ()),
    )
    for spec in _BASE_COMMAND_CATALOG
)

CATEGORIES = tuple(dict.fromkeys(spec.category for spec in COMMAND_CATALOG))


def command_spec(name: str) -> CommandSpec | None:
    """Find a command by canonical name or alias."""

    lowered = name.lower()
    for spec in COMMAND_CATALOG:
        if lowered == spec.name or lowered in spec.aliases:
            return spec
    return None


__all__ = ["CATEGORIES", "COMMAND_CATALOG", "TAGS", "CommandSpec", "command_spec"]
