# Batch jobs from CMD, PowerShell, and Bash

I use these patterns when one Flowmpeg command needs to run over a folder.
Every editing command still protects an existing output, so a repeated batch
stops or reports the files it would replace unless `--overwrite` is explicit.

Run a capability check before a long batch:

```console
flowmpeg doctor --require web-video
```

Run one representative file with `--dry-run` before processing the directory:

```console
flowmpeg compress sample.mp4 --crf 30 --dry-run -o small/sample.mp4
```

## CMD

CMD uses one percent sign in an interactive prompt and two percent signs in a
`.bat` file.

### Compress every MP4 from an interactive prompt

```bat
if not exist small mkdir small & for %F in (*.mp4) do flowmpeg compress "%F" --crf 30 -o "small\%~nF.mp4"
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
if not exist audio mkdir audio & for %F in (*.mp4) do flowmpeg audio "%F" --codec mp3 --bitrate 192k -o "audio\%~nF.mp3"
```

**Output:** `audio\name.mp3` for each source. Video is not included.

### Speed up a folder of silent captures

```bat
if not exist fast mkdir fast & for %F in (*.mp4) do flowmpeg speed "%F" --factor 4 --no-audio -o "fast\%~nF.mp4"
```

`--no-audio` matters here because speed changes normally filter both video and
audio timing.

### Make review sheets

```bat
if not exist sheets mkdir sheets & for %F in (*.mp4) do flowmpeg sheet "%F" --columns 5 --rows 3 --interval 10 -o "sheets\%~nF.jpg"
```

Each JPEG contains 15 sampled frames. It is useful for checking many takes
without opening each video.

## PowerShell

PowerShell exposes the full input path and base filename as properties, which
avoids manual string slicing.

### Compress a directory

```powershell
New-Item -ItemType Directory -Force small | Out-Null
Get-ChildItem -File *.mp4 | ForEach-Object { flowmpeg compress $_.FullName --crf 30 -o (Join-Path "small" ($_.BaseName + ".mp4")) }
```

### Reframe every clip for vertical delivery

```powershell
New-Item -ItemType Directory -Force vertical | Out-Null
Get-ChildItem -File *.mp4 | ForEach-Object { flowmpeg social $_.FullName --target vertical --fill blur -o (Join-Path "vertical" ($_.BaseName + ".mp4")) }
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
flowmpeg commands --json | ConvertFrom-Json | Where-Object category -eq audio | Select-Object name, aliases, summary
```

This prints only audio commands from the installed catalog. It does not start
FFmpeg.

## Bash

Quote every expansion so spaces in filenames remain one argument.

### Compress all MP4 files and stop on failure

```bash
mkdir -p small && for file in ./*.mp4; do flowmpeg compress "$file" --crf 30 -o "small/$(basename "${file%.mp4}").mp4" || break; done
```

### Create square social copies

```bash
mkdir -p square && for file in ./*.mp4; do name=$(basename "${file%.mp4}"); flowmpeg social "$file" --target square --fill fit -o "square/$name.mp4" || break; done
```

The result keeps the complete image inside a 1080 by 1080 frame and pads the
remaining area.

### Extract one thumbnail per source

```bash
mkdir -p thumbs && for file in ./*.mp4; do name=$(basename "${file%.mp4}"); flowmpeg thumb "$file" --at 5 -o "thumbs/$name.jpg" || printf '%s\n' "$file" >> failed-files.txt; done
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
| A required encoder may be absent | Run `doctor --require GROUP` | Fail before the directory loop starts |

Batch loops do not add parallel execution, cancellation groups, or automatic
cleanup. Each `flowmpeg` process finishes before the next file begins. This
keeps output ownership clear and avoids several jobs competing for the same
CPU and disk at once.
