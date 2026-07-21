# Batch jobs from CMD, PowerShell, and Bash

I wrote the native batch command for the common case where a directory of
local videos needs the same web MP4 conversion. It works the same way in CMD,
PowerShell, and Bash because Flowmpeg performs file discovery itself.

Shell loops are still useful for operations such as thumbnails, social
reframing, and audio extraction. Those recipes follow the native command.

For the compression examples, run the broad web-video check first:

```console
flowmpeg doctor --require web-video
flowmpeg doctor --command batch
```

The first check covers a family of delivery commands. The second resolves the
`batch` alias and checks the exact default H.264, AAC, and MP4 requirements.
Treat the results as preflight signals, then run one representative file
before the directory job.

Run one representative file with `--dry-run` before processing the directory:

```console
flowmpeg compress sample.mp4 --crf 30 --dry-run -o small/sample.mp4
```

## Convert a folder in one line

Pass a directory to convert its supported video files without descending into
subdirectories:

```console
flowmpeg batch recordings -o converted
```

Quote a wildcard in CMD so Flowmpeg, rather than the shell, expands it:

```console
flowmpeg batch "recordings/*.mov" -o converted
```

The canonical command and both aliases mean the same thing:

```console
flowmpeg batch-transcode recordings -o converted
flowmpeg batch-convert recordings -o converted
```

Use `shrink-batch` when the same folder needs smaller HEVC MP4 files with
size-reduction controls:

```console
flowmpeg shrink-batch "recordings/*.MOV" -o small-recordings
flowmpeg shrink-batch recordings -o small-recordings --recursive
```

The default shrink batch output name adds `-small`, so `recording.mov` becomes
`small-recordings/recording-small.mp4`. The same command accepts `--codec`,
`--crf`, `--max-height`, `--fps`, `--audio-codec`, and `--audio-bitrate`:

```console
flowmpeg shrink-batch "recordings/*.MOV" --max-height 720 --fps 30 --crf 28 -o small-recordings
flowmpeg shrink-batch "meetings/*.MOV" --audio-codec opus --audio-bitrate 32k -o small-meetings
flowmpeg shrink-batch "client/*.MOV" --codec h264 --audio-codec aac --crf 27 -o client-small
```

Flowmpeg recognizes common local video suffixes including MP4, MOV, MKV,
WebM, AVI, MPEG, MTS, and M2TS. An exact file path is accepted even when its
suffix is outside that discovery list.

### Search subdirectories

```console
flowmpeg batch recordings -o converted --recursive
flowmpeg batch "recordings/**/*.mov" -o converted --recursive
```

Directory entries are sorted by path. Repeated paths are removed, so the same
file is not encoded twice when two input patterns overlap.

### Control output names

The default output name is the source stem plus `.mp4`. Add text to every
stem when the result should be easy to distinguish:

```console
flowmpeg batch recordings -o converted --name-suffix=-web
```

| Source | Default output | With `--name-suffix=-web` |
|---|---|---|
| `intro.mov` | `converted/intro.mp4` | `converted/intro-web.mp4` |
| `lesson.mkv` | `converted/lesson.mp4` | `converted/lesson-web.mp4` |
| `silent.webm` | `converted/silent.mp4` | `converted/silent-web.mp4` |

If two sources would create the same output path, the command stops before
starting FFmpeg. For example, `camera/clip.mov` and `phone/clip.mkv` both map
to `converted/clip.mp4`.

### Preview every FFmpeg command

```console
flowmpeg batch recordings -o converted --dry-run
flowmpeg batch recordings -o converted --dry-run --json
```

Dry runs discover and validate the inputs but do not create the output
directory. JSON contains an ordered `jobs` array with each name, destination,
and redacted command.

### Handle silent inputs and time limits

```console
flowmpeg batch captures -o converted --no-audio
flowmpeg batch recordings -o converted --timeout 300
```

The timeout applies to each file, not to the batch total. The default audio
mode checks each source at run time and uses a video-only plan when the source
has no audio. `--no-audio` skips that check and always creates silent output.

### Choose the failure policy

The default stops after the first failure:

```text
COMPLETED intro.mov
FAILED    broken.mov
SKIPPED   lesson.mov
SKIPPED   outro.mov
```

Use this when later outputs depend on every earlier file succeeding:

```console
flowmpeg batch recordings -o converted
```

Use `--continue-on-error` when each file is independent:

```console
flowmpeg batch recordings -o converted --continue-on-error
```

```text
COMPLETED intro.mov
FAILED    broken.mov
COMPLETED lesson.mov
COMPLETED outro.mov
```

Successful final outputs remain in the selected output directory. Flowmpeg
does not delete completed work because another source fails later.

