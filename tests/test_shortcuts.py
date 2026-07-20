import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

import pytest

from flowmpeg import GraphError, probe, shortcuts
from flowmpeg.recipes.video import Rotation


def test_shortcuts_namespace_is_public() -> None:
    assert shortcuts.trim.__module__ == "flowmpeg.shortcuts"
    assert set(shortcuts.__all__) == {
        "AudioCodec",
        "AudioReplacementCodec",
        "NamedPosition",
        "Pathish",
        "ReplacementDuration",
        "SpectrumColor",
        "SpectrumMode",
        "VideoPreset",
        "WaveformScale",
        "add_music",
        "blurred_background",
        "change_speed",
        "contact_sheet",
        "crop",
        "duck_music",
        "extract_audio",
        "fade_edges",
        "fit_canvas",
        "grid",
        "join_matching",
        "make_gif",
        "mix_audio_files",
        "normalize_loudness",
        "picture_in_picture",
        "remove_audio",
        "replace_audio",
        "resize",
        "reverse_clip",
        "rotate",
        "spectrum_image",
        "still_image_video",
        "thumbnail",
        "transcode",
        "trim",
        "watermark",
        "waveform_image",
    }


def test_transcode_builds_web_output() -> None:
    plan = shortcuts.transcode("in.mov", "out.mp4")

    assert plan.raw_argv() == (
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-n",
        "-i",
        "in.mov",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "out.mp4",
    )


def test_transcode_can_select_video_only() -> None:
    plan = shortcuts.transcode("silent.mov", "silent.mp4", include_audio=False)

    assert "0:a:0" not in plan.raw_argv()
    assert "-c:a" not in plan.raw_argv()


def test_trim_accepts_duration() -> None:
    plan = shortcuts.trim("in.mp4", "clip.mp4", start=2, duration=3)

    assert plan.filter_graph() == (
        "[0:v:0]trim=start=2:end=5[v0];"
        "[v0]setpts=PTS-STARTPTS[v1];"
        "[0:a:0]atrim=start=2:end=5[a0];"
        "[a0]asetpts=PTS-STARTPTS[a1]"
    )


def test_resize_preserves_aspect_ratio() -> None:
    width_plan = shortcuts.resize("in.mp4", "wide.mp4", width=1280)
    height_plan = shortcuts.resize("in.mp4", "tall.mp4", height=720)

    assert width_plan.filter_graph() == "[0:v:0]scale=1280:-2[v0]"
    assert height_plan.filter_graph() == "[0:v:0]scale=-2:720[v0]"


def test_remove_audio_copies_only_video() -> None:
    plan = shortcuts.remove_audio("in.mp4", "silent.mp4")

    assert plan.raw_argv() == (
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-n",
        "-i",
        "in.mp4",
        "-map",
        "0:v:0",
        "-c:v",
        "copy",
        "silent.mp4",
    )


@pytest.mark.parametrize(
    ("destination", "codec", "expected"),
    [
        ("audio.mp3", "mp3", ("-c:a", "libmp3lame", "-b:a", "192k")),
        ("audio.m4a", "aac", ("-c:a", "aac", "-b:a", "192k")),
        ("audio.wav", "wav", ("-c:a", "pcm_s16le")),
        ("audio.flac", "flac", ("-c:a", "flac")),
        ("audio.mka", "copy", ("-c:a", "copy")),
    ],
)
def test_extract_audio_codec_settings(
    destination: str,
    codec: shortcuts.AudioCodec,
    expected: tuple[str, ...],
) -> None:
    plan = shortcuts.extract_audio("in.mp4", destination, codec=codec)

    argv = plan.raw_argv()
    start = argv.index("-c:a")
    assert argv[start : start + len(expected)] == expected
    assert argv[-1] == destination


def test_extract_audio_selects_requested_track() -> None:
    plan = shortcuts.extract_audio("in.mkv", "track.mp3", track=2)

    assert plan.raw_argv()[6:8] == ("-map", "0:a:2")


