"""Metadata for Flowmpeg command discovery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Discovery data for one command and its shortcuts."""

    name: str
    category: str
    summary: str
    aliases: tuple[str, ...] = ()
    input_kind: str = "media"
    output_kind: str = "media"
    capability_group: str | None = None


COMMAND_CATALOG = (
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
        "Encode a smaller H.264 MP4",
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
        output_kind="audio",
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
        "Copy media without subtitles",
        ("strip-subtitles",),
        output_kind="media",
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

CATEGORIES = tuple(dict.fromkeys(spec.category for spec in COMMAND_CATALOG))


def command_spec(name: str) -> CommandSpec | None:
    """Find a command by canonical name or alias."""

    lowered = name.lower()
    for spec in COMMAND_CATALOG:
        if lowered == spec.name or lowered in spec.aliases:
            return spec
    return None


__all__ = ["CATEGORIES", "COMMAND_CATALOG", "CommandSpec", "command_spec"]
