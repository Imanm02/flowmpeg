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
| Where is the picture black? | `find-black` | Black picture intervals |
| Where does the picture change sharply? | `scenes` | Timecodes and scene scores |
| Can this machine run a command? | `doctor --command NAME` | Exact capability checks |

Add `--json` when another program will read the result. Human reports favor
short values; JSON keeps named fields and a schema version.

## Check a delivery contract

An audit can require more than the presence of audio and video. This one line
checks a 1080p H.264 and AAC delivery file with a one-minute limit:

```console
flowmpeg audit delivery.mp4 --expect av --max-duration 60 --width 1920 --height 1080 --video-codec h264 --audio-codec aac --sample-rate 48000 --channels 2
```

The report prints the active contract before the measured values:

```text
Media audit: pass
Source: delivery.mp4
Expectation: av
Failure threshold: error
Constraints: duration <= 60s, width = 1920, height = 1080, video codec = h264, audio codec = aac, sample rate = 48000 Hz, channels = 2
Container: QuickTime / MOV
Duration: 58.2 seconds
Size: 24.50 MiB
Streams: 1 video, 1 audio, 0 subtitle
Video: 1920x1080, 30 fps, h264
Audio: 48000 Hz, 2 channel(s), aac
Findings:
  none
```

Each mismatch has a stable finding code and error severity:

| Contract field | Finding | Example meaning |
|---|---|---|
| Minimum duration | `AUD203` | The program is shorter than required |
| Maximum duration | `AUD204` | The upload exceeds its time limit |
| Width | `AUD215` | The first video track has another width |
| Height | `AUD216` | The first video track has another height |
| Video codec | `AUD217` | The first video track uses another codec |
| Audio codec | `AUD224` | The first audio track uses another codec |
| Sample rate | `AUD225` | The first audio track uses another rate |
| Channels | `AUD226` | The first audio track has another channel count |

The codec values are FFprobe codec names such as `h264`, `hevc`, `aac`, or
`opus`. Matching ignores letter case. Width and height apply to the first video
track; audio constraints apply to the first audio track.

Use both duration bounds when a platform requires a range:

```console
flowmpeg check-media advertisement.mp4 --expect av --min-duration 14.5 --max-duration 15.5 --fail-on warning
```

Exit code 9 means the probed file did not meet the selected audit policy. This
makes the command usable as a release gate without parsing its prose output.

## Define an audit contract in Python

```python
from flowmpeg import AuditConstraints, audit_media, probe

contract = AuditConstraints(
    minimum_duration=10,
    maximum_duration=60,
    width=1920,
    height=1080,
    video_codec="h264",
    audio_codec="aac",
    sample_rate=48000,
    channels=2,
)

result = audit_media(probe("delivery.mp4"), expect="av", constraints=contract)
if not result.passes():
    for finding in result.findings:
        print(finding.code, finding.message)
```

The constraints are included in audit JSON, so a stored report records both
what was measured and what the file was expected to match.

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

## Find black picture ranges

```console
flowmpeg find-black tape.mp4
```

The default report requires 98 percent of pixels to be black for at least half
a second. Each pixel counts as black when its normalized level is at or below
0.1. A tape with black leader and a later gap could report:

```text
Black report: 2 intervals
Source: tape.mp4
Video track: 0
Picture ratio: 0.98
Pixel threshold: 0.1
Minimum duration: 0.5s
Total black: 2.900s
Longest black: 2.200s

Intervals:
  1. 0.000s to 0.700s (0.700s)
  2. 5.200s to 7.400s (2.200s)
```

```text
picture    black leader            program             black gap
           |----------|================================|----------|
time       0.00       0.70                              5.20       7.40
candidate  remove lead-in                              chapter break
```

Black ranges are editing candidates, not automatic cuts. A title card with a
black background can meet the detector settings even though it carries useful
text.

## Tune black detection

```console
flowmpeg black-report tape.mp4 --minimum 1.5
flowmpeg find-black faded-film.mp4 --picture-ratio 0.9 --pixel-threshold 0.16
flowmpeg detect-black multi-angle.mkv --track 1 --json
```

| Control | Lower value | Higher value |
|---|---|---|
| `--picture-ratio` | Allows more nonblack pixels | Requires more of the frame to be black |
| `--pixel-threshold` | Uses a darker pixel cutoff | Accepts brighter dark pixels |
| `--minimum-duration` | Reports shorter flashes | Keeps only longer ranges |

The two threshold options are normalized from 0 through 1. Start with the
defaults. For faded analog sources, raise the pixel threshold slightly and
check the returned intervals against the picture.

## Use black intervals in Python

```python
from flowmpeg import detect_black

report = detect_black(
    "tape.mp4",
    picture_ratio=0.95,
    pixel_threshold=0.12,
    minimum_duration=1,
    timeout=60,
)

for interval in report.intervals:
    print(interval.start, interval.end)

print(report.total_black)
```

Use the command-specific doctor check before adding this scan to an ingest
script:

```console
flowmpeg doctor --command find-black
```

The check requires FFmpeg's `blackdetect` filter. The scan maps one selected
video track and does not encode an output file.

## Find scene-change timecodes

```console
flowmpeg scenes interview.mp4
```

The scene score is normalized from 0 through 1. Higher scores mean a larger
visual difference from the preceding frame. The default threshold is 0.35:

```text
Scene report: 3 changes
Source: interview.mp4
Video track: 0
Threshold: 0.35
Strongest change: 48.200s (score 0.910)

Changes:
  1. 12.400s (score 0.430)
  2. 31.750s (score 0.620)
  3. 48.200s (score 0.910)
```

```text
time       0        12.40             31.75             48.20
           |==========|=================|=================|
candidate             cut               chapter           thumbnail
score                  0.43              0.62              0.91
```

The score is not a semantic understanding of the scene. A camera flash or a
hard exposure change can score highly, while a slow dissolve may not cross the
threshold.

## Choose a scene threshold

```console
flowmpeg scenes lecture.mp4 --threshold 0.5
flowmpeg find-scenes music-video.mp4 --threshold 0.2
flowmpeg scene-report multi-angle.mkv --track 1 --threshold 0.4 --json
```

| Goal | Starting threshold | Expected effect |
|---|---:|---|
| Major chapter boundaries | 0.5 | Fewer, stronger candidates |
| General shot changes | 0.35 | Balanced starting list |
| Fast montage review | 0.2 | More candidates, including smaller changes |

Lower the value when known cuts are missing. Raise it when flashes or camera
movement create too many candidates. The report always stays in timeline
order, and `strongest_change` points to the highest score.

## Use scene candidates in Python

```python
from flowmpeg import detect_scenes

report = detect_scenes("interview.mp4", threshold=0.4, timeout=60)

for change in report.changes:
    print(f"{change.time:.3f}s", change.score)

if report.strongest_change is not None:
    print(report.strongest_change.time)
```

Possible next steps include creating chapter candidates, choosing contact-sheet
frames, or reviewing a long recording around its strongest changes. Flowmpeg
reports measurements and leaves the editorial choice to the caller.

```console
flowmpeg doctor --command scenes
```

The exact check requires FFmpeg's `select` and `metadata` video filters.
