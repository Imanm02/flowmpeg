import shutil
from pathlib import Path

import pytest

from flowmpeg import GraphError, input, output
from flowmpeg.recipes.audio import (
    delay_audio,
    duck_audio,
    fade_audio,
    mix_audio,
    trim_audio,
    volume,
)


def test_audio_mix_compiles_gains_and_weights() -> None:
    voice = input("voice.wav").audio()
    music = volume(input("music.wav").audio(), db=-12)

    mixed = mix_audio(
        voice,
        music,
        weights=(1, 0.25),
        duration="first",
        dropout_transition=0,
    )
    graph = output(mixed, to="mix.wav").filter_graph()

    assert graph == (
        "[1:a:0]volume=volume=-12dB[a0];"
        "[0:a:0][a0]amix=inputs=2:duration=first:"
        "dropout_transition=0:normalize=1:weights=1 0.25[a1]"
    )


def test_audio_timing_recipes_reset_timestamps() -> None:
    source = input("voice.wav").audio()

    edited = fade_audio(
        delay_audio(trim_audio(source, start=1, end=5), 0.5),
        fade_type="out",
        start=3,
        duration=1,
    )
    graph = output(edited, to="edit.wav").filter_graph()

    assert graph is not None
    assert "atrim=start=1:end=5" in graph
    assert "asetpts=PTS-STARTPTS" in graph
    assert "adelay=delays=500:all=1" in graph
    assert "afade=t=out:st=3:d=1" in graph


def test_ducking_builds_compression_and_mix_nodes() -> None:
    music = input("music.wav").audio()
    voice = input("voice.wav").audio()

    result = duck_audio(music, voice)
    graph = output(result, to="ducked.wav").filter_graph()

    assert graph is not None
    assert "sidechaincompress=" in graph
    assert "amix=" in graph


def test_mix_rejects_mismatched_weights() -> None:
    first = input("first.wav").audio()
    second = input("second.wav").audio()

    with pytest.raises(GraphError, match="weights"):
        mix_audio(first, second, weights=(1,))


@pytest.mark.integration
def test_audio_mix_runs_with_generated_tones(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")

    first = input(
        "sine=frequency=440:duration=0.2",
        "-f",
        "lavfi",
    ).audio()
    second = input(
        "sine=frequency=880:duration=0.2",
        "-f",
        "lavfi",
    ).audio()
    target = tmp_path / "mix.wav"
    plan = output(
        mix_audio(first, second),
        to=target,
        args=("-c:a", "pcm_s16le"),
    )

    result = plan.run(ffmpeg=ffmpeg, expected_duration=0.2, timeout=10)

    assert result.returncode == 0
    assert target.stat().st_size > 44


@pytest.mark.integration
def test_audio_ducking_runs_with_generated_tones(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")

    music = input(
        "sine=frequency=220:duration=0.2",
        "-f",
        "lavfi",
    ).audio()
    voice = input(
        "sine=frequency=660:duration=0.2",
        "-f",
        "lavfi",
    ).audio()
    target = tmp_path / "ducked.wav"
    plan = output(
        duck_audio(music, voice),
        to=target,
        args=("-c:a", "pcm_s16le"),
    )

    result = plan.run(ffmpeg=ffmpeg, expected_duration=0.2, timeout=10)

    assert result.returncode == 0
    assert target.stat().st_size > 44
