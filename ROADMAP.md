# Flowmpeg roadmap

This file tracks verified bugs, current limits, and planned work. Items are
ordered by user impact. A checked item should point to shipped behavior, not
only a discussion or test placeholder.

## Verified bugs

### P1

- [x] Redact secret query values in displayed URLs, including signed URL keys.
- [x] Redact input and output values printed by `Plan.explain()`.
- [x] Redact completed destination paths before the CLI prints them.
- [x] Convert FFmpeg startup permission and operating-system failures into a
  typed Flowmpeg error instead of a traceback.
- [x] Convert FFprobe startup permission and operating-system failures into a
  typed Flowmpeg error instead of a traceback.
- [x] Reject `-` as a synchronous runner input or output because the runner
  reserves stdin and stdout.
- [x] Reject local output aliases such as `out.mp4` and `.\out.mp4` in one
  plan.
- [x] Reject a local output that resolves to one of the plan inputs.
- [ ] Make common video shortcuts work with silent input files without mapping
  a missing audio stream.
- [ ] Guarantee even H.264 dimensions for compression, resize, crop, and grid
  outputs.
- [ ] Put a safe resource bound around two-pass edge-silence trimming.
- [ ] Make doctor requirements cover every filter and output capability used by
  each public command.

### P2

- [x] Store the executable kind on missing and unusable binary errors so
  FFmpeg paths containing the word `probe` are classified correctly.
- [x] Keep `ExecutionError` messages short while retaining bounded stderr in
  the structured field.
- [x] Bound probe failure text shown by the CLI.
- [x] Prefer the causal FFmpeg line when choosing a short failure reason.
- [ ] Distinguish missing capabilities from capability checks that failed or
  timed out.
- [x] Validate audio bitrate syntax before building a command.
- [x] Ignore audio bitrate controls when audio output is disabled.
- [x] Reject Boolean audio, video, and subtitle stream indexes.
- [ ] Reject unordered filter option collections.
- [ ] Reject duplicate filter option names.
- [ ] Strengthen runtime validation for graph model values.
- [ ] Add a package-manager timeout and map timeout failures to `FMG304`.
- [ ] Treat end-of-file at the setup confirmation prompt as cancellation.
- [ ] Let setup inspect custom FFmpeg and FFprobe executable paths.
- [ ] Include tool return codes and bounded failure reasons in doctor JSON.

## Product and discovery work

- [ ] Add a central command catalog with category, alias, input, output, and
  capability metadata.
- [ ] Add `flowmpeg commands` with category filtering.
- [ ] Add machine-readable command catalog output.
- [ ] Add category and search filters to `flowmpeg examples`.
- [ ] Add `doctor --require GROUP` for scripts that depend on one feature
  group.
- [ ] Add an optional doctor smoke test that encodes and probes a tiny generated
  input.
- [ ] Infer progress duration for start and end trims.
- [ ] Infer doubled progress duration for boomerang outputs.
- [ ] Add a documentation landing page organized by task.
- [ ] Add a generated project statistics report from source metadata.
- [ ] Test that generated statistics remain current.
- [ ] Parse documented terminal options, not only command names.
- [ ] Build safe graph examples without starting FFmpeg.
- [ ] Add an encode, copy, and filter behavior matrix.
- [ ] Add a stream retention and track-selection matrix.
- [ ] Add a social frame dimension and fill-mode comparison.
- [ ] Add a plan lifecycle and failure-path diagram.
- [ ] Add a podcast voice-chain diagram.
- [ ] Add a fixed-region privacy blur coordinate diagram.
- [ ] Add probe-first examples for secondary tracks.
- [ ] Add CMD, PowerShell, and Bash batch examples.
- [ ] Add a generated demo-media script based on FFmpeg test sources.
- [ ] Add an education workflow from trim through selectable captions.
- [ ] Add a podcast workflow from voice cleanup through tags and audiogram.
- [ ] Add an archive workflow with deinterlacing and review images.
- [ ] Add creator workflows for product demos and animation sequences.

## Current limits

- Shortcuts select explicit first streams unless a track option says otherwise.
- Fixed-region blur does not track a moving face, plate, or screen area.
- Compression quality settings do not guarantee a smaller file than every
  possible input. Measure the result before choosing a delivery setting.
- Subtitle addition creates a selectable MP4 text track. It does not burn text
  into video frames.
- Metadata removal copies selected first streams. It does not claim to remove
  every private byte from every container format.
- Reverse video and reverse audio filters buffer decoded media in memory.
- HLS, DASH, frame directories, and other multi-file outputs need explicit
  artifact ownership before they become shortcuts.
- Batch orchestration, cancellation groups, and temporary-file cleanup are not
  part of the current single-process runner.

## Release gates

- Every behavior change needs a focused regression test.
- FFmpeg-specific fixes need a real-media integration test when practical.
- Documentation command examples must use registered commands.
- New public commands must declare their category and capability needs.
- Commits must pass formatting, lint, typing, tests, and the content scan.
