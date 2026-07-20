"""Audio filtering and mixing recipes."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

from flowmpeg.errors import GraphError
from flowmpeg.model import FilterValue, StreamKind, expr
from flowmpeg.streams import AudioStream, apply_filter

MixDuration = Literal["first", "longest", "shortest"]
FadeType = Literal["in", "out"]


def volume(
    stream: AudioStream,
    *,
    factor: float | None = None,
    db: float | None = None,
) -> AudioStream:
    """Change audio volume by a linear factor or decibel amount."""

    if (factor is None) == (db is None):
        raise GraphError("Set exactly one of factor or db")
    if factor is not None:
        _finite("factor", factor)
        if factor < 0:
            raise GraphError("Volume factors cannot be negative")
        value: FilterValue = factor
    else:
        assert db is not None
        _finite("db", db)
        value = f"{db:g}dB"
    return stream.filter("volume", volume=value)


def delay_audio(stream: AudioStream, seconds: float) -> AudioStream:
    """Delay every channel by the given number of seconds."""

    _nonnegative("seconds", seconds)
    milliseconds = round(seconds * 1_000)
    return stream.filter("adelay", delays=milliseconds, all=True)


def fade_audio(
    stream: AudioStream,
    *,
    fade_type: FadeType,
    start: float = 0,
    duration: float = 1,
) -> AudioStream:
    """Apply an audio fade at a specific time."""

    if fade_type not in {"in", "out"}:
        raise GraphError("Fade type must be 'in' or 'out'")
    _nonnegative("start", start)
    _positive("duration", duration)
    return stream.filter("afade", t=fade_type, st=start, d=duration)


def trim_audio(
    stream: AudioStream,
    *,
    start: float | None = None,
    end: float | None = None,
) -> AudioStream:
    """Trim audio and reset its timestamps to zero."""

    if start is None and end is None:
        raise GraphError("Audio trim requires start or end")
    if start is not None:
        _nonnegative("start", start)
    if end is not None:
        _positive("end", end)
    if start is not None and end is not None and end <= start:
        raise GraphError("Audio trim end must be greater than start")

    options: dict[str, FilterValue] = {}
    if start is not None:
        options["start"] = start
    if end is not None:
        options["end"] = end
    trimmed = stream.filter("atrim", **options)
    return trimmed.filter("asetpts", expr("PTS-STARTPTS"))


def mix_audio(
    *streams: AudioStream,
    weights: Sequence[float] | None = None,
    duration: MixDuration = "longest",
    dropout_transition: float = 2,
    normalize: bool = True,
) -> AudioStream:
    """Mix audio streams into one output with explicit duration behavior."""

    if len(streams) < 2:
        raise GraphError("Audio mixing requires at least two streams")
    if duration not in {"first", "longest", "shortest"}:
        raise GraphError("Invalid audio mix duration")
    _boolean("normalize", normalize)
    _nonnegative("dropout_transition", dropout_transition)

    options: dict[str, FilterValue] = {
        "inputs": len(streams),
        "duration": duration,
        "dropout_transition": dropout_transition,
        "normalize": normalize,
    }
    if weights is not None:
        if len(weights) != len(streams):
            raise GraphError("Audio mix weights must match the stream count")
        for weight in weights:
            _finite("weight", weight)
        options["weights"] = " ".join(f"{weight:g}" for weight in weights)

    (result,) = apply_filter(
        streams,
        "amix",
        output_kinds=(StreamKind.AUDIO,),
        options=options,
    )
    assert isinstance(result, AudioStream)
    return result


def duck_audio(
    program: AudioStream,
    sidechain: AudioStream,
    *,
    threshold: float = 0.125,
    ratio: float = 8,
    attack: float = 20,
    release: float = 250,
    normalize: bool = True,
) -> AudioStream:
    """Lower program audio under a sidechain, then mix both streams."""

    _boolean("normalize", normalize)
    _range("threshold", threshold, 0.000_975_63, 1)
    _range("ratio", ratio, 1, 20)
    _range("attack", attack, 0.01, 2_000)
    _range("release", release, 0.01, 9_000)
    compression_sidechain, mix_sidechain = sidechain.split()
    (ducked,) = apply_filter(
        (program, compression_sidechain),
        "sidechaincompress",
        output_kinds=(StreamKind.AUDIO,),
        options={
            "threshold": threshold,
            "ratio": ratio,
            "attack": attack,
            "release": release,
        },
    )
    assert isinstance(ducked, AudioStream)
    return mix_audio(
        ducked,
        mix_sidechain,
        duration="first",
        dropout_transition=0,
        normalize=normalize,
    )


def change_audio_speed(stream: AudioStream, factor: float) -> AudioStream:
    """Change audio tempo using compatible atempo stages."""

    _positive("factor", factor)
    if factor == 1:
        return stream

    changed = stream
    for stage in _tempo_stages(factor):
        value: float | int = int(stage) if stage.is_integer() else stage
        changed = changed.filter("atempo", value)
    return changed.filter("asetpts", expr("PTS-STARTPTS"))


def normalize_loudness(
    stream: AudioStream,
    *,
    integrated: float = -16,
    loudness_range: float = 11,
    true_peak: float = -1.5,
    sample_rate: int = 48_000,
) -> AudioStream:
    """Apply one-pass EBU R128 loudness normalization."""

    _range("integrated", integrated, -70, -5)
    _range("loudness_range", loudness_range, 1, 50)
    _range("true_peak", true_peak, -9, 0)
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, int)
        or sample_rate <= 0
    ):
        raise GraphError("Sample rate must be a positive integer")

    normalized = stream.filter(
        "loudnorm",
        I=integrated,
        LRA=loudness_range,
        TP=true_peak,
    )
    return normalized.filter("aresample", sample_rate)


def _tempo_stages(factor: float) -> tuple[float, ...]:
    remaining = float(factor)
    stages: list[float] = []
    while remaining > 2:
        stages.append(2.0)
        remaining /= 2
    while remaining < 0.5:
        stages.append(0.5)
        remaining /= 0.5
    if remaining != 1:
        stages.append(remaining)
    return tuple(stages)


def _finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphError(f"{name} must be finite")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise GraphError(f"{name} must be finite")


def _positive(name: str, value: float) -> None:
    _finite(name, value)
    if value <= 0:
        raise GraphError(f"{name} must be positive")


def _nonnegative(name: str, value: float) -> None:
    _finite(name, value)
    if value < 0:
        raise GraphError(f"{name} cannot be negative")


def _range(name: str, value: float, minimum: float, maximum: float) -> None:
    _finite(name, value)
    if not minimum <= value <= maximum:
        raise GraphError(f"{name} must be between {minimum:g} and {maximum:g}")


def _boolean(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise GraphError(f"{name} must be a Boolean")