### Protect existing outputs

Without `--overwrite`, Flowmpeg checks every planned output before the first
job starts. One existing destination stops the whole batch with exit code 4:

```console
flowmpeg batch recordings -o converted
```

Replace those final files only when they are known rebuilds:

```console
flowmpeg batch recordings -o converted --overwrite
```

### Read the result as data

```console
flowmpeg batch recordings -o converted --continue-on-error --json
```

An example result shape is:

```json
{
  "counts": {
    "cancelled": 0,
    "completed": 18,
    "failed": 1,
    "skipped": 0
  },
  "elapsed": 94.8,
  "ok": false,
  "schema_version": 1
}
```

The real object also contains an ordered `items` array. Each item has a name,
state, elapsed time, output paths, and an error type when it failed.

```text
Example batch, 19 files
completed  ##################  18
failed     #                   1
cancelled                      0
skipped                        0
```

These numbers show the report layout. Actual counts and times come from the
current run.

### Exit codes

| Result | Exit code |
|---|---:|
| Every job completed | 0 |
| Invalid source, pattern, or duplicate output | 2 |
| FFmpeg or FFprobe is unavailable | 3 |
| A final output already exists | 4 |
| FFmpeg failed | 6 |
| A job exceeded its timeout | 7 |
| The batch was cancelled or interrupted | 130 |

## Build a batch in Python

Named jobs can use any `Plan`, so one batch is not limited to the terminal
command's web MP4 conversion:

```python
import flowmpeg
from flowmpeg import shortcuts as ff

jobs = (
    flowmpeg.BatchJob("intro", ff.transcode("intro.mov", "web/intro.mp4")),
    flowmpeg.BatchJob("lesson", ff.resize("lesson.mp4", "web/lesson.mp4", width=1280)),
    flowmpeg.BatchJob("audio", ff.extract_audio("talk.mp4", "web/talk.mp3")),
)

result = flowmpeg.run_batch(jobs, continue_on_error=True)
for item in result.items:
    print(item.name, item.status, item.outputs)
```

The result always follows job order. Its counts separate completed, failed,
cancelled, and skipped jobs.

### Cancel a running group

`CancellationToken` is thread-safe. A UI, signal handler, or controller thread
can call `cancel()`. The active FFmpeg process tree is stopped, and jobs that
have not started are marked cancelled.

```python
import flowmpeg
from flowmpeg import shortcuts as ff

token = flowmpeg.CancellationToken()
jobs = (
    flowmpeg.BatchJob("one", ff.transcode("one.mov", "out/one.mp4")),
    flowmpeg.BatchJob("two", ff.transcode("two.mov", "out/two.mp4")),
)

token.cancel()
result = flowmpeg.run_batch(jobs, token=token)
print(result.cancelled)
```

The terminal command maps Ctrl+C to exit code 130 and uses the same process
tree cleanup in the runner.

### Keep temporary intermediates separate

Use `BatchWorkspace` for files that are not final deliverables. It creates a
unique directory and removes everything under it when the context exits,
including after an exception:

```python
import flowmpeg
from flowmpeg import shortcuts as ff

with flowmpeg.BatchWorkspace() as workspace:
    intermediate = workspace.allocate("stage/voice.wav")
    job = flowmpeg.BatchJob(
        "extract voice",
        ff.extract_audio("interview.mp4", intermediate, codec="wav"),
    )
    result = flowmpeg.run_batch((job,))
    print(result.ok)
```

Workspace paths reject absolute values and parent traversal. Final batch
outputs do not use this workspace automatically because deleting a completed
deliverable would be surprising.

## Shell loops for other commands

The next patterns apply one non-batch Flowmpeg command to a folder. Every
editing command still protects an existing output, so a repeated loop stops
or reports files it would replace unless `--overwrite` is explicit.

## CMD

CMD uses one percent sign in an interactive prompt and two percent signs in a
`.bat` file.

### Compress every MP4 from an interactive prompt

```bat
(if not exist small mkdir small) & for %F in (*.mp4) do flowmpeg compress "%F" --crf 30 -o "small\%~nF.mp4"
```

**Input:** every `.mp4` in the current directory.

**Output:** one H.264 MP4 in `small` for each input. `interview.mp4` becomes
`small\interview.mp4`.

### Put the same job in a batch file

```bat
@if not exist small mkdir small
@for %%F in (*.mp4) do flowmpeg compress "%%F" --crf 30 -o "small\%%~nF.mp4" || exit /b 1
```

The `|| exit /b 1` part stops at the first failed edit. Remove that part when
later files should still be attempted.

### Extract audio from every MP4

