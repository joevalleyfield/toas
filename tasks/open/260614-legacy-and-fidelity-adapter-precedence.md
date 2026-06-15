Filed as: 260614-compatibility-domain-truth-precedence
FKA: 260614-compatibility-domain-truth-precedence
AKA: envelope legacy precedence; domain truth precedence; compatibility response truth; fidelity lowering adapters; legacy field retirement
Legacy index:

keywords: transport, investigation, inception, architecture, legacy, protocol, envelope, truth, adapter, fidelity

# Legacy And Fidelity-Adapter Precedence

## Current Reality

The architecture says transport envelopes, adapter views, and legacy response
fields carry meaning but must not own semantic truth.

The old task name used `compatibility` as a bucket, but that word hides two
different forces:

- `legacy`: a transition surface retained only until callers are migrated away
  from it
- `fidelity-lowering adapter`: an edge view that adapts a full-fidelity
  internal stream/result to a real interface limitation

Those should not be treated the same. Legacy should shrink. Fidelity-lowering
adapters may remain, but they must be explicitly edge-owned and must not reduce
internal stream fidelity.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

For each legacy or fidelity-lowering surface, TOAS should know which layer wins
when domain result, full-fidelity stream event, envelope payload, adapter view,
and legacy field disagree.

Internal producers should emit the highest-fidelity semantic stream/result they
can. Edge adapters may lower fidelity for real transport/editor/display
constraints, but the lowering must be named, adapter-owned, and visibly derived
from semantic events or domain results.

Legacy fields should be derived from domain results or stream events during the
transition window, then retired as soon as callers no longer need them.

## Inception Note

This task is intentionally inception-only. It should become active when protocol
or adapter work needs to decide a concrete precedence/retirement rule.

## Vocabulary Decision: 2026-06-15

- Use `legacy` for transition surfaces retained only while callers migrate.
- Use `fidelity-lowering adapter` for an edge view that adapts full-fidelity
  internal events/results to a real interface limitation.
- Do not use `compatibility` as an undifferentiated design justification.
- Internal streams should retain full semantic fidelity until an explicit edge
  adapter lowers them.
- Legacy fields and fidelity-lowering views must be derived from domain results
  or stream events; they must not redefine semantic truth.

## Known Facts

- `676` tracks optional stronger transport equivalence certification.
- Backend command adapters now consume lifecycle domain results.
- CLI rendering may prefer envelope payload status/detail in some paths.
- Runtime streams already carry lane/phase-scoped events that are higher
  fidelity than legacy `chunk` fields.
- Stdio/Vim surfaces may need bounded or projected views, but those are edge
  limitations rather than semantic truth.

## Unknowns

- Whether this should merge into `676` or remain a separate architecture
  contract task.
- Which protocol surfaces need explicit precedence/retirement tables.
- Whether mismatch diagnostics should be operator-visible, test-only, or both.
- Which current uses of `compatibility` mean legacy transition, and which mean
  legitimate fidelity-lowering adapter.

## Evidence

Ready to leave inception when:

- a protocol/adapter slice exposes conflicting envelope and legacy meanings
- the expected winner and mismatch handling can be stated per operation
- a vocabulary pass can replace fuzzy `compatibility` wording with `legacy`,
  `adapter`, or `fidelity-lowering view`
- internal full-fidelity stream shape is protected until an explicit edge
  adapter lowers it for a named interface limitation
