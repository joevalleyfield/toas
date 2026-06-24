# Large event graph render performance

Filed as: 260624-large-event-graph-render-performance

## Goal
Make graph/history inspection commands usable on large durable logs, including event files around 55MB, without multi-minute or unbounded-feeling render times.

## Problem
The event graph renderer repeatedly scans edge lists to resolve parents and active lanes. On large mostly-linear histories this makes rendering effectively quadratic, so a big `.toas/events.jsonl` can appear hung.

The same log also exposes `toas heads` cost: 503 heads over ~38k message records should be a small query, but the operator API rebuilds each head lineage separately.

The dogfood log also includes duplicate message ids from earlier history. The graph renderer must not collapse duplicate ids into shared nodes while still replaying duplicate edges, because that can create cyclic/repeated traversal during layout.

## Scope
- Optimize renderer-side graph lookup and row/lane computations.
- Optimize head-row stats so `toas heads` does not rebuild every lineage independently.
- Keep renderer graph construction robust to duplicate durable message ids.
- Preserve temporal and consequence projection output contracts.
- Add focused regression coverage for long lineages and multi-head stats.

## Acceptance
- `toas graph` shared renderer avoids repeated full-graph parent scans.
- `toas heads` computes row stats from shared indexed state.
- Duplicate message ids do not make renderer traversal hang.
- Long linear histories render in bounded time under targeted tests.
- Existing event graph projection tests continue to pass.
