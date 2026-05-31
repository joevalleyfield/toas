# Roots on Top Event Graph Visualization

## Goal

Render rooted event graphs in a terminal.

The renderer is optimized for:

```text
[gutter][label]
```

where:

* labels consume most horizontal space
* topology is compressed into a narrow gutter
* vertical scrolling is assumed
* multiple projections may exist over the same graph

The canonical graph is not the rendering.

The rendering is a projection.

---

## Terminology

### Forest

A collection of root nodes.

### Tree

A rooted causal structure.

### Node

An event in the graph.

Nodes are rendered explicitly.

### Branch

A divergence of futures.

### Corridor

A projection-level continuation path.

A corridor represents an unresolved future.

Corridors are not reused.

Corridors are not screen columns.

### Lane

A renderer-level screen column.

Lanes are reusable.

Corridors are routed into lanes.

### Projection

A question asked of the graph.

Examples:

```text
temporal projection
consequence projection
workboard projection
agent-specific projection
```

---

## Important Observation

The renderer is not primarily visualizing containment.

It is primarily visualizing continuity.

Filesystem-style renderers are optimized for:

```text
many siblings
bounded depth
```

Event graphs are optimized for:

```text
few simultaneous futures
deep continuity
```

The renderer should preserve continuity whenever possible.

---

## Canonical Input Graph

Topology:

```text
R
└─ A
   ├─ A1
   │  └─ A1a
   │     └─ A1b
   ├─ A2
   └─ A3
      └─ A3a
         └─ A3b
            └─ A3c
```

Chronology:

```text
R
A
A1
A2
A3
A1a
A1b
A3a
A3b
A3c
```

This fixture should remain part of the test suite.

Most renderer concepts were derived from this example.

---

## Temporal Projection

Question:

```text
What happened next?
```

Chronology is preserved.

Reference rendering:

```text
○ A
├─╮
│ ○ A1
├─|─╮
│ │ ○ A2
│ |
○─│─ A3
│ │
│ ○ A1a
│ │
│ ○ A1b
│
○ A3a
│
○ A3b
│
○ A3c
```

Important properties:

* A3 appears before A1a and A1b.
* A1 remains visibly active after A3 appears.
* A3 inherits A's primary continuation.
* unresolved futures remain visible.

---

## Consequence Projection

Question:

```text
What came from this?
```

Chronology may be relaxed.

Reference rendering:

```text
○ A
├─╮
│ ○ A2
├─╮
│ ○ A1
│ │
│ ○ A1a
│ │
│ ○ A1b
│
○ A3
│
○ A3a
│
○ A3b
│
○ A3c
```

Important properties:

* chronology is intentionally relaxed
* short-lived futures are drained first
* long-lived futures inherit the primary continuation
* width is reduced relative to the temporal projection

The consequence projection spends temporal freedom to recover horizontal label space.

---

## Corridor Model

A corridor is:

```text
reserved continuation for an unresolved future
```

A corridor is not:

```text
a subtree
a lane
a parent-child edge
```

Example:

```text
C0 : A -> A3 -> A3a -> A3b -> A3c
C1 : A1 -> A1a -> A1b
C2 : A2
```

Corridors are projection artifacts.

They are not properties of the canonical graph.

---

## Node Markers

Node markers are semantically significant.

The renderer must distinguish:

```text
event occurrence
```

from:

```text
continuity
```

A useful mental model:

```text
line   = corridor continuity
circle = event occurrence
```

or equivalently:

```text
line   = corridor
circle = corridor ownership transfer
```

Removing node markers destroys information.

They are not decorative glyphs.

---

## Lane Allocation

Lanes are renderer resources.

Initial allocator:

```text
allocate lowest free lane
release lane when corridor ends
never move active corridors
```

Start simple.

Observe real graphs before introducing compaction.

---

## Filtering

Filtering is explicitly out of scope for the initial renderer.

However, projections are expected to operate on filtered views of the graph.

Examples:

```text
collapsed explorations
summarized dead ends
agent-specific views
workboard views
```

The renderer should assume that filtering may already have occurred.

The renderer is responsible for rendering a projection, not for determining what belongs in it.

---

## Success Criteria

The implementation demonstrates:

* temporal continuity rendering
* consequence-oriented continuity rendering
* corridor construction
* lane allocation
* explicit node markers
* preservation of continuity
* maximal label space within projection constraints

The renderings above are the primary reference artifacts.

The implementation should explain them rather than merely reproduce them.

---

## Progress

- Renamed this task file to use the standard `.md` suffix.
- Re-enabled the temporal and consequence renderer snapshot tests that had been skipped while the renderer was in progress.
- Reworked the renderer around projection order, corridor/lane assignment, explicit connector rows, and node-marker-aware gutter rendering.
- Moved the canonical A/A1/A2/A3 examples into durable-message-shaped test fixtures so the reference renderings are exercised through the same adapter path as real events.
- Added `graph_from_message_events(...)` and `graph_from_events_jsonl(...)` as the first bridge from `.toas/events.jsonl` forests into the renderer, preserving durable root order and ignoring non-message records (`run`, `tool_request`, `tool_result`, `llm_call`, etc.).
- Extended rendering to handle forests with multiple roots while preserving the single-root snapshot output.
- Validation:
  - `uv run pytest tests/test_event_graph.py::TestCanonicalGraphRenderers::test_temporal_projection -q --no-cov`
  - `uv run pytest tests/test_event_graph.py::TestCanonicalGraphRenderers::test_consequence_projection -q --no-cov`
  - `uv run pytest tests/test_event_graph.py -q --no-cov` (`9 passed`)
  - `uv run ruff check src/toas/tools_cluster/event_graph.py tests/test_event_graph.py`
  - `uv run mypy src/toas/tools_cluster/event_graph.py`
  - `./.codex-local/bin/uvt run pytest tests/test_cli_smoke.py -q --no-cov` (`4 passed`) confirmed the earlier `No module named toas` smoke failures were plain environment setup.
  - `./.codex-local/bin/uvt run pytest` was attempted; `tests/test_event_graph.py` passed in the full run, and the environment-related stdio/import failures cleared, but the suite still has an unrelated daemon stream assertion failure in `tests/test_daemon_async_runner.py::test_stream_process_output_emits_explicit_tool_progress_for_result_marker` plus the resulting coverage gate.
  - `./.codex-local/bin/uvt run pytest tests/test_event_graph.py -q --no-cov` (`13 passed`) after the real-event adapter/forest pass.
  - `./.codex-local/bin/uvt run python ... graph_from_events_jsonl(Path(".toas/events.jsonl"))` confirmed the live repo event log ingests as a one-root forest rooted at `n0`.

---

## Follow-up

- `667` tracks the first non-Python entry points: `toas graph` and `/graph`, with deterministic real-event labels and explicit projection selection.

---

## Final Status

Closed after landing the renderer foundation: canonical snapshots are active, durable-message-shaped examples back the tests, real event-log adapters exist, forest rendering supports multiple roots, and follow-up `667` tracks non-Python CLI/operator entry points.
