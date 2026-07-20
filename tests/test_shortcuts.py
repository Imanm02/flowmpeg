import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

import pytest

from flowmpeg import GraphError, probe, shortcuts
from flowmpeg.plan import Plan
from flowmpeg.recipes.video import Rotation


def test_shortcuts_namespace_is_public() -> None:
    assert shortcuts.trim.__module__ == "flowmpeg.shortcuts"
    assert set(shortcuts.__all__) == {
        "AudioCodec",
        "AudioLayout",
        "AudioReplacementCodec",
        "CrossfadeCurve",
        "DeinterlaceMode",
        "EncoderPreset",
        "FlipDirection",
        "NamedPosition",
        "Pathish",
        "ReplacementDuration",
        "SocialFill",
        "SocialTarget",
        "SpectrumColor",
        "SpectrumMode",
        "VideoPreset",
        "WaveformScale",
        "add_music",
        "add_subtitles",
        "adjust_colors",
        "blur_region",
        "blurred_background",
        "boomerang",
        "burn_subtitles",
        "change_speed",
        "compress_audio",
        "compress_video",
        "contact_sheet",
        "crop",
        "deinterlace",
        "denoise_audio",
        "duck_music",
        "extract_audio",
        "extract_subtitles",
        "fade_edges",
        "fit_canvas",
        "flip_video",
        "freeze_end",
        "grid",
        "join_normalized",
        "image_sequence_video",
        "join_matching",
        "make_gif",
        "mix_audio_files",
        "mono_audio",
        "mute_section",
        "normalize_loudness",
        "picture_in_picture",
        "podcast_audiogram",
        "podcast_voice",
        "reframe",
        "remove_audio",
        "remove_subtitles",
        "resample_audio",
        "replace_audio",
        "resize",
        "reverse_clip",
        "rotate",
        "set_frame_rate",
        "sharpen",
        "social_video",
        "spectrum_image",
        "still_image_video",
        "strip_metadata",
        "tag_audio",
        "tag_media",
        "thumbnail",
        "transcode",
        "transcode_hevc",
        "trim",
        "trim_silence",
        "transcode_webm",
        "watermark",
        "waveform_image",
        "crossfade_audio",
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
        "0:a:0?",
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


def test_webm_transcode_sets_vp9_and_opus() -> None:
    plan = shortcuts.transcode_webm(
        "source.mov",
        "delivery.webm",
        crf=28,
        cpu_used=4,
        audio_bitrate="96k",
    )
    argv = plan.raw_argv()

    assert argv[argv.index("-c:v") : argv.index("-c:v") + 2] == (
        "-c:v",
        "libvpx-vp9",
    )
    assert argv[argv.index("-c:a") : argv.index("-c:a") + 2] == (
        "-c:a",
        "libopus",
    )
    assert argv[argv.index("-crf") : argv.index("-crf") + 2] == ("-crf", "28")
    assert "0:a:0?" in argv


def test_hevc_transcode_sets_x265_and_hvc1() -> None:
    plan = shortcuts.transcode_hevc(
        "source.mov",
        "delivery.mp4",
        crf=26,
        encoder_preset="slow",
        audio_bitrate="128k",
    )
    argv = plan.raw_argv()

    pairs = tuple(zip(argv, argv[1:], strict=False))
    assert ("-c:v", "libx265") in pairs
    assert ("-tag:v", "hvc1") in pairs
    assert ("-crf", "26") in pairs
    assert ("-preset", "slow") in pairs
    assert ("-c:a", "aac") in pairs


@pytest.mark.parametrize(
    "plan",
    [
        shortcuts.transcode("silent.mov", "out.mp4"),
        shortcuts.resize("silent.mov", "out.mp4", width=640),
        shortcuts.crop("silent.mov", "out.mp4", width=640, height=360),
    ],
)
def test_video_only_filters_map_audio_optionally(plan: Plan) -> None:
    assert "0:a:0?" in plan.raw_argv()


def test_timeline_shortcuts_attach_video_only_fallbacks() -> None:
    plans = (
        shortcuts.trim("movie.mp4", "trim.mp4", duration=2),
        shortcuts.join_matching(("one.mp4", "two.mp4"), "join.mp4"),
        shortcuts.change_speed("movie.mp4", "speed.mp4", factor=2),
        shortcuts.fade_edges("movie.mp4", "fade.mp4", duration=2),
        shortcuts.freeze_end("movie.mp4", "freeze.mp4"),
        shortcuts.reverse_clip("movie.mp4", "reverse.mp4", duration=2),
        shortcuts.boomerang("movie.mp4", "bounce.mp4", duration=2),
    )

    for plan in plans:
        assert plan.audio_probe_sources
        assert plan.missing_audio_fallback is not None
        assert "0:a:0" not in plan.missing_audio_fallback.raw_argv()


def test_explicit_video_only_timeline_plan_skips_probe() -> None:
    plan = shortcuts.change_speed(
        "silent.mp4",
        "fast.mp4",
        factor=2,
        include_audio=False,
    )

    assert plan.audio_probe_sources == ()
    assert plan.missing_audio_fallback is None


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


@pytest.mark.parametrize(("width", "height"), [(1279, None), (None, 719)])
def test_resize_rejects_odd_web_dimensions(
    width: int | None,
    height: int | None,
) -> None:
    with pytest.raises(GraphError, match="must be even"):
        shortcuts.resize("in.mp4", "out.mp4", width=width, height=height)


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
        ("audio.opus", "opus", ("-c:a", "libopus", "-b:a", "128k")),
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


@pytest.mark.parametrize("width,height", [(639, 360), (640, 359)])
def test_grid_rejects_odd_cell_dimensions(width: int, height: int) -> None:
    with pytest.raises(GraphError, match="must be even"):
        shortcuts.grid(
            ("one.mp4", "two.mp4"),
            "grid.mp4",
            cell_width=width,
            cell_height=height,
        )


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


@pytest.mark.parametrize("width,height", [(639, 360), (640, 359)])
def test_crop_rejects_odd_web_dimensions(width: int, height: int) -> None:
    with pytest.raises(GraphError, match="must be even"):
        shortcuts.crop("in.mp4", "out.mp4", width=width, height=height)


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


def test_compress_video_exposes_size_controls() -> None:
    plan = shortcuts.compress_video(
        "source.mov",
        "small.mp4",
        crf=30,
        encoder_preset="slow",
        max_width=1280,
        audio_bitrate="96k",
    )

    graph = plan.filter_graph()
    assert graph == "[0:v:0]scale=w=trunc(min(iw\\,1280)/2)*2:h=-2[v0]"
    argv = plan.raw_argv()
    assert argv[argv.index("-crf") : argv.index("-crf") + 2] == ("-crf", "30")
    assert argv[argv.index("-preset") : argv.index("-preset") + 2] == (
        "-preset",
        "slow",
    )
    assert argv[argv.index("-b:a") : argv.index("-b:a") + 2] == ("-b:a", "96k")


@pytest.mark.parametrize("bitrate", ["", "0k", "128 kbps", "fast", "-1k"])
def test_compress_video_rejects_invalid_audio_bitrates(bitrate: str) -> None:
    with pytest.raises(GraphError, match="positive value"):
        shortcuts.compress_video("source.mov", "small.mp4", audio_bitrate=bitrate)


def test_compress_video_ignores_bitrate_without_audio() -> None:
    plan = shortcuts.compress_video(
        "silent.mov",
        "small.mp4",
        include_audio=False,
        audio_bitrate="not-used",
    )

    assert "-b:a" not in plan.raw_argv()


def test_reframe_and_social_targets_build_expected_frames() -> None:
    reframed = shortcuts.reframe(
        "wide.mp4",
        "vertical.mp4",
        width=720,
        height=1280,
    )
    square = shortcuts.social_video(
        "wide.mp4",
        "square.mp4",
        target="square",
        fill="fit",
    )

    assert "force_original_aspect_ratio=increase" in (reframed.filter_graph() or "")
    assert "crop=w=720:h=1280" in (reframed.filter_graph() or "")
    assert "pad=w=1080:h=1080" in (square.filter_graph() or "")


def test_video_correction_shortcuts_build_filters() -> None:
    plans = {
        "fps=fps=24": shortcuts.set_frame_rate("in.mp4", "fps.mp4", fps=24),
        "bwdif=mode=send_frame": shortcuts.deinterlace("in.mp4", "deint.mp4"),
        "hflip": shortcuts.flip_video("in.mp4", "flip.mp4"),
        "eq=brightness=0.1:contrast=1.2:saturation=0.9:gamma=1.1": (
            shortcuts.adjust_colors(
                "in.mp4",
                "color.mp4",
                brightness=0.1,
                contrast=1.2,
                saturation=0.9,
                gamma=1.1,
            )
        ),
        "unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=1": (
            shortcuts.sharpen("in.mp4", "sharp.mp4")
        ),
    }

    for expected, plan in plans.items():
        assert expected in (plan.filter_graph() or "")


def test_time_and_region_video_shortcuts_build_bounded_graphs() -> None:
    frozen = shortcuts.freeze_end("in.mp4", "frozen.mp4", seconds=3)
    muted = shortcuts.mute_section("in.mp4", "muted.mp4", start=2, end=4)
    blurred = shortcuts.blur_region(
        "in.mp4",
        "blurred.mp4",
        x=10,
        y=20,
        width=100,
        height=50,
    )
    bounced = shortcuts.boomerang("in.mp4", "bounce.mp4", duration=4)

    assert "tpad=stop_mode=clone:stop_duration=3" in (frozen.filter_graph() or "")
    assert "apad=pad_dur=3" in (frozen.filter_graph() or "")
    assert "enable=between(t\\,2\\,4)" in (muted.filter_graph() or "")
    assert "crop=w=100:h=50:x=10:y=20" in (blurred.filter_graph() or "")
    assert "boxblur=luma_radius=12:luma_power=2:chroma_radius=12" in (
        blurred.filter_graph() or ""
    )
    assert "reverse" in (bounced.filter_graph() or "")
    assert "concat=n=2:v=1:a=1" in (bounced.filter_graph() or "")


def test_audio_cleanup_shortcuts_build_expected_chains() -> None:
    denoised = shortcuts.denoise_audio("voice.wav", "clean.wav")
    compressed = shortcuts.compress_audio("voice.wav", "level.wav")
    podcast = shortcuts.podcast_voice("voice.wav", "podcast.wav")
    trimmed = shortcuts.trim_silence("voice.wav", "trimmed.wav", duration=120)
    mono = shortcuts.mono_audio("voice.wav", "mono.wav")

    assert "afftdn=nr=12:nf=-50" in (denoised.filter_graph() or "")
    assert "acompressor=threshold=0.125:ratio=3" in (compressed.filter_graph() or "")
    podcast_graph = podcast.filter_graph() or ""
    assert "highpass=f=80" in podcast_graph
    assert "lowpass=f=12000" in podcast_graph
    assert "loudnorm=I=-16:LRA=11:TP=-1.5" in podcast_graph
    trimmed_graph = trimmed.filter_graph() or ""
    assert "atrim=end=120" in trimmed_graph
    assert trimmed_graph.count("silenceremove=") == 2
    assert "aformat=channel_layouts=mono" in (mono.filter_graph() or "")


def test_resample_audio_sets_rate_and_layout() -> None:
    plan = shortcuts.resample_audio(
        "interview.wav",
        "standard.wav",
        sample_rate=44_100,
        layout="mono",
    )

    assert plan.filter_graph() == (
        "[0:a:0]aresample=44100[a0];[a0]aformat=channel_layouts=mono[a1]"
    )


def test_crossfade_audio_maps_two_inputs() -> None:
    plan = shortcuts.crossfade_audio(
        "first.wav",
        "second.wav",
        "joined.wav",
        duration=2,
        curve="qsin",
    )

    assert plan.filter_graph() == ("[0:a:0][1:a:0]acrossfade=d=2:c1=qsin:c2=qsin[a0]")
    assert plan.raw_argv().count("-i") == 2


def test_join_normalized_aligns_video_and_audio_formats() -> None:
    plan = shortcuts.join_normalized(
        ("phone.mp4", "camera.mp4"),
        "joined.mp4",
        width=1280,
        height=720,
        fps=24,
        sample_rate=44_100,
    )
    graph = plan.filter_graph() or ""

    assert graph.count("scale=w=1280:h=720") == 2
    assert graph.count("pad=w=1280:h=720") == 2
    assert graph.count("fps=fps=24") == 2
    assert graph.count("aresample=44100") == 2
    assert graph.count("aformat=channel_layouts=stereo") == 2
    assert "concat=n=2:v=1:a=1" in graph
    assert plan.missing_audio_fallback is not None


def test_subtitle_shortcuts_map_selected_streams() -> None:
    extracted = shortcuts.extract_subtitles("movie.mkv", "captions.vtt", track=1)
    added = shortcuts.add_subtitles(
        "movie.mp4",
        "captions.srt",
        "captioned.mp4",
        language="fra",
    )
    removed = shortcuts.remove_subtitles("movie.mkv", "plain.mp4")
    burned = shortcuts.burn_subtitles(
        "movie.mp4",
        "captions.srt",
        "open-captioned.mp4",
        font_name="Arial",
        font_size=28,
    )

    assert extracted.raw_argv()[6:8] == ("-map", "0:s:1")
    assert extracted.raw_argv()[-3:-1] == ("-c:s", "webvtt")
    assert "1:s:0" in added.raw_argv()
    assert added.raw_argv()[
        added.raw_argv().index("-c:s") : added.raw_argv().index("-c:s") + 2
    ] == ("-c:s", "mov_text")
    assert "0:s:0" not in removed.raw_argv()
    assert burned.filter_graph() == (
        "[0:v:0]subtitles=filename=captions.srt:si=0:"
        "force_style=FontName=Arial\\,FontSize=28[v0]"
    )
    assert "0:a:0?" in burned.raw_argv()


def test_burn_subtitles_escapes_windows_filter_paths() -> None:
    plan = shortcuts.burn_subtitles(
        "movie.mp4",
        r"C:\Media Files\captions.srt",
        "captioned.mp4",
    )

    assert "filename=C\\\\\\:/Media Files/captions.srt" in (plan.filter_graph() or "")


def test_image_sequence_uses_input_frame_rate() -> None:
    plan = shortcuts.image_sequence_video(
        "frames/frame-%04d.png",
        "timelapse.mp4",
        fps=24,
        start_number=10,
        width=1280,
        height=720,
    )

    assert plan.raw_argv()[4:10] == (
        "-framerate",
        "24",
        "-start_number",
        "10",
        "-i",
        "frames/frame-%04d.png",
    )
    assert "pad=w=1280:h=720" in (plan.filter_graph() or "")


def test_podcast_audiogram_keeps_audio_and_draws_wave() -> None:
    plan = shortcuts.podcast_audiogram(
        "episode.wav",
        "cover.png",
        "episode.mp4",
        width=1280,
        height=720,
        wave_width=1000,
        wave_height=160,
    )

    graph = plan.filter_graph() or ""
    assert "asplit=outputs=2" in graph
    assert "showwaves=s=1000x160:mode=line:colors=white:rate=25" in graph
    assert "colorkey=color=black:similarity=0.01:blend=0.1" in graph
    assert plan.raw_argv()[-3:] == ("-tune", "stillimage", "episode.mp4")


def test_metadata_shortcuts_copy_selected_streams() -> None:
    stripped = shortcuts.strip_metadata("source.mkv", "clean.mkv")
    tagged = shortcuts.tag_audio(
        "source.m4a",
        "tagged.m4a",
        title="Episode 1",
        artist="Example Host",
    )

    assert stripped.raw_argv()[-7:-1] == (
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c",
        "copy",
    )
    assert ("-metadata", "title=Episode 1") in tuple(
        zip(tagged.raw_argv(), tagged.raw_argv()[1:], strict=False)
    )
    assert "0:v:0" not in tagged.raw_argv()


def test_tag_media_copies_tracks_and_sets_container_fields() -> None:
    plan = shortcuts.tag_media(
        "source.mp4",
        "tagged.mp4",
        title="Camera master",
        comment="Approved copy",
        include_subtitles=True,
    )
    argv = plan.raw_argv()

    assert "0:v:0" in argv
    assert "0:a:0?" in argv
    assert "0:s:0" in argv
    assert ("-c", "copy") in tuple(zip(argv, argv[1:], strict=False))
    assert ("-metadata", "title=Camera master") in tuple(
        zip(argv, argv[1:], strict=False)
    )
    assert ("-metadata", "comment=Approved copy") in tuple(
        zip(argv, argv[1:], strict=False)
    )


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
        lambda: shortcuts.transcode_webm("in.mov", "out.mp4"),
        lambda: shortcuts.transcode_webm("in.mov", "out.webm", crf=64),
        lambda: shortcuts.transcode_webm("in.mov", "out.webm", cpu_used=9),
        lambda: shortcuts.transcode_webm(
            "in.mov",
            "out.webm",
            audio_bitrate="96k -map 0",
        ),
        lambda: shortcuts.transcode_hevc("in.mov", "out.webm"),
        lambda: shortcuts.transcode_hevc("in.mov", "out.mp4", crf=52),
        lambda: shortcuts.transcode_hevc(
            "in.mov",
            "out.mp4",
            encoder_preset=cast(shortcuts.EncoderPreset, "quick"),
        ),
        lambda: shortcuts.join_normalized(("one.mp4",), "out.mp4"),
        lambda: shortcuts.join_normalized(
            ("one.mp4", "two.mp4"), "out.mp4", width=1279
        ),
        lambda: shortcuts.join_normalized(("one.mp4", "two.mp4"), "out.mp4", fps=0),
        lambda: shortcuts.join_normalized(
            ("one.mp4", "two.mp4"), "out.mp4", sample_rate=7999
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
        lambda: shortcuts.compress_video("in.mov", "out.mp4", crf=52),
        lambda: shortcuts.compress_video(
            "in.mov",
            "out.mp4",
            encoder_preset=cast(shortcuts.EncoderPreset, "quick"),
        ),
        lambda: shortcuts.social_video(
            "in.mp4",
            "out.mp4",
            target=cast(shortcuts.SocialTarget, "story"),
        ),
        lambda: shortcuts.social_video(
            "in.mp4",
            "out.mp4",
            fill=cast(shortcuts.SocialFill, "stretch"),
        ),
        lambda: shortcuts.set_frame_rate("in.mp4", "out.mp4", fps=0),
        lambda: shortcuts.deinterlace(
            "in.mp4",
            "out.mp4",
            mode=cast(shortcuts.DeinterlaceMode, "auto"),
        ),
        lambda: shortcuts.flip_video(
            "in.mp4",
            "out.mp4",
            direction=cast(shortcuts.FlipDirection, "diagonal"),
        ),
        lambda: shortcuts.adjust_colors(
            "in.mp4",
            "out.mp4",
            brightness=2,
        ),
        lambda: shortcuts.sharpen("in.mp4", "out.mp4", matrix_size=4),
        lambda: shortcuts.freeze_end("in.mp4", "out.mp4", seconds=61),
        lambda: shortcuts.mute_section(
            "in.mp4",
            "out.mp4",
            start=4,
            end=2,
        ),
        lambda: shortcuts.blur_region(
            "in.mp4",
            "out.mp4",
            x=-1,
            y=0,
            width=100,
            height=100,
        ),
        lambda: shortcuts.boomerang("in.mp4", "out.mp4", duration=16),
        lambda: shortcuts.denoise_audio(
            "in.wav",
            "out.wav",
            codec="copy",
        ),
        lambda: shortcuts.compress_audio(
            "in.wav",
            "out.wav",
            ratio=21,
        ),
        lambda: shortcuts.podcast_voice(
            "in.wav",
            "out.wav",
            highpass=3_000,
            lowpass=2_000,
        ),
        lambda: shortcuts.trim_silence(
            "in.wav",
            "out.wav",
            duration=120,
            threshold_db=-100,
        ),
        lambda: shortcuts.trim_silence(
            "in.wav",
            "out.wav",
            duration=601,
        ),
        lambda: shortcuts.crossfade_audio(
            "one.wav",
            "two.wav",
            "out.wav",
            curve=cast(shortcuts.CrossfadeCurve, "linear"),
        ),
        lambda: shortcuts.extract_subtitles("in.mkv", "out.txt"),
        lambda: shortcuts.add_subtitles(
            "in.mp4",
            "captions.srt",
            "out.mp4",
            language="english",
        ),
        lambda: shortcuts.burn_subtitles(
            "in.mp4",
            "captions.srt",
            "out.mp4",
            font_size=0,
        ),
        lambda: shortcuts.burn_subtitles(
            "in.mp4",
            "captions.srt",
            "out.mp4",
            font_name="Arial,FontSize=80",
        ),
        lambda: shortcuts.image_sequence_video("frames/*.png", "out.mp4"),
        lambda: shortcuts.podcast_audiogram(
            "voice.wav",
            "cover.png",
            "out.mp4",
            width=640,
            height=360,
            wave_width=800,
        ),
        lambda: shortcuts.strip_metadata("in.mkv", "out.mp4"),
        lambda: shortcuts.tag_audio("in.m4a", "out.m4a"),
        lambda: shortcuts.tag_audio(
            "in.m4a",
            "out.m4a",
            title="\x00",
        ),
        lambda: shortcuts.tag_media("in.mp4", "out.mp4"),
        lambda: shortcuts.tag_media("in.mp4", "out.mkv", title="Copy"),
        lambda: shortcuts.tag_media(
            "in.mp4",
            "out.mp4",
            title="Copy",
            video_track=True,
        ),
        lambda: shortcuts.tag_media(
            "in.mp4",
            "out.mp4",
            title="\x00",
        ),
        lambda: shortcuts.resample_audio(
            "in.wav",
            "out.wav",
            sample_rate=7_999,
        ),
        lambda: shortcuts.resample_audio(
            "in.wav",
            "out.wav",
            layout=cast(shortcuts.AudioLayout, "surround"),
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
def test_trim_silence_runs_with_bounded_audio(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, _, voice, _ = shortcut_media
    target = voice.parent / "trimmed.wav"

    shortcuts.trim_silence(
        voice,
        target,
        duration=0.2,
        threshold_db=-80,
        minimum=0.01,
    ).run(ffmpeg=ffmpeg, timeout=10)

    assert probe(target).duration == pytest.approx(0.2, abs=0.1)


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


@pytest.mark.integration
def test_new_video_shortcuts_run(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    compressed = source.parent / "compressed.mp4"
    reframed = source.parent / "reframed.mp4"
    corrected = source.parent / "corrected.mp4"
    private = source.parent / "private.mp4"

    shortcuts.compress_video(source, compressed, max_width=48).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.reframe(source, reframed, width=48, height=64).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    correction = shortcuts.adjust_colors(
        source,
        corrected,
        brightness=0.05,
        saturation=0.8,
    )
    correction.run(ffmpeg=ffmpeg, timeout=10)
    shortcuts.blur_region(
        source,
        private,
        x=4,
        y=4,
        width=16,
        height=16,
        radius=8,
    ).run(ffmpeg=ffmpeg, timeout=10)

    assert probe(compressed).video_streams[0].width == 48
    reframed_video = probe(reframed).video_streams[0]
    assert (reframed_video.width, reframed_video.height) == (48, 64)
    assert probe(corrected).video_streams
    assert probe(private).video_streams


@pytest.mark.integration
def test_compress_video_handles_odd_source_dimensions(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "odd.mkv"
    target = tmp_path / "compressed.mp4"
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
            "testsrc=size=63x47:duration=0.2",
            "-c:v",
            "ffv1",
            str(source),
        ),
        check=True,
    )

    shortcuts.compress_video(
        source,
        target,
        include_audio=False,
    ).run(ffmpeg=ffmpeg, timeout=10)

    video = probe(target).video_streams[0]
    assert video.width is not None and video.width % 2 == 0
    assert video.height is not None and video.height % 2 == 0


@pytest.mark.integration
def test_video_filters_accept_a_source_without_audio(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "silent.mp4"
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
            "color=black:size=64x48:duration=0.2",
            "-c:v",
            "libx264",
            "-an",
            str(source),
        ),
        check=True,
    )
    targets = (
        shortcuts.transcode(source, tmp_path / "converted.mp4"),
        shortcuts.transcode_webm(source, tmp_path / "converted.webm"),
        shortcuts.join_normalized(
            (source, source),
            tmp_path / "joined-silent.mp4",
            width=64,
            height=48,
            fps=15,
        ),
        shortcuts.resize(source, tmp_path / "resized.mp4", width=32),
        shortcuts.crop(source, tmp_path / "cropped.mp4", width=32, height=24),
    )

    for plan in targets:
        plan.run(ffmpeg=ffmpeg, timeout=10)
        info = probe(plan.outputs[0].destination)
        assert info.video_streams
        assert not info.audio_streams


@pytest.mark.integration
def test_hevc_transcode_runs(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    encoders = subprocess.run(
        (ffmpeg, "-hide_banner", "-encoders"),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if "libx265" not in encoders:
        pytest.skip("The FFmpeg build does not include libx265")
    target = source.parent / "delivery-hevc.mp4"

    shortcuts.transcode_hevc(
        source,
        target,
        crf=35,
        encoder_preset="ultrafast",
        include_audio=False,
    ).run(ffmpeg=ffmpeg, timeout=20)

    info = probe(target)
    assert info.video_streams[0].codec_name == "hevc"
    assert not info.audio_streams


@pytest.mark.integration
def test_join_normalized_runs_with_different_inputs(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    second = source.parent / "different.mp4"
    target = source.parent / "normalized-join.mp4"
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
            "color=blue:size=80x60:rate=12:duration=0.3",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:sample_rate=32000:duration=0.3",
            "-shortest",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(second),
        ),
        check=True,
    )

    shortcuts.join_normalized(
        (source, second),
        target,
        width=64,
        height=48,
        fps=15,
        sample_rate=44_100,
    ).run(ffmpeg=ffmpeg, timeout=10)
    info = probe(target)

    assert info.video_streams[0].width == 64
    assert info.video_streams[0].height == 48
    assert info.audio_streams[0].sample_rate == 44_100
    assert info.duration is not None and info.duration > 0.6


@pytest.mark.integration
def test_new_timeline_shortcuts_run(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    frozen = source.parent / "frozen.mp4"
    muted = source.parent / "muted.mp4"
    bounced = source.parent / "bounced.mp4"

    shortcuts.freeze_end(source, frozen, seconds=0.2).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.mute_section(source, muted, start=0.1, end=0.3).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.boomerang(source, bounced, duration=0.2).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )

    assert probe(frozen).duration == pytest.approx(0.8, abs=0.2)
    assert probe(muted).audio_streams
    assert probe(bounced).duration == pytest.approx(0.4, abs=0.2)


@pytest.mark.integration
def test_new_audio_shortcuts_run(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, voice, _ = shortcut_media
    denoised = source.parent / "denoised.wav"
    podcast = source.parent / "podcast.wav"
    mono = source.parent / "mono.wav"
    mono_opus = source.parent / "mono.opus"
    resampled = source.parent / "resampled.wav"
    crossfaded = source.parent / "crossfaded.wav"

    shortcuts.denoise_audio(voice, denoised).run(ffmpeg=ffmpeg, timeout=10)
    shortcuts.podcast_voice(voice, podcast).run(ffmpeg=ffmpeg, timeout=10)
    shortcuts.mono_audio(voice, mono).run(ffmpeg=ffmpeg, timeout=10)
    shortcuts.mono_audio(voice, mono_opus, codec="opus", bitrate="64k").run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.resample_audio(
        voice,
        resampled,
        sample_rate=32_000,
        layout="stereo",
    ).run(ffmpeg=ffmpeg, timeout=10)
    shortcuts.crossfade_audio(
        voice,
        voice,
        crossfaded,
        duration=0.05,
    ).run(ffmpeg=ffmpeg, timeout=10)

    assert probe(denoised).audio_streams
    assert probe(podcast).audio_streams
    assert probe(mono).audio_streams[0].channels == 1
    assert probe(mono_opus).audio_streams[0].codec_name == "opus"
    resampled_stream = probe(resampled).audio_streams[0]
    assert resampled_stream.sample_rate == 32_000
    assert resampled_stream.channels == 2
    assert probe(crossfaded).duration == pytest.approx(0.35, abs=0.1)


@pytest.mark.integration
def test_subtitle_and_metadata_shortcuts_run(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, _, _ = shortcut_media
    captions = source.parent / "captions.srt"
    captioned = source.parent / "captioned.mp4"
    extracted = source.parent / "extracted.srt"
    stripped = source.parent / "stripped.mp4"
    burned = source.parent / "burned.mp4"
    tagged = source.parent / "tagged.mp4"
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:00,500\nExample caption\n",
        encoding="utf-8",
    )

    shortcuts.add_subtitles(source, captions, captioned).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.extract_subtitles(captioned, extracted).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.strip_metadata(captioned, stripped).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.burn_subtitles(source, captions, burned, font_size=28).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )
    shortcuts.tag_media(
        source,
        tagged,
        title="Camera master",
        comment="Approved copy",
    ).run(
        ffmpeg=ffmpeg,
        timeout=10,
    )

    assert probe(captioned).subtitle_streams
    assert "Example caption" in extracted.read_text(encoding="utf-8")
    assert not probe(stripped).subtitle_streams
    assert probe(burned).video_streams
    assert not probe(burned).subtitle_streams
    tagged_info = probe(tagged)
    assert tagged_info.format is not None
    assert dict(tagged_info.format.tags)["title"] == "Camera master"
    assert tagged_info.video_streams
    assert tagged_info.audio_streams


@pytest.mark.integration
def test_sequence_and_audiogram_shortcuts_run(
    shortcut_media: tuple[str, Path, Path, Path],
) -> None:
    ffmpeg, source, voice, logo = shortcut_media
    frame_pattern = source.parent / "sequence-%02d.png"
    sequence = source.parent / "sequence.mp4"
    audiogram = source.parent / "audiogram.mp4"
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
            "testsrc=size=32x24:rate=5:duration=0.6",
            str(frame_pattern),
        ),
        check=True,
    )

    shortcuts.image_sequence_video(
        frame_pattern,
        sequence,
        fps=5,
        width=64,
        height=48,
    ).run(ffmpeg=ffmpeg, timeout=10)
    shortcuts.podcast_audiogram(
        voice,
        logo,
        audiogram,
        width=64,
        height=48,
        wave_width=48,
        wave_height=12,
        frame_rate=10,
    ).run(ffmpeg=ffmpeg, timeout=10)

    sequence_video = probe(sequence).video_streams[0]
    assert (sequence_video.width, sequence_video.height) == (64, 48)
    audiogram_info = probe(audiogram)
    assert audiogram_info.video_streams
    assert audiogram_info.audio_streams
