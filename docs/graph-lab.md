# Graph lab without running FFmpeg

I use these examples when I need a layout that is more specific than a
shortcut. Every block builds and compiles a plan. None of them reads an input
or starts FFmpeg.

## Put a logo over scaled video

```python
from flowmpeg import input, output
from flowmpeg.recipes.video import named_overlay_position, overlay_video, scale

source = input("lesson.mp4")
background = scale(source.video(), width=1280)
logo = scale(input("logo.png").video(), width=160)
x, y = named_overlay_position("top-right", padding=20)
video = overlay_video(background, logo, x=x, y=y)
plan = output(video, source.audio(), to="lesson-branded.mp4")

print(plan.command())
```

The graph maps filtered video and the original first audio stream.

## Make two outputs from one filtered stream

```python
from flowmpeg import input, output
from flowmpeg.recipes.video import scale

video = scale(input("camera.mp4").video(), width=1280)
preview_video, archive_video = video.split()
plan = output(preview_video, to="preview.mp4", args=("-c:v", "libx264"))
plan = plan.add_output(
    archive_video,
    to="archive.mkv",
    args=("-c:v", "ffv1"),
)

print(plan.explain())
print(plan.command())
```

`split` is required because one filter output cannot feed two consumers.

## Build a side-by-side review file

```python
from flowmpeg import input, output, stack_video
from flowmpeg.recipes.video import scale

before = scale(input("before.mp4").video(), width=640, height=360)
after = scale(input("after.mp4").video(), width=640, height=360)
review = stack_video(before, after, columns=2, shortest=True)
plan = output(review, to="review.mp4", args=("-c:v", "libx264"))

print(plan.filter_graph())
```

The first input appears on the left because stream order is preserved.

## Mix voice and music with explicit gain

```python
from flowmpeg import input, output
from flowmpeg.recipes.audio import mix_audio, volume

voice = input("voice.wav").audio()
music = volume(input("music.wav").audio(), db=-18)
mixed = mix_audio(voice, music, weights=(1, 0.8), duration="first")
plan = output(mixed, to="program.wav", args=("-c:a", "pcm_s16le"))

print(plan.command())
```

The music gain happens before the two inputs reach `amix`.

## Keep optional audio on a direct mapping

```python
from flowmpeg import input, output
from flowmpeg.recipes.video import scale

source = input("maybe-silent.mp4")
video = scale(source.video(), width=854)
audio = source.audio(optional=True)
plan = output(
    video,
    audio,
    to="delivery.mp4",
    args=("-c:v", "libx264", "-c:a", "aac"),
)

print(plan.command())
```

Optional streams can be mapped directly. They cannot feed an audio filter,
because a filter input must exist when FFmpeg builds the graph.
