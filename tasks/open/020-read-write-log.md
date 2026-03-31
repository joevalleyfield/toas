
## Goal

Basic append-only interaction with `events.jsonl`.

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

## Non-Goals

- No indexing
- No id handling yet
- No validation beyond JSON parse

## Done When

- Can append nodes and read them back
