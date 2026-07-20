"""Intent-level media composition recipes."""

from flowmpeg.recipes.audio import (
    change_audio_speed,
    delay_audio,
    duck_audio,
    fade_audio,
    mix_audio,
    normalize_loudness,
    trim_audio,
    volume,
)
from flowmpeg.recipes.video import (
    change_video_speed,
    crop_video,
    named_overlay_position,
    overlay_video,
    rotate_video,
    scale,
    stack_video,
    trim_video,
)

__all__ = [
    "change_audio_speed",
    "change_video_speed",
    "crop_video",
    "delay_audio",
    "duck_audio",
    "fade_audio",
    "mix_audio",
    "named_overlay_position",
    "normalize_loudness",
    "overlay_video",
    "rotate_video",
    "scale",
    "stack_video",
    "trim_audio",
    "trim_video",
    "volume",
]
