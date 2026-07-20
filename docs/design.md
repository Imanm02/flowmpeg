# Design notes

Flowmpeg separates description, compilation, inspection, and execution. That
boundary keeps most behavior testable without an FFmpeg process.

## Layers

```text
Clip methods and recipes
        |
Typed stream graph
        |
Pure command compiler
        |
Probe and process runner
        |
FFprobe and FFmpeg
```

`InputNode` and `FilterNode` values are frozen dataclasses. A stream is a typed
reference to one node output. Combining streams merges their graphs by internal
node identity, while labels are assigned later from topological order.

The recipe layer does not own a second graph format. Audio mixing, overlays,
and clip operations all expand into the same filter nodes exposed by the
low-level API.

## Compiler rules

- Compilation returns an immutable `CompiledCommand`.
- Global arguments appear before inputs.
- Input arguments appear immediately before their matching `-i`.
- Output maps and arguments appear before their destination.
- Filter labels are based on stream kind and traversal order.
- Every filtered output must have one consumer.
- Filter values escape FFmpeg option and graph separators.
- Compilation performs no filesystem writes and starts no process.

Input streams may be mapped directly. Filter outputs that need fanout must pass
through `split` or `asplit`, which keeps the cost visible in the graph.

## Inspection and secrets

`Plan.raw_argv()` exposes the exact command tokens. It is intended for process
execution and advanced debugging. `Plan.command()` formats a redacted copy for
display. URL user information and known secret-bearing header values are hidden
from command displays and captured errors.

## Process runner

The synchronous runner reserves stdout for `-progress pipe:1` and drains stderr
on another thread. Completed progress records are delivered on the caller's
thread. Stderr storage is bounded, timeout cleanup first terminates the child,
and a later kill is used when the grace period expires.

Raw media pipes are outside this runner's first contract. They need a separate
transport design so progress, logs, and media bytes cannot collide.

## Probe model

The common `probe()` path converts FFprobe JSON into frozen container and stream
objects. Missing and `N/A` fields become `None`. Exact ratios remain rational
values. `probe_raw()` remains available for packets, frames, or fields that do
not belong in the common model.

## Planned boundaries

Two-pass loudness normalization and two-pass encoding will use a `Workflow`
that owns several plans and temporary artifacts. Async execution will share the
same compiled command and result models instead of introducing another builder.

Generated wrappers for every FFmpeg filter are not part of the current design.
Typed helpers will be added for common operations, while `filter()` remains the
escape hatch for the rest of FFmpeg.
