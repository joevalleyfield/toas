## Goal

Expand the first inference-path integration from packet construction+gating to explicit packet shaping that materially influences generation input structure.

## Why Now

Current seam computes packet data and quality checks, but model input remains mostly transcript-projected; this limits the practical payoff of context assembly.

## Scope

- define and implement explicit packet shaping rules for generation request preparation
- include ordered sections such as:
  - goal cue
  - lens distillations
  - minimal evidence references/snippets
  - constraints/policy reminders
- preserve deterministic ordering and stable fallback behavior
- add parity tests for unchanged baseline when no artifacts are active

## Intended Behavior

- packet assembly has visible, controlled influence on generation inputs
- shaping remains deterministic and debuggable
- inactive/no-artifact flows preserve current behavior expectations

## Constraints

- avoid semantic drift that breaks existing prompt/runtime contracts
- keep token growth bounded and observable
- maintain append-only durable history and reversible derivations

## Done When

- generation request preparation uses shaped packet content when artifacts exist
- no-artifact path parity is test-covered
- shaping behavior is documented with examples and tradeoffs

## Progress

- 2026-04-26: Landed first shaping slice:
  - added packet-to-message shaping helper (`shape_messages_for_packet`) that prepends a deterministic system packet summary when lens artifacts exist.
  - wired `GenerationRunner.prepare_request` to use shaped packet messages instead of raw projected messages when artifacts are active.
  - preserved no-artifact parity (returns original projected message sequence unchanged).
  - added module-level and runner-level regressions for artifact-shaped inputs and parity behavior.
- 2026-04-26: Landed shaping expansion slice:
  - expanded packet shaping into explicit ordered sections (`goal_cue`, `lens_distillations`, `evidence_refs`, `constraints`, `packet_limits`) so generation input influence is concrete and auditable.
  - added lightweight evidence snippets derived from source-pointer message IDs and threaded them into shaped packet rendering.
  - added deterministic size controls (artifact cap, distillation clipping, evidence-ref cap) with truncation signaling to keep growth bounded.
  - added regressions for section rendering and bounded-size/truncation behavior.
