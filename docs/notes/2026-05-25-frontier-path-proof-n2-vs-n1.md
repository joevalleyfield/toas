# Frontier Path Proof: `n2` Expected vs `n1` Observed

## Scope

This note proves the exact decision-path for the shortest known lag sequence where the last common parent should be `n2` (`ASSISTANT: B`) but observed divergence parent is `n1` (`USER: A`).

Primary purpose:
- make the seam values explicit before any fix work
- separate expectation proof from implementation hypotheses

## Minimal Two-Step Evolution

### Step 1 transcript (seed)

```md
## TOAS:USER

A

## TOAS:ASSISTANT

B

## TOAS:USER

C
```

Expected durable message lineage after step:
- `n1`: `USER A`
- `n2`: `ASSISTANT B`
- `n3`: `USER C`
- generated assistant consequence (tip advances)

### Step 2 transcript (tail rewrite)

```md
## TOAS:USER

A

## TOAS:ASSISTANT

B

## TOAS:USER

rebuild tail

## RESULT

Z2
```

Interpretation contract (already agreed):
- `## RESULT` is inline content in a user turn, not a structural boundary class.
- Shared transcript prefix across step-1/step-2 is:
  - `USER A`
  - `ASSISTANT B`
- Therefore LCP boundary parent should be `n2`.

## Decision Path (Observed)

From interaction harness traces around `run_step_local -> step_runtime._build_new_transcript_nodes`:

1. `head_id = active_head_id(events)`
2. `lineage = message_lineage(events, head_id=head_id)`
3. `bind_index = active_bind_index(events)` (none in this flow)
4. `bind_parent = active tip in selected lineage` (observed `n3` for second step pre-rewrite context)
5. `anchor_index = alignment_anchor_index(...)` (observed `0`)
6. Runtime computes:
   - `bound_log = log[bind_index:]` (full lineage when bind unset)
   - `i = anchor_index + lcp(nodes[anchor_index:], bound_log[anchor_index:])`
7. For second step in failing flow:
   - observed `i = 2`
   - expected boundary id at `bound_lineage[i-1]` is `n2`
   - observed `divergence_parent = n1`
   - observed `first_new_parent = n1`

## Why This Is Off-By-One

Given `i = 2`, boundary parent selection in message lineage should resolve to index `1` (0-based), i.e. `n2`.

Observed `n1` corresponds to index `0`, one node earlier than expected for this shared prefix.

So this sequence is a concrete `n2 -> n1` boundary lag.

## Where To Cross-Check In Tests

- Interaction evolution signature:
  - [tests/test_cli.py:4212](/Users/tim/Documents/Projects/toas/tests/test_cli.py:4212)
- Input-shape shortest variant (`single-user-inline-result`):
  - [tests/test_cli.py:4352](/Users/tim/Documents/Projects/toas/tests/test_cli.py:4352)
- End-to-end red guard (still failing by design):
  - [tests/test_cli.py:3805](/Users/tim/Documents/Projects/toas/tests/test_cli.py:3805)

## Status

- Path proof complete for shortest known sequence.
- No runtime fix proposed in this note.