def test_replace_audio_pads_to_video_duration() -> None:
    plan = shortcuts.replace_audio("in.mp4", "voice.wav", "dubbed.mp4")

    assert plan.filter_graph() == "[1:a:0]apad[a0]"
    assert plan.raw_argv()[-10:] == (
        "-map",
        "[a0]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "dubbed.mp4",
    )


def test_replace_audio_can_copy_until_shortest() -> None:
    plan = shortcuts.replace_audio(
        "in.mp4",
        "voice.m4a",
        "dubbed.mp4",
        duration="shortest",
        audio_codec="copy",
    )

    assert plan.filter_graph() is None
    assert plan.raw_argv()[-6:] == (
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-shortest",
        "dubbed.mp4",
    )


def test_watermark_builds_static_overlay() -> None:
    plan = shortcuts.watermark(
        "in.mp4",
        "logo.png",
        "marked.mp4",
        opacity=0.8,
    )

    assert plan.filter_graph() == (
        "[1:v:0]format=pix_fmts=rgba[v0];"
        "[v0]colorchannelmixer=aa=0.8[v1];"
        "[0:v:0][v1]overlay=x=W-w-24:y=24:"
        "shortest=0:eof_action=repeat[v2]"
    )
    assert "-loop" not in plan.raw_argv()


def test_add_music_exposes_volume_and_looping() -> None:
    plan = shortcuts.add_music(
        "in.mp4",
        "music.mp3",
        "mixed.mp4",
        music_volume=0.25,
        loop_music=True,
    )

    assert plan.filter_graph() == (
        "[1:a:0]volume=volume=0.25[a0];"
        "[0:a:0][a0]amix=inputs=2:duration=first:"
        "dropout_transition=2:normalize=1[a1]"
    )
    argv = plan.raw_argv()
    assert argv[6:11] == ("-stream_loop", "-1", "-i", "music.mp3", "-filter_complex")


def test_add_music_can_supply_silent_video_audio() -> None:
    plan = shortcuts.add_music(
        "silent.mp4",
        "music.mp3",
        "scored.mp4",
        source_has_audio=False,
    )

    assert plan.filter_graph() == ("[1:a:0]volume=volume=0.15[a0];[a0]apad[a1]")
    assert "0:a:0" not in plan.raw_argv()
    assert plan.raw_argv()[-2:] == ("-shortest", "scored.mp4")


def test_join_matching_keeps_paired_streams() -> None:
    plan = shortcuts.join_matching(("one.mp4", "two.mp4"), "joined.mp4")

    assert plan.filter_graph() == (
        "[0:v:0]setpts=PTS-STARTPTS[v0];"
        "[0:a:0]asetpts=PTS-STARTPTS[a0];"
        "[1:v:0]setpts=PTS-STARTPTS[v1];"
        "[1:a:0]asetpts=PTS-STARTPTS[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v2][a2]"
    )


def test_mix_audio_files_applies_per_file_volumes() -> None:
    plan = shortcuts.mix_audio_files(
        ("one.wav", "two.wav"),
        "mix.wav",
        volumes=(1, 0.5),
    )

    assert plan.filter_graph() == (
        "[1:a:0]volume=volume=0.5[a0];"
        "[0:a:0][a0]amix=inputs=2:duration=longest:"
        "dropout_transition=2:normalize=1[a1]"
    )
    assert plan.raw_argv()[-3:] == ("-c:a", "pcm_s16le", "mix.wav")


