"""Intent-level media composition recipes."""

from flowmpeg.recipes.audio import (
    delay_audio,
    duck_audio,
    fade_audio,
    mix_audio,
    trim_audio,
    volume,
)
from flowmpeg.recipes.video import (
    named_overlay_position,
    overlay_video,
    scale,
    stack_video,
    trim_video,
)

__all__ = [
    "delay_audio",
    "duck_audio",
    "fade_audio",
    "mix_audio",
    "named_overlay_position",
    "overlay_video",
    "scale",
    "stack_video",
    "trim_audio",
    "trim_video",
    "volume",
]
