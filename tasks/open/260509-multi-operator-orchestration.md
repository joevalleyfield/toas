Filed as: 488-multi-operator-orchestration-exploration
FKA: 488-multi-operator-orchestration-exploration
AKA: multi-operator; toas-in-toas; multiplayer
Legacy index: 488

keywords: surface, exploration, parked, research, orchestration, multiplayer

# Multi-Operator Orchestration Exploration

Evaluate higher-level orchestration patterns (including TOAS-in-TOAS or multi-agent collaboration) as a follow-on capability, separate from base single-operator acceptance proof.

## Why
There is clear interest in reducing single-operator cognitive overhead by introducing structured high-level delegation/orchestration. This should be explored deliberately without destabilizing core acceptance closure.

## Scope
In scope:
- evaluate candidate orchestration shapes (single supervisor + worker transcripts, parallel task lanes, checkpoint handoff model)
- define success criteria and failure modes
- run at least one bounded experiment with explicit artifacts

Out of scope:
- making orchestration a prerequisite for 469 closure
- broad productionization of multi-agent runtime semantics

## Deliverables
- short design note with candidate models + tradeoffs
- one bounded experiment artifact
- recommendation: adopt, defer, or split additional tasks

## Done When
- orchestration options are documented with explicit constraints
- at least one bounded experiment is completed
- next-step recommendation is recorded

## Related
- 469 functional acceptance epic: `closed/260502-functional-acceptance-epic-complete-change-request-on-a-repository.md`
- 470 operator API seam migration: `closed/260502-operator-api-seam-and-cli-thin-wrapper-migration-for-acceptance-e2e.md`
- 487 operator spike cadence and scorecard: `closed/260509-operator-spike-cadence-and-scorecard.md`
