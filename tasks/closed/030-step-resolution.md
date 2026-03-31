## Goal

Implement the core `step` operator as alignment plus single-layer frontier resolution.

## Scope

- Create `step.py`
- Implement:
  - alignment of transcript nodes against log nodes
  - frontier inspection
  - one-step advancement

Suggested shape:

- `step(transcript: str, log: list[Node], ...) -> (append_set, stdout_set)`

## Algorithm

1. Parse transcript into nodes
2. Compare transcript nodes with log nodes linearly
3. Find longest common prefix using byte-level identity
4. Treat everything after that as accepted transcript divergence
5. Inspect the resulting frontier for unresolved state
6. Produce exactly one layer of consequence
7. Return:
   - everything to append to history
   - only newly produced consequences for stdout

## Resolution Rules

- NOT callable + user -> generate assistant
- NOT callable + assistant -> no-op
- CALLABLE + assistant -> execute and emit RESULT
- CALLABLE + user -> execute and emit RESULT

Refinements:

- execution is role-agnostic
- generation is role-driven
- execution does not trigger generation
- control returns to the transcript author after execution

## Simplifications

- Ignore `parent` initially (assume linear)
- Ignore full branching semantics for now
- `jump` may remain a separate manual override path
- Callable detection can be minimal as long as the boundary is explicit

## Output

- Return append-set separately from stdout-set
- Append-set includes accepted transcript divergence plus newly produced consequences
- Stdout-set includes only newly produced consequences

## Done When

- Editing transcript causes new nodes to append
- No duplication when rerunning unchanged transcript
- User-tail non-callable transcripts can generate one assistant consequence
- Callable tails can execute one result consequence without auto-continuation
