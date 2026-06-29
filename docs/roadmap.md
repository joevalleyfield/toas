# TOAS Roadmap

## Purpose

This roadmap is a high-level direction document, not a task ledger.

Use it to answer:
- what strategic concerns are active
- what order of pressure matters most
- where durable product/architecture intent lives

Do not use it to thread routine task openings, closures, or focus changes.
Task files and generated sections of `tasks/WORKBOARD.md` own that operational
state. The manually curated roadmap and workboard sections should be visited
periodically for drift, not updated by reflex on every task movement.

Current capability shape belongs in `docs/capabilities.md`.
Doc intent/status guardrails (CURRENT vs DIRECTIONAL vs DRAFT) are defined in
`docs/notes/2026-05-16-doc-truth-model.md`.

Execution policy from the closed runtime ownership arc (`525`):
- capability-first sequencing: land happy-path capability first
- add restrictions/guardrails only when backed by concrete failure evidence or
  cross-platform/data-integrity risk

## Now

The highest-level pressure is still architecture follow-through: keep the
primary runtime path local, durable, and transcript-oriented while hardening the
history substrate that operators now depend on.

Near-term implementation should favor:
- segmented history/storage proof and parity hardening
- history-surface clarity, especially recovery and user-intent alignment
- release and routine-check discipline that supports local-first development
- narrow implementation slices opened from concrete evidence, not broad
  decomposition umbrellas

Acceptance, weak-model protocol reliability, cross-platform tool behavior, and
frontend/orchestration exploration remain important, but they should not crowd
out the current history/runtime spine unless fresh evidence changes the order.

## Next

Prefer this sequencing shape:

1. Finish the active history/storage proof chain.
2. Make healthy and corrupt history surfaces clearer for operators.
3. Keep release/routine verification lightweight but reproducible.
4. Open focused follow-ons only when a failure mode, domain boundary, or
   operator friction is concrete enough to test.
5. Use recurring maintenance runs to prune planning/help drift instead of
   reopening broad umbrellas.

## Durable Concerns

### History Substrate And Recovery

TOAS needs durable history to be both reliable substrate and usable operator
surface. Healthy-history views should answer distinct questions clearly, while
corrupt-history refusal should point toward safe recovery actions.

### Runtime Ownership

Primary execution semantics belong in runtime/operator code, with daemon/RPC
and Vim channels treated as transport adapters. Transport choices should not
fork meaning.

### Acceptance-Proven Operation

TOAS should preserve a reproducible path from operator intent to validated
change, including durable history, transcript projection, and bounded repair
semantics.

### Protocol Reliability For Weaker Models

Prompt/template composition, callable lanes, and edit/tool contracts should
reduce manual coaching for less reliable local models without hiding policy in
runtime side effects.

### Planning Surface Hygiene

`tasks/WORKBOARD.md` is the operational queue. This roadmap carries only
strategic concerns and should be pruned aggressively when it starts mirroring
task inventory.