def test_grid_scales_cells_and_stops_at_shortest() -> None:
    plan = shortcuts.grid(
        ("1.mp4", "2.mp4", "3.mp4", "4.mp4"),
        "grid.mp4",
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert graph.count("scale=640:360") == 4
    assert ("xstack=inputs=4:layout=0_0|w0_0|0_h0|w2_h0:fill=black:shortest=1") in graph
    assert "0:a:0" not in plan.raw_argv()


def test_thumbnail_uses_input_seek_and_one_frame() -> None:
    plan = shortcuts.thumbnail("in.mp4", "cover.jpg", at=5)

    assert plan.raw_argv() == (
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-n",
        "-ss",
        "5",
        "-i",
        "in.mp4",
        "-map",
        "0:v:0",
        "-frames:v",
        "1",
        "-q:v",
        "2",
        "cover.jpg",
    )


def test_png_thumbnail_does_not_use_jpeg_quality() -> None:
    plan = shortcuts.thumbnail("in.mp4", "cover.png", width=320)

    assert plan.filter_graph() == "[0:v:0]scale=320:-2[v0]"
    assert "-q:v" not in plan.raw_argv()


def test_make_gif_builds_palette_graph() -> None:
    plan = shortcuts.make_gif("in.mp4", "preview.gif")

    assert plan.filter_graph() == (
        "[0:v:0]trim=start=0:end=5[v0];"
        "[v0]setpts=PTS-STARTPTS[v1];"
        "[v1]fps=fps=12[v2];"
        "[v2]scale=480:-2:flags=lanczos[v3];"
        "[v3]split=outputs=2[v4][v5];"
        "[v4]palettegen=stats_mode=diff[v6];"
        "[v5][v6]paletteuse=dither=sierra2_4a[v7]"
    )
    assert plan.raw_argv()[-3:] == ("-loop", "0", "preview.gif")


def test_make_gif_resets_an_untrimmed_timeline() -> None:
    plan = shortcuts.make_gif(
        "in.mp4",
        "complete.gif",
        duration=None,
        width=None,
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert graph.startswith("[0:v:0]setpts=PTS-STARTPTS[v0];[v0]fps=fps=12")


@pytest.mark.parametrize(
    ("degrees", "expected"),
    [
        (90, "[0:v:0]transpose=dir=clock[v0]"),
        (180, "[0:v:0]hflip[v0];[v0]vflip[v1]"),
        (270, "[0:v:0]transpose=dir=cclock[v0]"),
    ],
)
def test_rotate_supports_quarter_turns(
    degrees: Rotation,
    expected: str,
) -> None:
    plan = shortcuts.rotate("in.mp4", "rotated.mp4", degrees=degrees)

    assert plan.filter_graph() == expected


def test_crop_uses_centered_defaults() -> None:
    centered = shortcuts.crop("in.mp4", "crop.mp4", width=640, height=360)
    positioned = shortcuts.crop(
        "in.mp4",
        "positioned.mp4",
        width=640,
        height=360,
        x=10,
        y=20,
    )

    assert centered.filter_graph() == "[0:v:0]crop=w=640:h=360[v0]"
    assert positioned.filter_graph() == "[0:v:0]crop=w=640:h=360:x=10:y=20[v0]"


@pytest.mark.parametrize(
    ("factor", "audio_filters"),
    [
        (0.25, ("atempo=0.5", "atempo=0.5")),
        (1.000000001, ("atempo=1.000000001",)),
        (1.23456789, ("atempo=1.23456789",)),
        (1.5, ("atempo=1.5",)),
        (4, ("atempo=2", "atempo=2")),
    ],
)
def test_change_speed_builds_compatible_audio_stages(
    factor: float,
    audio_filters: tuple[str, ...],
) -> None:
    plan = shortcuts.change_speed("in.mp4", "changed.mp4", factor=factor)

    graph = plan.filter_graph()
    assert graph is not None
    assert f"setpts=(PTS-STARTPTS)/{factor}" in graph
    for audio_filter in audio_filters:
        assert audio_filter in graph


def test_normalize_loudness_is_explicitly_one_pass() -> None:
    plan = shortcuts.normalize_loudness("voice.wav", "normal.wav")

    assert plan.filter_graph() == (
        "[0:a:0]loudnorm=I=-16:LRA=11:TP=-1.5[a0];[a0]aresample=48000[a1]"
    )
    assert plan.raw_argv()[-3:] == ("-c:a", "pcm_s16le", "normal.wav")


def test_fit_canvas_builds_scale_pad_and_square_pixels() -> None:
    plan = shortcuts.fit_canvas(
        "portrait.mp4",
        "fitted.mp4",
        width=1280,
        height=720,
    )

    assert plan.filter_graph() == (
        "[0:v:0]scale=w=1280:h=720:"
        "force_original_aspect_ratio=decrease:force_divisible_by=2[v0];"
        "[v0]pad=w=1280:h=720:x=(ow-iw)/2:y=(oh-ih)/2:color=black[v1];"
        "[v1]setsar=1[v2]"
    )


def test_picture_in_picture_drops_finished_inset() -> None:
    plan = shortcuts.picture_in_picture(
        "main.mp4",
        "inset.mp4",
        "pip.mp4",
        inset_width=320,
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert "scale=320:-2" in graph
    assert "eof_action=pass" in graph
    assert plan.raw_argv().count("-i") == 2


def test_waveform_image_changes_audio_into_video() -> None:
    plan = shortcuts.waveform_image(
        "voice.wav",
        "waveform.png",
        width=800,
        height=240,
        color="white",
    )

    assert plan.filter_graph() == (
        "[0:a:0]showwavespic=s=800x240:colors=white:"
        "split_channels=0:scale=lin:filter=peak[v0]"
    )
    assert plan.raw_argv()[-3:] == ("-frames:v", "1", "waveform.png")


def test_spectrum_image_builds_frequency_plot() -> None:
    plan = shortcuts.spectrum_image(
        "voice.wav",
        "spectrum.png",
        mode="separate",
        color="fire",
        legend=False,
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert "showspectrumpic=" in graph
    assert "mode=separate:color=fire:scale=log:legend=0" in graph


def test_still_image_video_scopes_loop_to_image_input() -> None:
    plan = shortcuts.still_image_video(
        "cover.png",
        "voice.wav",
        "episode.mp4",
        width=1280,
        height=720,
    )

    argv = plan.raw_argv()
    assert argv[4:12] == (
        "-loop",
        "1",
        "-framerate",
        "25",
        "-i",
        "cover.png",
        "-i",
        "voice.wav",
    )
    assert argv[-3:] == ("-tune", "stillimage", "episode.mp4")
    assert "-shortest" in argv


def test_contact_sheet_samples_and_tiles_frames() -> None:
    plan = shortcuts.contact_sheet(
        "video.mp4",
        "sheet.jpg",
        columns=3,
        rows=2,
        interval=5,
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert graph.startswith("[0:v:0]fps=fps=0.2")
    assert "tile=layout=3x2:nb_frames=6:padding=4:margin=8:color=black" in graph


def test_duck_music_follows_speech_duration() -> None:
    plan = shortcuts.duck_music("speech.mp4", "music.mp3", "ducked.mp4")

    graph = plan.filter_graph()
    assert graph is not None
    assert "asplit=outputs=2" in graph
    assert "sidechaincompress=" in graph
    assert "amix=inputs=2:duration=first" in graph
    assert plan.raw_argv()[6:10] == ("-stream_loop", "-1", "-i", "music.mp3")


def test_fade_edges_pairs_video_and_audio_fades() -> None:
    plan = shortcuts.fade_edges(
        "video.mp4",
        "faded.mp4",
        duration=10,
        fade_in=2,
        fade_out=3,
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert "fade=t=in:st=0:d=2" in graph
    assert "fade=t=out:st=7:d=3" in graph
    assert "afade=t=in:st=0:d=2" in graph
    assert "afade=t=out:st=7:d=3" in graph


def test_blurred_background_splits_video_once() -> None:
    plan = shortcuts.blurred_background(
        "portrait.mp4",
        "landscape.mp4",
        width=1280,
        height=720,
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert "split=outputs=2" in graph
    assert "force_original_aspect_ratio=increase" in graph
    assert "gblur=sigma=20" in graph
    assert "overlay=x=(W-w)/2:y=(H-h)/2:shortest=1" in graph


def test_reverse_clip_is_trimmed_before_buffering() -> None:
    plan = shortcuts.reverse_clip(
        "video.mp4",
        "reverse.mp4",
        start=3,
        duration=5,
    )

    graph = plan.filter_graph()
    assert graph is not None
    assert graph.index("trim=start=3:end=8") < graph.index("reverse")
    assert graph.index("atrim=start=3:end=8") < graph.index("areverse")


def test_shortcuts_accept_path_objects_and_overwrite() -> None:
    plan = shortcuts.resize(
        Path("folder/input.mp4"),
        Path("folder/output.mp4"),
        width=640,
        overwrite=True,
    )

    assert plan.raw_argv()[3] == "-y"
    assert plan.raw_argv()[5] == str(Path("folder/input.mp4"))


@pytest.mark.parametrize(
    "build",
    [
        lambda: shortcuts.resize("in.mp4", "out.mp4"),
        lambda: shortcuts.resize("in.mp4", "out.mp4", width=1, height=1),
        lambda: shortcuts.trim("in.mp4", "out.mp4"),
        lambda: shortcuts.trim("in.mp4", "out.mp4", start=1, end=2, duration=1),
        lambda: shortcuts.extract_audio("in.mp4", "out.wav"),
        lambda: shortcuts.replace_audio(
            "in.mp4",
            "voice.m4a",
            "out.mp4",
            audio_codec="copy",
        ),
        lambda: shortcuts.join_matching(("one.mp4",), "out.mp4"),
        lambda: shortcuts.join_matching(
            cast(Sequence[shortcuts.Pathish], "ab"),
            "out.mp4",
        ),
        lambda: shortcuts.mix_audio_files(("one.wav",), "out.wav"),
        lambda: shortcuts.grid(("one.mp4",), "out.mp4"),
        lambda: shortcuts.make_gif("in.mp4", "out.gif", fps=101),
        lambda: shortcuts.rotate("in.mp4", "out.mp4", degrees=45),  # type: ignore[arg-type]
        lambda: shortcuts.change_speed("in.mp4", "out.mp4", factor=0),
        lambda: shortcuts.normalize_loudness(
            "voice.wav",
            "out.wav",
            codec="copy",
        ),
        lambda: shortcuts.normalize_loudness(
            "voice.wav",
            "out.wav",
            sample_rate=cast(int, 48_000.5),
        ),
        lambda: shortcuts.replace_audio(
            "in.mp4",
            "voice.m4a",
            "out.mp4",
            duration="shortest",
            audio_codec="copy",
            bitrate="192k",
        ),
        lambda: shortcuts.transcode(
            "in.mov",
            "out.mp4",
            overwrite=cast(bool, "false"),
        ),
        lambda: shortcuts.fit_canvas(
            "in.mp4",
            "out.mp4",
            width=1279,
            height=720,
        ),
        lambda: shortcuts.fade_edges(
            "in.mp4",
            "out.mp4",
            duration=3,
            fade_in=2,
            fade_out=2,
        ),
        lambda: shortcuts.reverse_clip(
            "in.mp4",
            "out.mp4",
            duration=61,
        ),
        lambda: shortcuts.waveform_image(
            "voice.wav",
            "wave.png",
            scale_mode=cast(shortcuts.WaveformScale, "unknown"),
        ),
    ],
)
def test_shortcuts_reject_invalid_requests(build: Callable[[], object]) -> None:
    with pytest.raises(GraphError):
        build()


def test_shortcuts_reject_same_local_input_and_output() -> None:
    with pytest.raises(GraphError, match="differ"):
        shortcuts.transcode("same.mp4", "same.mp4")


def test_shortcut_construction_does_not_start_a_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_process_start(*args: object, **kwargs: object) -> None:
        raise AssertionError("Shortcut construction started a process")

    monkeypatch.setattr(subprocess, "Popen", fail_process_start)
    plans = (
        shortcuts.trim("in.mp4", "clip.mp4", start=1, end=2),
        shortcuts.watermark("in.mp4", "logo.png", "marked.mp4"),
        shortcuts.make_gif("in.mp4", "preview.gif"),
    )

    for plan in plans:
        plan.raw_argv()


@pytest.fixture(scope="module")
def shortcut_media(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[str, Path, Path, Path]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    folder = tmp_path_factory.mktemp("shortcut-media")
    source = folder / "source.mp4"
    voice = folder / "voice.wav"
    logo = folder / "logo.bmp"

    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=64x48:rate=10:duration=0.6",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.6",
            "-shortest",
            "-c:v",
            "mpeg4",
            "-q:v",
            "5",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ),
        check=True,
    )
    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:duration=0.2",
            str(voice),
        ),
        check=True,
    )
    subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=red:size=16x16",
            "-frames:v",
            "1",
            str(logo),
        ),
        check=True,
    )
    return ffmpeg, source, voice, logo


@pytest.mark.integration
def test_watermark_shortcut_runs_with_still_image(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, logo = shortcut_media
    target = source.parent / "watermarked.mp4"

    result = shortcuts.watermark(source, logo, target).run(ffmpeg=ffmpeg, timeout=10)

    assert result.returncode == 0
    assert probe(target).duration is not None
    assert probe(target).audio_streams


@pytest.mark.integration
def test_gif_shortcut_runs_with_generated_video(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    target = source.parent / "preview.gif"

    result = shortcuts.make_gif(
        source,
        target,
        duration=0.4,
        width=32,
        fps=5,
    ).run(ffmpeg=ffmpeg, timeout=10)

    assert result.returncode == 0
    info = probe(target)
    assert info.format is not None
    assert info.format.format_name == "gif"
    assert info.video_streams[0].width == 32


@pytest.mark.integration
def test_speed_shortcut_runs_with_chained_atempo(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    target = source.parent / "fast.mp4"

    shortcuts.change_speed(source, target, factor=4).run(ffmpeg=ffmpeg, timeout=10)

    source_duration = probe(source).duration
    output_duration = probe(target).duration
    assert source_duration is not None
    assert output_duration is not None
    assert output_duration < source_duration


@pytest.mark.integration
def test_replace_audio_shortcut_pads_short_track(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, voice, _ = shortcut_media
    target = source.parent / "dubbed.mp4"

    shortcuts.replace_audio(source, voice, target).run(ffmpeg=ffmpeg, timeout=10)

    info = probe(target)
    assert info.duration == pytest.approx(0.6, abs=0.15)
    assert len(info.audio_streams) == 1


@pytest.mark.integration
def test_fit_canvas_shortcut_has_requested_dimensions(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    target = source.parent / "canvas.mp4"

    shortcuts.fit_canvas(source, target, width=128, height=72).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )

    video = probe(target).video_streams[0]
    assert (video.width, video.height) == (128, 72)


@pytest.mark.integration
def test_audio_image_shortcuts_run(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, voice, _ = shortcut_media
    waveform = source.parent / "waveform.png"
    spectrum = source.parent / "spectrum.png"

    shortcuts.waveform_image(voice, waveform, width=120, height=40).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.spectrum_image(voice, spectrum, width=120, height=60).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )

    waveform_video = probe(waveform).video_streams[0]
    spectrum_video = probe(spectrum).video_streams[0]
    assert (waveform_video.width, waveform_video.height) == (120, 40)
    assert (spectrum_video.width, spectrum_video.height) == (120, 60)


@pytest.mark.integration
def test_still_image_video_ends_with_audio(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, voice, logo = shortcut_media
    target = source.parent / "still.mp4"

    shortcuts.still_image_video(
        logo,
        voice,
        target,
        width=64,
        height=48,
    ).run(ffmpeg=ffmpeg, timeout=10)

    info = probe(target)
    assert info.duration == pytest.approx(0.2, abs=0.2)
    assert len(info.video_streams) == 1
    assert len(info.audio_streams) == 1


@pytest.mark.integration
def test_contact_sheet_has_combined_dimensions(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    target = source.parent / "sheet.jpg"

    shortcuts.contact_sheet(
        source,
        target,
        columns=2,
        rows=2,
        interval=0.1,
        cell_width=32,
        cell_height=24,
        padding=2,
        margin=2,
    ).run(ffmpeg=ffmpeg, timeout=10)

    video = probe(target).video_streams[0]
    assert (video.width, video.height) == (70, 54)


@pytest.mark.integration
def test_duck_and_reverse_shortcuts_run(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, voice, _ = shortcut_media
    ducked = source.parent / "ducked.mp4"
    reversed_target = source.parent / "reversed.mp4"

    shortcuts.duck_music(source, voice, ducked).run(ffmpeg=ffmpeg, timeout=10)
    shortcuts.reverse_clip(source, reversed_target, duration=0.4).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )

    assert probe(ducked).audio_streams
    reversed_info = probe(reversed_target)
    assert reversed_info.duration == pytest.approx(0.4, abs=0.2)
