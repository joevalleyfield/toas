## Goal

Basic append-only interaction with `events.jsonl` as durable history.

## Scope

- Create `graph.py`
- Implement:
  - `read_log(path) -> list[Node]`
  - `append_nodes(path, nodes)`

## Shape

Node:
- parent: optional[int]
- role: str
- content: str

## Rules

- One JSON object per line
- Line number = physical identity
- Do not mutate existing lines
- Log is history, not a projection target
- Appends may include accepted transcript nodes and produced consequences
- Future non-causal entries such as anchors must still preserve append-only behavior

## Non-Goals

- No indexing
- No branch selection logic yet
- No id handling yet
- No validation beyond JSON parse

## Done When

- Can append nodes and read them back without restating or rewriting prior history
