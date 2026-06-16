Filed as: 260615-force-structure-alignment-survey
FKA:
AKA: architecture force survey; alignment survey; least-aligned surface inventory
Legacy index:

keywords: docs, investigation, inception, architecture, alignment, survey, boundaries, maintainability

# Force Structure Alignment Survey

## Current Reality

The architecture work has named the main forces: durable state, transcript
reconciliation, operator semantics, activity lifecycle, session host
supervision, effective policy and authority, model invocation, model backend
lifecycle, transport/protocol, surface adapters, and projection/rendering.

Individual tasks now cover several seams, but there is no broad survey task
that periodically asks which current code, docs, names, adapters, or task
claims are least aligned with that force structure.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

TOAS should have an explicit alignment survey pass that inventories the most
force-misaligned current surfaces and converts them into bounded future work.

The survey should rank friction by how much it distorts current understanding
or blocks future alignment, not by how tempting a new feature might be.

## Alignment Target

This is a survey and triage task. It should not implement fixes directly.

The output should be a short inventory of misalignments, each classified as:

- naming mismatch
- ownership mismatch
- adapter/domain confusion
- legacy transition debt
- documentation fiction
- package/module placement pressure
- parked feature idea that should stay parked

## Known Facts

- `260615-runtime-package-growth-boundary-audit` covers the narrower
  `runtime/` module-to-domain map.
- `260614-legacy-and-fidelity-adapter-precedence` covers legacy and
  fidelity-lowering adapter vocabulary.
- Several current tasks were born from finding fiction in architecture wording,
  especially around backend lifecycle and activity replay.

## Unknowns

- Which current surfaces are most misleading relative to the force map.
- Whether the highest-value next work is naming, documentation, module
  placement, or tests.
- How much of the remaining mismatch is historical text versus live code shape.

## Evidence

Ready to leave inception when:

- a first alignment inventory exists
- each entry names the distorted force and current evidence
- follow-ups are split only where they are bounded alignment work
- speculative feature ideas are marked as parked instead of promoted
