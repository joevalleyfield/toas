Filed as: 260614-compatibility-domain-truth-precedence
FKA:
AKA: envelope legacy precedence; domain truth precedence; compatibility response truth
Legacy index:

keywords: transport, investigation, inception, architecture, compatibility, protocol, envelope, truth

# Compatibility And Domain-Truth Precedence

## Current Reality

The architecture says transport envelopes and legacy response fields carry
meaning but must not own semantic truth.

Some consumers already prefer envelope payloads for display, while domain
objects produce result shapes that adapters serialize into compatibility fields.
The general precedence rule is not yet consolidated.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

For each compatibility surface, TOAS should know which layer wins when domain
result, envelope payload, and legacy fields disagree.

Compatibility adapters should derive legacy fields from domain results, not let
legacy response shape redefine domain meaning.

## Inception Note

This task is intentionally inception-only. It should become active when protocol
or adapter work needs to decide a concrete precedence rule.

## Known Facts

- `676` tracks optional stronger transport equivalence certification.
- Backend command adapters now consume lifecycle domain results.
- CLI rendering may prefer envelope payload status/detail in some paths.

## Unknowns

- Whether this should merge into `676` or remain a separate architecture
  contract task.
- Which protocol surfaces need explicit precedence tables.
- Whether mismatch diagnostics should be operator-visible, test-only, or both.

## Evidence

Ready to leave inception when:

- a protocol/adapter slice exposes conflicting envelope and legacy meanings
- the expected winner and mismatch handling can be stated per operation
