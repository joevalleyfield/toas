Filed as: 488-multi-operator-orchestration-exploration
FKA: 488-multi-operator-orchestration-exploration
AKA: multi-operator; toas-in-toas; multiplayer
Legacy index: 488

keywords: surface, exploration, parked, research, orchestration, operator-driver, working-memory, waypoint, drift

# Operator/Driver Working-Memory Exploration

Evaluate how TOAS can support an operator/driver relationship in which a human
or Codex holds the larger intent and trajectory, while TOAS and its configured
LLM handle short-horizon transcript progression and tool use. Treat broader
multi-operator orchestration as a possible follow-on, not as the immediate
center of the work.

## Why
An operator does not reread the whole transcript at every step. They retain a
working sense of intent, completed work, trajectory, uncertainty, and likely
next action. A compact, eloquent projection could reduce context cost for both
human operators and configured drivers, but correlated summaries can also hide
drift. The exploration should therefore separate useful compression from
independent evidence-grounded judgment without destabilizing core acceptance
closure.

## Scope
In scope:
- evaluate an operator/driver working-memory projection (for example, a
  `step memory` or `waypoint`) containing intent, completed work, trajectory,
  frontier state, likely next action, open questions, risks, and source refs
- distinguish three layers:
  - driver-generated trajectory: what should happen next
  - evidence-grounded state: what durable facts support
    (or fail to support) that trajectory
  - operator sanity check: whether the trajectory still seems right
- evaluate candidate orchestration shapes as secondary extensions, including
  TOAS-in-TOAS, child proposal branches, parallel task lanes, and checkpoint
  handoff
- define source-linking, uncertainty, staleness, and operator-ownership
  constraints for compact projections
- define success criteria and failure modes
- run at least one bounded experiment with explicit artifacts; the experiment
  may use an ordinary repository task, a replayed transcript, or a synthetic
  transcript derived from real TOAS records

Out of scope:
- making orchestration a prerequisite for 469 closure
- broad productionization of multi-agent runtime semantics
- treating a generated summary as canonical state or as an independent vote
- requiring a purpose-built drift benchmark before the exploration can begin

## Deliverables
- short design note with operator/driver working-memory model, candidate views,
  orchestration extensions, and tradeoffs
- one compact, source-linked step-memory or waypoint specimen
- one independent evidence-audit or trajectory-challenge specimen
- one bounded replay or live experiment with explicit artifacts
- experiment notes covering where compression helped, where eloquence obscured
  uncertainty, and where source expansion recovered an error
- recommendation: adopt, defer, or split additional tasks

## Done When
- the operator/driver relationship and transcript authority boundary are
  documented explicitly
- working-memory projections are documented as projections of durable state,
  not replacements for transcript or graph truth
- trajectory proposals are distinguished from evidence-grounded state; the
  evidence view is not merely a second correlated summary
- orchestration options are documented with explicit constraints
- at least one ordinary or replayed repository workflow is evaluated in both
  unperturbed and deliberately perturbed forms
- perturbations include enough variety to test at least some of: wrong-scope
  edits, premature completion, unexplained file changes, repeated no-progress
  steps, unsupported success claims, or trajectory/evidence conflict
- the experiment includes an independent larger-context reconstruction,
  evaluator, or equivalent evidence-grounded judgment
- the artifacts record token/context cost, progress, recovery quality, drift
  detection, evidence traceability, operator confidence, and false alarms
- next-step recommendation is recorded

## Working Model

The proposed operating loop is:

```text
operator intent and trajectory
          ↓
TOAS-owned transcript and one-step resolution
          ↓
configured LLM short-horizon driving
          ↓
durable facts and compact step result
          ↓
operator working-memory projection and sanity check
```

The useful projection may be eloquent prose or structured text, but important
claims should remain expandable to durable source records. Computed facts,
interpreted trajectory, and operator intent should not be conflated. Only
accepted operator-owned intent may redirect execution.

## Bounded Experiment Guidance

The experiment need not begin with a known drift-bound task. Select an ordinary
repository workflow or replay an existing TOAS transcript, then perturb the
projection, trajectory claim, or evidence visibility at controlled checkpoints.
Compare, where practical:

- full transcript context
- existing compaction/lens projection
- step memory plus frontier-local evidence
- step memory plus an independent evidence audit

The experiment should ask whether the operator-facing affordances expose a
problem, not merely whether two summaries agree. Deliberately correlated
summaries do not count as independent confirmation.

Potential future affordances to evaluate include:

```text
toas step
toas step-memory
toas check-trajectory
toas step-memory --expand <source-ref>
```

These names are exploratory. The experiment should establish the contract and
ownership boundary before productionizing a command surface.

## Related
- First slice design note: `docs/notes/2026-08-10-operator-driver-working-memory-design.md`
- 469 functional acceptance epic: `closed/260502-functional-acceptance-epic-complete-change-request-on-a-repository.md`
- 470 operator API seam migration: `closed/260502-operator-api-seam-and-cli-thin-wrapper-migration-for-acceptance-e2e.md`
- 487 operator spike cadence and scorecard: `closed/260509-operator-spike-cadence-and-scorecard.md`