```bat
(if not exist audio mkdir audio) & for %F in (*.mp4) do flowmpeg audio "%F" --codec mp3 --bitrate 192k -o "audio\%~nF.mp3"
```

**Output:** `audio\name.mp3` for each source. Video is not included.
Use `doctor --require audio-files` as a broad audio-format preflight.

### Speed up a folder of silent captures

```bat
(if not exist fast mkdir fast) & for %F in (*.mp4) do flowmpeg speed "%F" --factor 4 --no-audio -o "fast\%~nF.mp4"
```

`--no-audio` matters here because speed changes normally filter both video and
audio timing.

### Make review sheets

```bat
(if not exist sheets mkdir sheets) & for %F in (*.mp4) do flowmpeg sheet "%F" --columns 5 --rows 3 --interval 10 -o "sheets\%~nF.jpg"
```

Each JPEG has 15 cells and up to 15 sampled frames. A short source can leave
cells empty. Use `doctor --require analysis-images` as a broad image-output
preflight.

## PowerShell

PowerShell exposes the full input path and base filename as properties, which
avoids manual string slicing.

### Compress a directory

```powershell
New-Item -ItemType Directory -Force small | Out-Null
Get-ChildItem -File *.mp4 | ForEach-Object { flowmpeg compress $_.FullName --crf 30 -o (Join-Path "small" ($_.BaseName + ".mp4")); if ($LASTEXITCODE -ne 0) { throw "Flowmpeg failed for $($_.FullName)" } }
```

### Reframe every clip for vertical delivery

```powershell
New-Item -ItemType Directory -Force vertical | Out-Null
Get-ChildItem -File *.mp4 | ForEach-Object { flowmpeg social $_.FullName --target vertical --fill blur -o (Join-Path "vertical" ($_.BaseName + ".mp4")); if ($LASTEXITCODE -ne 0) { throw "Flowmpeg failed for $($_.FullName)" } }
```

**Output:** 1080 by 1920 MP4 files with the full source shown over a blurred
background.

### Continue after a failed file and record its name

```powershell
Get-ChildItem -File *.mp4 | ForEach-Object { flowmpeg thumb $_.FullName --at 5 -o (Join-Path "thumbs" ($_.BaseName + ".jpg")); if ($LASTEXITCODE -ne 0) { $_.Name | Add-Content failed-files.txt } }
```

Create `thumbs` first. A failed source name is appended to
`failed-files.txt`; successful files produce one JPEG.

### Read the command catalog as data

```powershell
(flowmpeg commands --json | ConvertFrom-Json).commands | Where-Object category -eq audio | Select-Object name, aliases, summary
```

This prints only audio commands from the installed catalog. It does not start
FFmpeg. The top-level object contains `schema_version` and `commands` fields.

## Bash

Quote every expansion so spaces in filenames remain one argument.

### Compress all MP4 files and stop on failure

```bash
mkdir -p small && (shopt -s nullglob; for file in ./*.mp4; do flowmpeg compress "$file" --crf 30 -o "small/$(basename "${file%.mp4}").mp4" || exit $?; done)
```

### Create square social copies

```bash
mkdir -p square && (shopt -s nullglob; for file in ./*.mp4; do name=$(basename "${file%.mp4}"); flowmpeg social "$file" --target square --fill fit -o "square/$name.mp4" || exit $?; done)
```

The result keeps the complete image inside a 1080 by 1080 frame and pads the
remaining area.

### Extract one thumbnail per source

```bash
mkdir -p thumbs && (shopt -s nullglob; for file in ./*.mp4; do name=$(basename "${file%.mp4}"); flowmpeg thumb "$file" --at 5 -o "thumbs/$name.jpg" || printf '%s\n' "$file" >> failed-files.txt; done)
```

This version continues after a failure and records the input path.

## Safer batch choices

| Situation | Choice | Reason |
|---|---|---|
| First run on unfamiliar media | Add `--dry-run` to one file | Inspect maps and filters before processing |
| Destination may already contain work | Keep the default | Existing outputs remain untouched |
| Outputs are disposable rebuilds | Add `--overwrite` | Each destination may be replaced |
| Input videos have no audio | Add `--no-audio` | Audio filters must not request a missing track |
| Files may use different tracks | Run `flowmpeg probe` first | Default shortcuts select the first matching stream |
| A required encoder may be absent | Run `doctor --require GROUP` | Get a broad preflight result before the loop |

Native batches and these shell loops run one FFmpeg process at a time. This
keeps ordering stable and prevents several encoders from competing for the
same CPU and disk at once. Native batches add state reporting, cancellation,
and temporary workspaces; shell loops keep the failure behavior of their
chosen shell.
