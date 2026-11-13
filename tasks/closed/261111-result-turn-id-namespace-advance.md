Filed as: 261111-result-turn-id-namespace-advance
FKA:
AKA: user-content turn not branched on edit; appended result reuses original turn handle
Legacy index:

keywords: historical, turn-namespace, reconciliation, tool-result, user-shell, nato, turn-id, branching, defect
Depends on:
Related: `261109-tool-result-decorations-elapsed-time` (result decoration/projection family)

# Edited user-content turn is not materialized as a branched new node

Status: CLOSED 2026-11-13; edited user turns branch from their prior parent and result attribution uses the fresh handle

## Objective

When a user turn that already carries `## RESULT` content is re-saved with
*added* user content, the reconciliation path must materialize the change as
a **new user node in `events.jsonl`, branched from the parent of the
original node**, with a **fresh turn identity**. Today it instead matches the
user turn by position/identity and carries the original handle forward, so
the result under the added content inherits the original (now-stale) handle
rather than the new node's.

## Why this is the right model (operator formulation, confirmed)

A `## RESULT` block is **user content**: it lives inside the `## TOAS:USER`
turn, below the user's own text. Therefore appending to a user turn that
already has a result under it is an *edit of prior transcript-aligned
content*, which per the repo invariants means **branching, not undo**, and
must **never mutate the prior node**:

- The original node (user text + its `write_file` result) keeps its allocated
  handle (`romeo-2`) and is untouched.
- The re-saved content (original content **plus** the new line) is a *branch*
  from the original node's parent, i.e. a **new user node**, so it gets a
  **new numbered identity** (which *might* coincidentally equal the original,
  but the reason the content changed is precisely that the user edited it,
  turning it into an allocated user-content node -- so it should advance,
  e.g. `romeo-2` -> `sierra-2`).
- The `## RESULT` produced under the *new* node must point at the *new*
  node's handle, not the original's.

This also explains the masking: an *intervening* separate `## TOAS:USER`
message is a genuinely new node and gets a fresh allocation, which is the
behavior the append case *should* have received but did not.

## Defect (observed)

A single durable user turn was edited across steps:

Initial transcript content of the user turn:
    ## TOAS:USER

    ## RESULT [romeo-2.p1.o1 OK write_file 38.5k]

    [OK] write_file (...): wrote 3660 bytes

The operator then appended to the SAME user turn:
    ... (same as above) ...

    $ jj st

Result projected for the appended `$ jj st`:
    ## RESULT [romeo-2.p1.o1 OK shell 43.9k]   <- should have been sierra-2.p1.o1

The appended command's result inherited the original node's handle
(`romeo-2`) because the reconciliation treated the edited turn as the *same*
node rather than branching a new node with a fresh allocation.

## Root Cause / Seam (confirmed)

The reconciliation that decides "same node vs. branched new node" is
`src/toas/runtime/step_runtime.py` -> `_build_new_transcript_nodes` and
`_working_with_transcript_tail_frontier` (invoked from
`_build_run_step_frontier_context`, ~L1500). The reproduced slips:

- On a user-turn content change, the LCP/divergence reconciliation matches
  the user turn by position/identity (or by a prefix that still matches the
  original) and carries the ORIGINAL node's allocated handle forward,
  instead of detecting the divergence and branching a new node from the
  original node's parent with a fresh turn allocation.

The result decorator (`step_runtime.py` ~L1780-1803,
`format_result_hierarchical_id(parent_handle, plan_index, op_index)`) is
downstream and correct given its input; the stale `parent_handle` it
receives is a symptom of the reconciliation, not a defect in the decorator.
Fix the reconciliation, not the decorator.

Additionally, `extract_human_user_content` filtered a recognized `[OK]` result
line without marking the result's first line as consumed. The following actual
user command was then mistaken for the result's single-line payload and omitted
from human-turn detection.

## Verification questions (resolved)

(a) The re-saved turn produces a new message event, branched from its
    predecessor's parent.
(b) The new node receives a fresh turn allocation, and its result uses that
    handle.
(c) The original node's handle and content remain unchanged.

## Scope

- Make user-turn content edits (especially appending content under an
  existing `## RESULT`) reconcile as a **branched new node** from the
  original node's parent, with a **fresh turn identity**, per the
  branch-on-edit invariant.
- Keep the fix in the reconciliation/allocation seam
  (`_build_new_transcript_nodes` / `_working_with_transcript_tail_frontier` /
  turn allocation), not a projection-time string patch and not the result
  decorator.
- Preserve the `p1.o1` (plan_index/op_index) semantics.
- Respect the invariants: never mutate prior history entries; editing prior
  transcript-aligned content means branching; adjacent user messages
  concatenate only at model-input projection time (so the durable transcript
  keeps them distinct).
- Keep the user-shell shorthand (direct user intent) distinct from the
  model-addressable `shell` tool even though they share result shapes.

## Verification

- `uv run pytest` green; `./scripts/check.sh` green; 100.00% statement
  coverage on the touched reconciliation/allocation path.
- Operator-perspective end-to-end (mandatory, transcript/durable surface):
  - Drive the two-state transcript (user turn + result, then same turn
    re-saved with added content) through `toas step`.
  - Inspect `events.jsonl`: the edited turn is a NEW branch node (not an
    in-place mutation); the original node is unchanged; the new node has a
    FRESH turn identity; the result under the new content carries the new
    handle (e.g. `sierra-2.p1.o1`).
  - Confirm `toas transcript` / `toas llm-input` project the branched node
    and its fresh handle consistently, and that adjacent user messages are
    still concatenated only at model-input projection time.
- Test the public step/transcript seam (a real two-state transcript through
  `toas step` / the operator API), not private `_` helpers.

## Resolution and Evidence

- `extract_human_user_content` now treats a recognized result status line as
  the result payload line, so later user-authored content remains visible to
  turn detection.
- Frontier selection keeps the reconciled, newly materialized user node when
  it matches the transcript tail. Matched or unchanged tails still use the
  transcript-parsed tail object.
- A public `run_step` regression test confirms the edited user turn branches
  from the previous node's parent, receives a fresh handle, keeps the old
  history unchanged, and gives the `$ pwd` result the new hierarchical handle.
- A real CLI run confirmed `events.jsonl` retained original node `n2`, wrote
  edited node `n3` parented to `n1`, and related the `tool_result` to `n3`.
  `toas step` displayed `bravo.p1.o1`; `toas transcript` displayed the new
  user-turn handle; `toas llm-input` included the edited `$ pwd` content.
- Full suite: 4,095 passed, 9 skipped, 17 deselected with 100.00% statement
  coverage; acceptance suite: 17 passed. Ruff and mypy passed.
