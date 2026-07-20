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
- [x] Reject local output aliases such as relative paths, file URLs, hard
  links, and symbolic links in one plan.
- [x] Reject a local output that resolves to one of the plan inputs, including
  file URLs and filesystem links.
- [x] Make passthrough-audio video shortcuts work with silent input files
  without mapping a missing audio stream.
- [x] Guarantee even H.264 dimensions for compression, resize, crop, and grid
  outputs.
- [x] Accept integer audio speed factors without calling float-only methods.
- [x] Redact runner and probe errors before keeping a bounded tail.
- [x] Reject raw FFmpeg options that can replace Flowmpeg inputs, mappings,
  filter graphs, overwrite policy, or progress channels.
- [x] Parse FFprobe sample aspect ratios that use colon notation.
- [x] Verify that configured FFmpeg and FFprobe paths identify the requested
  programs.
- [x] Normalize Windows extended path prefixes before checking new output
  aliases.
- [ ] Put a safe resource bound around two-pass edge-silence trimming.
- [ ] Make doctor requirements cover every filter and output capability used by
  each public command.
- [ ] Let audio-transforming timeline shortcuts detect a missing input audio
  stream without a separate probe or `--no-audio` choice.

### P2

- [x] Store the executable kind on missing and unusable binary errors so
  FFmpeg paths containing the word `probe` are classified correctly.
- [x] Keep `ExecutionError` messages short while retaining bounded stderr in
  the structured field.
- [x] Bound probe failure text shown by the CLI.
- [x] Prefer the causal FFmpeg line when choosing a short failure reason.
- [x] Distinguish missing capabilities from capability checks that failed or
  timed out.
- [x] Validate audio bitrate syntax before building a command.
- [x] Ignore audio bitrate controls when audio output is disabled.
- [x] Reject Boolean audio, video, and subtitle stream indexes.
- [x] Reject unordered filter option collections.
- [x] Reject duplicate filter option names.
- [x] Strengthen runtime validation for graph model values.
- [x] Reject optional filter inputs and optional filter outputs built through
  low-level model values.
- [x] Validate direct Python probe timeouts before starting FFprobe.
- [x] Add a package-manager timeout and map timeout failures to `FMG304`.
- [x] Treat end-of-file at the setup confirmation prompt as cancellation.
- [x] Let setup inspect custom FFmpeg and FFprobe executable paths.
- [x] Include tool return codes and bounded failure reasons in doctor JSON.
- [x] Reject nonfinite, Boolean, text, and oversized runner control values.
- [x] Reject malformed numeric and switch values in public audio and video
  recipes.
- [x] Treat dangling symbolic links as existing outputs during preflight.
- [x] Keep cleanup warnings from replacing the active job error.
- [x] Normalize null outputs according to the current operating system.
- [x] Reject unordered filter streams, arguments, and output kinds.
- [x] Test the dependency versions recorded in `uv.lock` in CI.
- [ ] Stop the full FFmpeg process tree after a timeout or callback failure.
- [ ] Bound or coalesce queued progress events when a callback is slow.
- [ ] Make package-manager timeouts stop descendant processes.

## Product and discovery work

- [x] Add a central command catalog with category, alias, input, output, and
  capability metadata.
- [x] Add `flowmpeg commands` with category filtering.
- [x] Add machine-readable command catalog output.
- [x] Add category and search filters to `flowmpeg examples`.
- [x] Add `doctor --require GROUP` for scripts that depend on one feature
  group.
- [ ] Add an optional doctor smoke test that encodes and probes a tiny generated
  input.
- [ ] Split doctor requirements by the exact encoders and muxers each command
  needs.
- [x] Infer progress duration for start and end trims.
- [x] Infer doubled progress duration for boomerang outputs.
- [x] Add a documentation landing page organized by task.
- [x] Add a generated project statistics report from source metadata.
- [x] Test that generated statistics remain current.
- [x] Parse documented terminal options, not only command names.
- [x] Build safe graph examples without starting FFmpeg.
- [x] Execute CMD, PowerShell, and Bash loop examples in documentation tests.
- [x] Add built-in examples for every editing, inspection, and help command.
- [x] Keep built-in example categories aligned with the command catalog.
- [x] Add creator, podcast, privacy, archive, copy, inspect, and silent-input
  tags to commands and examples.
- [x] Generate the CLI command map from the command catalog.
- [x] Add effects and metadata to the documentation task index.
- [x] Add a before-and-after media comparison command with JSON output.
- [x] Expand demo media with a second clip, silent video, logo, music, and image
  sequence inputs.
- [x] Run join, grid, watermark, social, GIF, contact sheet, crossfade, and
  metadata cleanup in the demo lab.
- [x] Document that exit code 3 also covers an unmet doctor requirement.
- [x] Add an encode, copy, and filter behavior matrix.
- [x] Add a stream retention and track-selection matrix.
- [x] Add a social frame dimension and fill-mode comparison.
- [x] Add a plan lifecycle and failure-path diagram.
- [x] Add a podcast voice-chain diagram.
- [x] Add a fixed-region privacy blur coordinate diagram.
- [x] Add probe-first examples for secondary tracks.
- [x] Add CMD, PowerShell, and Bash batch examples.
- [x] Add a generated demo-media script based on FFmpeg test sources.
- [x] Add an education workflow from trim through selectable captions.
- [x] Add a podcast workflow from voice cleanup through tags and audiogram.
- [x] Add a tape review workflow with deinterlacing and review images.
- [x] Add a creator workflow for product demos and derived previews.

## Current limits

- Shortcuts select explicit first streams unless a track option says otherwise.
- Audio-transforming video shortcuts require `include_audio=False` or
  `--no-audio` when the source has no audio stream.
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
- Commits must pass formatting, lint, typing, tests, and
  `python scripts/content_scan.py`.
