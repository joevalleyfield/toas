# 486 Runbook vs Acceptance Boundary Cleanup

## Objective
Separate operator runbook/process guidance from executable acceptance proof artifacts so task 469 can close on acceptance outcomes without absorbing process-evolution scope.

## Why
Current 469 context mixes two concerns:
- acceptance proof that TOAS can complete bounded repo change requests end-to-end
- evolving runbook guidance for interactive operator probing

This conflation makes DoD ambiguous and keeps 469 open for work that should be tracked separately.

## Scope
In scope:
- define explicit artifact boundary between acceptance assets and runbook/probing assets
- update references in 469 docs/tasking so closure criteria only depend on acceptance-proof surfaces
- document where runbook/probing updates should land going forward

Out of scope:
- redesigning acceptance scenarios themselves
- adding new runtime behavior changes

## Deliverables
- boundary note/update in acceptance docs referencing where each artifact type belongs
- 469 task updates removing process-doc obligations from exit criteria
- roadmap/task linkage updated to point process evolution at follow-on tasks instead of 469

## Done When
- [x] 469 no longer implicitly depends on runbook/process iteration to close
- [x] runbook/probing artifacts have explicit ownership and destination
- [x] references are coherent across tasks/roadmap

## Status
Complete (2026-05-09).

Boundary is now explicit:
- acceptance proof artifacts and executable checks remain under `docs/acceptance/*` + `tests/acceptance/*`
- process/runbook and probing cadence are tracked through `docs/acceptance/spikes/*` with task ownership in `487`
- roadmap/469 references now treat this split as a maintained contract

## Related
- 469 functional acceptance epic
- 470 operator API seam migration
- 487 operator spike cadence and scorecard
