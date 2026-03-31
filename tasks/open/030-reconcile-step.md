
## Goal

Implement the core `step` operator.

## Scope

- Create `reconcile.py`
- Implement:
  - `reconcile(transcript_msgs, log_nodes) -> list[Node]`

## Algorithm (first pass)

1. Compare transcript messages with log nodes linearly
2. Find longest common prefix
3. Everything after that = divergence
4. Return nodes to append

## Simplifications

- Ignore `parent` initially (assume linear)
- Ignore branching semantics for now
- No rewind handling yet (just append)

## Output

- Only return *new* nodes
- CLI will:
  - append them to log
  - print them to stdout

## Done When

- Editing transcript causes new nodes to append
- No duplication when rerunning unchanged transcript
