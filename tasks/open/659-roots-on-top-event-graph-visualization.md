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

## Follow-up

- `667` tracks the first non-Python entry points: `toas graph` and `/graph`, with deterministic real-event labels and explicit projection selection.
