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

Make locally available models dependable in actual operator workflows. The
integrated state-shaped alpha, branch-local policy reducers, and endpoint/model
setup surfaces provide a working base. Current pressure is response and state
quality, inspectable effective policy, faithful execution/recovery, and editor
behavior across the environments operators use.

Durable history and runtime ownership remain foundations. Segmented storage,
source-selection parity, and fatal-corruption refusal have landed; they should
not keep driving a broad proof program after their concrete requirements are
satisfied. Reopen history work through an observed affordance or recovery gap.

## Next

Prefer this sequencing shape:

1. Reconcile remaining scope in partially implemented programs before adding
   more implementation or new tasks.
2. Select a bounded operator-facing slice from real model, policy-inspection,
   execution, or editor evidence, with a concrete artifact to inspect.
3. Keep routine checks and platform verification reproducible; distinguish
   tested environments from historical reports and untested variants.
4. Pursue broader parallelism, provenance, or frontend research when one
   consumer and ownership boundary are concrete enough to evaluate.
5. Keep release review and planning hygiene lightweight recurring operation.

The workboard owns current candidate tasks and sequencing. This direction does
not promote every open research idea into an implementation commitment.

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
