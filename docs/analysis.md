# Media analysis

Flowmpeg analysis commands answer questions before an edit starts. They do not
write media files. I use them to find cut points, check delivery files, and
choose settings from measured input instead of guessing.

## Choose the report

| Question | Command | Result |
|---|---|---|
| What streams and codecs are present? | `probe` | Typed container and stream fields |
| Does the file have the streams I expect? | `audit` | Stable findings and a pass decision |
| What changed after an edit? | `compare` | Before and after media values |
| How loud is an audio track? | `loudness` | EBU R128 measurements |
| Where are the quiet gaps? | `find-silence` | Start, end, and duration intervals |
| Can this machine run a command? | `doctor --command NAME` | Exact capability checks |

Add `--json` when another program will read the result. Human reports favor
short values; JSON keeps named fields and a schema version.

## Find silence in one line

```console
flowmpeg find-silence interview.wav
```

With the defaults, a range must stay at or below -40 dB for at least half a
second. A result with two gaps looks like this:

```text
Silence report: 2 intervals
Source: interview.wav
Audio track: 0
Threshold: -40 dB
Minimum duration: 0.5s
Total silence: 2.970s
Longest silence: 2.250s

Intervals:
  1. 0.000s to 0.720s (0.720s)
  2. 5.250s to 7.500s (2.250s)
```

The same report can be pictured as a small timeline:

```text
time       0.00        0.72                 5.25        7.50
           |-----------|=====================|-----------|
level      silence              sound               silence
edit idea  trim lead-in                       review this gap
```

The report finds candidates. It does not remove them, because a pause may be
intentional speech timing or room tone that should stay.

## Match the threshold to the recording

```console
flowmpeg silence-report studio.wav --noise-db -50 --minimum-duration 0.3
flowmpeg find-silence meeting.wav --noise-db -35 --minimum 1.2
flowmpeg detect-silence field.wav --noise-db -28 --minimum-duration 2
```

| Recording | Starting threshold | Starting duration | Reason |
|---|---:|---:|---|
| Clean studio voice | -50 dB | 0.3 s | A low noise floor makes short pauses visible |
| Online meeting | -35 dB | 1.2 s | Fan noise may sit above a studio threshold |
| Outdoor recorder | -28 dB | 2.0 s | Longer ranges reduce false matches from speech dips |

These are starting points, not loudness rules. If speech appears in the
reported intervals, lower the threshold or require a longer duration. If no
gaps appear, raise the threshold in small steps.

## Inspect another audio track

Tracks use zero-based positions within the input's audio streams. Probe first,
then pass the position you want:

```console
flowmpeg probe interview.mkv
flowmpeg find-silence interview.mkv --track 1 --minimum 0.8
```

This is useful when track 0 is a mix and track 1 is an isolated microphone.
The command maps only the selected audio track and ignores video, subtitles,
and data streams during the scan.

## Read JSON from another program

```console
flowmpeg find-silence interview.wav --json
```

The report has stable field names:

```json
{
  "intervals": [
    {
      "duration": 0.72,
      "end": 0.72,
      "start": 0.0
    }
  ],
  "longest_silence": 0.72,
  "minimum_duration": 0.5,
  "noise_db": -40.0,
  "schema_version": 1,
  "source": "interview.wav",
  "total_silence": 0.72,
  "track": 0
}
```

PowerShell can select the longest gap in one line:

```powershell
flowmpeg find-silence interview.wav --json | ConvertFrom-Json | Select-Object longest_silence
```

## Use the Python report

```python
from flowmpeg import detect_silence

report = detect_silence(
    "interview.wav",
    noise_db=-42,
    minimum_duration=0.75,
    timeout=30,
)

for gap in report.intervals:
    print(gap.start, gap.end, gap.duration)

print(report.total_silence)
print(report.longest_silence)
```

`SilenceReport` and `SilenceInterval` are frozen dataclasses. The terminal JSON
comes from the same typed values used by Python callers.

## Failure behavior

The analysis uses the same process boundary as loudness measurement. It starts
FFmpeg without a shell, captures a bounded diagnostic tail on failure, and
stops the FFmpeg process tree on timeout.

```console
flowmpeg find-silence missing.wav
flowmpeg find-silence video-only.mp4
flowmpeg find-silence long-session.wav --timeout 20
```

Common outcomes are:

| Situation | Result |
|---|---|
| FFmpeg is missing | Exit code 3 and `FMG300` |
| The selected audio track is missing | Exit code 6 and bounded FFmpeg context |
| The scan exceeds `--timeout` | Exit code 7 and `FMG700` |
| No silence meets the settings | Success with zero intervals |

Run the exact capability check before depending on the command in a job:

```console
flowmpeg doctor --command find-silence
```

This checks for FFmpeg's `silencedetect` filter. It does not require a video
encoder or an output muxer because the command writes no media file.
