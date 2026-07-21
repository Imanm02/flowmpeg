# PSNR and SSIM quality reports

I added this report for checking how an encoded candidate differs from a known
reference. FFmpeg calculates the frame metrics; Flowmpeg validates the inputs,
parses the summaries, and returns typed values instead of leaving them inside
diagnostic text.

## Measure both metrics

```console
flowmpeg quality reference.mov candidate.mp4
```

The default runs PSNR and SSIM in separate passes and prints one report:

```text
Visual quality report
Reference: reference.mov (video track 0)
Candidate: candidate.mp4 (video track 0)
Dimensions: 1920x1080
Window: full shared timeline
PSNR:
  average: 42.700 dB
  minimum: 40.100 dB
  maximum: 45.900 dB
  components: Y 42.100 dB, U 44.200 dB, V 43.300 dB
SSIM:
  all: 0.993000 (21.549 dB)
  components: Y 0.991000 (20.457 dB), U 0.995000 (23.010 dB)
Elapsed: 8.24s
```

The values are an example report shape, not a promised result for a codec or
quality setting.

## Read PSNR

PSNR is expressed in decibels. Higher values mean less pixel error against the
reference under the same alignment and dimensions.

```text
more pixel error                                      less pixel error
20 dB          30 dB          40 dB          50 dB          inf dB
                                                              ^
                                                     identical samples
```

`inf dB` means FFmpeg measured no pixel difference. It is preserved as Python
infinity and serialized as the JSON string `"inf"`.

There is no universal PSNR pass value. Grain, animation, screen recordings,
camera noise, scaling, and color conversion can change what one number means.
Compare candidates made for the same source and delivery goal.

Run only this pass when SSIM is not needed:

```console
flowmpeg quality reference.mov candidate.mp4 --metric psnr
```

## Read SSIM

SSIM measures structural similarity. A value of 1 means identical measured
structure; values closer to 1 indicate a closer match. Flowmpeg also reports
FFmpeg's decibel form in parentheses.

```text
example only
0.900              0.950              0.990              1.000
  |------------------|------------------|------------------|
less similar                                             identical
```

Run only SSIM with:

```console
flowmpeg quality reference.mov candidate.mp4 --metric ssim
```

PSNR and SSIM answer different questions. PSNR emphasizes sample error. SSIM
emphasizes local structure. Keep both when comparing encoding choices, then
inspect difficult scenes with a player.

## Compare a short window

A full feature-length comparison decodes both videos twice. Use a bounded
window while tuning settings:

```console
flowmpeg quality reference.mov candidate.mp4 --start 600 --duration 30
flowmpeg quality reference.mov candidate.mp4 --start 600 --duration 30 --metric ssim
```

The same start and duration are applied to both inputs. The timeout applies to
each FFmpeg metric pass:

```console
flowmpeg quality reference.mov candidate.mp4 --duration 60 --timeout 120
```

## Select video tracks

Track numbers are indexes within each file's video streams:

```console
flowmpeg quality reference.mkv candidate.mkv --reference-track 1 --candidate-track 0
```

Probe both files before choosing secondary tracks:

```console
flowmpeg probe reference.mkv
flowmpeg probe candidate.mkv
```

The selected tracks must have known matching dimensions. Flowmpeg refuses a
1920 by 1080 reference and a 1280 by 720 candidate instead of scaling one
silently. Resize through an explicit, inspectable command when scaling is part
of the intended comparison.

## Use JSON in a release check

```console
flowmpeg quality reference.mov candidate.mp4 --json
flowmpeg quality reference.mov candidate.mp4 --metric ssim --json
```

The report includes:

| Field | Meaning |
|---|---|
| `reference`, `candidate` | Compared sources |
| `reference_track`, `candidate_track` | Selected video-only indexes |
| `width`, `height` | Validated shared dimensions |
| `start`, `duration` | Requested comparison window |
| `psnr.average_db` | Average PSNR across measured frames |
| `psnr.minimum_db`, `maximum_db` | Lowest and highest frame summaries |
| `ssim.all` | Combined SSIM value |
| `ssim.db` | Combined SSIM in decibels |
| `components` | Luma and chroma, or RGB values when FFmpeg reports them |
| `elapsed` | Probe and measurement wall time |
| `schema_version` | CLI JSON schema version |

A small policy script can read the JSON and apply thresholds chosen for one
project. Keep the raw scores in build artifacts so a later threshold change
does not erase the measured history.

## Check the installed filters

```console
flowmpeg doctor --command quality
flowmpeg doctor --require quality-analysis
```

Both checks require the PSNR and SSIM filters. The command also needs FFprobe
to validate tracks and dimensions.

## Use the Python API

```python
import flowmpeg

report = flowmpeg.measure_quality(
    "reference.mov",
    "candidate.mp4",
    start=120,
    duration=20,
    timeout=60,
)

if report.psnr is not None:
    print(report.psnr.average_db)
if report.ssim is not None:
    print(report.ssim.all)
```

Use `metric="psnr"` or `metric="ssim"` to skip the other pass. Component
values preserve the names FFmpeg reports, such as Y, U, V or R, G, B.

## Pair quality with media comparison

`quality` decodes frames and compares their pixels or structure. `compare`
probes file-level facts such as codec, size, duration, dimensions, and stream
counts.

```console
flowmpeg compare reference.mov candidate.mp4
flowmpeg quality reference.mov candidate.mp4
```

| Question | Command |
|---|---|
| Did file size or codec change? | `compare` |
| Did duration or stream count change? | `compare` |
| How much pixel error was measured? | `quality` PSNR |
| How close was measured structure? | `quality` SSIM |

## Measurement boundaries

The report assumes corresponding timestamps contain corresponding pictures.
Edits that shift time, remove frames, change speed, or alter cuts need explicit
alignment before measurement. Audio is not measured. A high score does not
prove that text is readable, faces look natural, or a delivery file meets a
business requirement.

VMAF is not part of this first report because many FFmpeg builds omit
`libvmaf`. It remains a separate optional-capability task on the roadmap.
