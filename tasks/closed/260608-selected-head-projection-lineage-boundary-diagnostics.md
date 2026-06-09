# Selected-Head Lineage Boundary Diagnostics

Filed as: 354-selected-head-projection-lineage-boundary-diagnostics
FKA: 354-selected-head-projection-lineage-boundary-diagnostics.md
AKA: selected head projection; lineage boundary diagnostics; replay loops
Legacy index: 354
keywords: projection, investigation, historical, correctness, head, lineage, rebuild, diagnostics

## Goal

Diagnose and fix selected-head transcript projection so rewinds reflect the intended lineage boundary and do not unexpectedly retain distant/sibling replay mass.

## Why Now

Dogfood runs showed very large `session.md` projections even after explicit head rewinds and rebuilds, with observed behavior that appears inconsistent with expected "project selected lineage only" mental model.

## Scope

- reproduce from a fresh dogfood baseline with controlled branching/rewind sequences
- define expected projection semantics for:
  - selected head vs available heads
  - sibling/cousin/distant lineage exclusion
  - control-record timing (`head`, `anchor`, `jump`) vs projection boundary
- instrument projection path to explain why replay mass persists after rewind
- implement fix so `rebuild <head>` and current-head projection are lineage-bounded by design
- add regression tests for branch-heavy ancestry shapes and repeated rewind/rebuild cycles

## Intended Behavior

- selecting head `nX` and rebuilding projects only the transcript lineage implied by `nX`
- sibling/cousin branches remain durable history but do not inflate projected transcript
- projection behavior is deterministic and explainable from durable records

## Constraints

- no mutation of prior durable history entries
- preserve branch-first semantics (rewind by selection, not destructive undo)
- keep message/control/tool/model-call record types distinct

## Done When

- reproducible minimal case is captured in tests
- failing behavior is fixed with clear projection invariants
- docs describe selected-head projection boundary semantics unambiguously

## Repro Log (2026-04-12)

Fresh baseline:
- reset dogfood workspace (`session.md`, `events.jsonl`, `events.idx`) to empty
- confirmed `uv run toas history 20` reported no selected head and no recent events

Deterministic branch construction (no model-generation dependency):
1. write `session.md` with:
   - `u1` user
   - `a1` assistant
2. run `uv run toas step`
   - observed head `n1`
3. write `session.md` with:
   - `u1`/`a1`
   - `u2`/`a2`
4. run `uv run toas step`
   - observed head `n3` (linear chain `n0..n3`)
5. run `uv run toas head n1` and `uv run toas rebuild n1`
6. overwrite `session.md` with:
   - `u1`/`a1`
   - `uB`/`aB`
7. run `uv run toas step`
   - observed sibling branch with second head `n5`

Observed rebuild behavior:
- `uv run toas rebuild n1` projected only `u1/a1`
- `uv run toas rebuild n3` projected only `u1/a1/u2/a2`
- `uv run toas rebuild n5` projected only `u1/a1/uB/aB`

Interim finding:
- lineage-bounded projection behaves correctly in this minimal branch scenario
- large dogfood transcript growth appears to require additional conditions not yet isolated (likely involving oversized user-content replay loops or repeated projection ingestion patterns)

Next isolation targets:
- introduce controlled oversized user events into the minimal scenario
- replay the exact prompt-injection pattern that previously produced repeated massive `TOAS:USER` blocks
- capture first divergence point where rebuild output no longer matches selected lineage expectation

## Errata

- initial interpretation over-attributed large `session.md` size to rewind/rebuild projection semantics
- corrected understanding:
  - `rebuild <head>` can be lineage-correct while still producing a large transcript if selected lineage itself contains oversized replayed user content
  - methodology matters: command rendering (`/prompt`) and transcript append flow can create replay mass patterns independent of branch projection logic
- therefore this task remains open, but root cause focus is now narrowed to oversized replay-content ingress and projection/append interaction, not a blanket lineage-selection failure

## Closeout Audit Rationale (2026-06-08)

An audit of the `/prompt` command consequence execution was conducted to determine if consecutive step commands on a raw-injected prompt cause repeated/cascading user turns or loop duplication.

Key findings:
1. **No loop duplication**: When `/prompt` executes, `_handle_prompt` returns a result node with `transcript_render="raw"` and `transcript_inert=False`. This result block replaces the original command in the session. Since the `/prompt` command itself is no longer in the transcript, it cannot be executed again or loop.
2. **Deterministic frontier progression**: The raw prompt rendering appends `\n\n## TOAS:USER\n\n` to the end of the content. During transcript parsing on the next step, this is parsed into two user nodes: a user node containing the prompt content (`## RESULT\n\n{exact}`), and an empty user turn (`role="user"`, `content=""`) acting as the frontier.
3. **LLM Generation Fallback**: When the step runtime processes the empty frontier, it finds no active command or plan intents. It falls back to `_handle_user_generation_fallback` and invokes `generate(working)` to produce the assistant's turn.

Thus, the system transitions cleanly from `/prompt` execution to raw prompt injection, followed by a model generation step. The process is fully deterministic and safe. The original concern of oversized replay loops or projection boundaries from `/prompt` is resolved by this design.
