# Understand Flowmpeg errors

Flowmpeg reports a stable process exit code and an error identifier. The exit
code is useful in shell scripts. The identifier points to a specific class of
failure.

```text
flowmpeg [FMG612]: FFmpeg exited with code 1
Reason: No such filter: madeup
Try: flowmpeg explain-error FMG612
A partial output may remain. Inspect it before running with --overwrite.
```

List every identifier:

```console
flowmpeg errors
```

Explain one identifier:

```console
flowmpeg explain-error FMG612
```

## Identifier map

| Identifier | Meaning | What to check |
| --- | --- | --- |
| `FMG200` | Invalid media plan | Paths, option ranges, stream choices, output extension |
| `FMG300` | FFmpeg missing | `PATH`, installation, custom `--ffmpeg` path |
| `FMG301` | FFprobe missing | `PATH`, installation, custom `--ffprobe` path |
| `FMG302` | Media tool unusable | Execute permission, architecture, security software |
| `FMG303` | Installer unavailable | Supported package manager or manual installation |
| `FMG304` | Install failed | Package manager output, permissions, network access |
| `FMG400` | Output exists | Output name or `--overwrite` |
| `FMG500` | Probe failed | Input path, URL access, damaged input |
| `FMG600` | FFmpeg failed | The bounded reason line and dry-run command |
| `FMG610` | Encoder missing | FFmpeg encoder list and build choice |
| `FMG611` | Decoder missing | Input codec and FFmpeg decoder list |
| `FMG612` | Filter missing | FFmpeg filter list and build choice |
| `FMG620` | Permission denied | Input access and output folder access |
| `FMG621` | Storage full | Free space on output and temporary devices |
| `FMG630` | Network input failed | URL, credentials, connection, protocol support |
| `FMG700` | Job timed out | `--timeout` value and media duration |

## Process exit codes

| Code | Meaning |
| ---: | --- |
| 0 | Command completed or a preview was printed |
| 1 | Another Flowmpeg error occurred |
| 2 | Arguments or a media plan were invalid |
| 3 | A required executable is unavailable or setup is incomplete |
| 4 | A local output exists |
| 5 | FFprobe could not inspect the input |
| 6 | FFmpeg returned an error |
| 7 | The FFmpeg job reached its timeout |
| 8 | A package manager command failed |
| 130 | The command was interrupted |

CMD exposes the last program's exit code as `%ERRORLEVEL%`:

```bat
flowmpeg convert input.mov -o output.mp4
if errorlevel 1 echo Flowmpeg failed with %ERRORLEVEL%
```

PowerShell exposes it as `$LASTEXITCODE`:

```powershell
flowmpeg convert input.mov -o output.mp4
if ($LASTEXITCODE -ne 0) { Write-Error "Flowmpeg failed" }
```

## Start with a dry run

When a media command fails, print the command without executing it:

```console
flowmpeg captions movie.mp4 captions.srt -o captioned.mp4 --dry-run
```

Add the plan explanation when stream mappings matter:

```console
flowmpeg captions movie.mp4 captions.srt -o captioned.mp4 --dry-run --explain
```

The displayed command redacts common credential locations. It can be copied
for local testing, but inspect it before sharing because media paths can still
contain private names.

## FFmpeg or FFprobe is missing

Typical identifiers: `FMG300`, `FMG301`.

```console
flowmpeg setup
ffmpeg -version
ffprobe -version
```

On Windows, also run:

```console
where ffmpeg
where ffprobe
```

On macOS or Linux:

```console
command -v ffmpeg
command -v ffprobe
```

If installation just finished, open a new terminal so it receives the updated
`PATH`. See the [installation guide](installation.md) for each operating
system.

## The output already exists

Identifier: `FMG400`. Flowmpeg protects local outputs by default.

Use another name:

```console
flowmpeg cut interview.mp4 --duration 30 -o clip-2.mp4
```

Or explicitly replace the file:

```console
flowmpeg cut interview.mp4 --duration 30 -o clip.mp4 --overwrite
```

Flowmpeg does not remove a partial file after a failed run. Inspect or remove
that specific file before enabling replacement.

## An encoder is missing

Identifier: `FMG610`.

Check the build:

```console
flowmpeg doctor
ffmpeg -hide_banner -encoders
```

Common Flowmpeg encoders include `libx264`, `aac`, `libmp3lame`, `png`,
`mov_text`, `srt`, and `webvtt`. A minimal or distribution-specific FFmpeg
build may omit one.

## A decoder is missing

Identifier: `FMG611`.

Probe the input first:

```console
flowmpeg probe problem-file.mkv
ffmpeg -hide_banner -decoders
```

The container extension does not identify every codec inside it. A Matroska
file, for example, can hold many video and audio codecs.

## A filter is missing

Identifier: `FMG612`.

```console
flowmpeg doctor
ffmpeg -hide_banner -filters
```

Doctor groups capabilities by job. A core installation can be ready while a
feature group is limited. This allows copy and probe jobs to work on a smaller
FFmpeg build.

## FFprobe cannot inspect a file

Identifier: `FMG500`.

Try the typed report and then raw JSON:

```console
flowmpeg probe input.mp4
flowmpeg probe input.mp4 --raw
```

Check that the file exists and is readable. For a URL, confirm it works in the
same terminal and that any credentials are still valid.

## Permission is denied

Identifier: `FMG620`.

Check both sides of the job:

- The input file must be readable.
- The output directory must exist and allow file creation.
- The output must not be locked by another application.
- The FFmpeg executable must be allowed to run.

Test a different output folder before changing broad system permissions:

```console
flowmpeg convert input.mov -o test-output.mp4
```

## Storage is full

Identifier: `FMG621`.

The destination device can fill even when the source is small because decoded
or lightly compressed output may be much larger. Check the output device and
any temporary device used by the operating system.

After freeing space, inspect the partial output before replacement:

```console
flowmpeg probe partial.mp4
flowmpeg convert input.mov -o partial.mp4 --overwrite
```

## A network input failed

Identifier: `FMG630`.

The first checks are:

- Confirm the URL in the same machine and network.
- Confirm authorization has not expired.
- Check proxy and firewall rules.
- Check that the FFmpeg build supports the URL protocol.

Previewing a command does not connect to the URL:

```console
flowmpeg convert https://example.com/video.mp4 -o local.mp4 --dry-run
```

## A job timed out

Identifier: `FMG700`.

The timeout is wall-clock run time, not output duration. A one-hour video can
take less or more than one hour to encode.

Increase it:

```console
flowmpeg compress long-recording.mov -o long-recording.mp4 --timeout 7200
```

Or omit `--timeout`:

```console
flowmpeg compress long-recording.mov -o long-recording.mp4
```

## Python exception details

The Python API keeps structured execution fields:

```python
from flowmpeg import ExecutionError, shortcuts as ff

try:
    ff.transcode("input.mov", "output.mp4").run(timeout=300)
except ExecutionError as error:
    print(error.returncode)
    print(error.command)
    print(error.stderr)
```

The CLI prints one bounded reason line. Python callers can inspect the bounded
stderr tail stored on `ExecutionError` when they need more detail.
