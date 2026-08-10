# Operator/Driver Working Memory

Status: DRAFT
Task Link: `488-multi-operator-orchestration-exploration`

## Purpose

Explore a compact working-memory projection for repeated TOAS steps. The
operator—human or Codex—holds the larger intent and trajectory. TOAS owns the
working transcript and resolves one consequence at a time. The configured LLM
handles short-horizon driving and tool use.

The projection should reduce rereading without pretending that compression is
independent judgment or canonical state.

## Operating Model

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

The projection is a waypoint between steps. It is not a second transcript and
does not replace `session.md` or `events.jsonl`.

## Proposed Contract

A waypoint contains these semantic fields:

```yaml
intent: <accepted larger objective>
completed:
  - <durable, completed fact>
trajectory:
  - <interpreted direction or plan>
frontier:
  state: <unresolved|callable|awaiting-operator|blocked|complete>
  message_id: <frontier message reference>
  likely_action: <next consequence, if one is justified>
attention:
  - <open question, risk, contradiction, or unexplained change>
evidence:
  - ref: <message/tool/test/file fact reference>
    claim: <what the reference supports>
uncertainty:
  - <claim that remains provisional>
```

The exact serialization is deliberately unresolved. The semantic distinction
is more important than whether the first surface is YAML, prose, or a result
node.

## Three Different Views

The same underlying facts may produce different views:

### Operator view

Optimized for orientation and intervention:

```text
Intent: preserve legacy parser behavior while fixing escaped delimiters.

Done:
- located the failing tokenizer branch
- added a regression fixture
- applied a parser patch

Trajectory:
- run focused tests
- inspect the compatibility failure

Attention:
- the adapter layer also changed, but no evidence explains why

Frontier: callable; run focused parser tests.
Evidence: n184, n191, tr42.
```

### Driver view

Optimized for immediate continuation:

```text
Objective: preserve legacy parser behavior while fixing escaped delimiters.
Current frontier: callable, message n194.
Relevant constraints: do not broaden adapter behavior without evidence.
Confirmed facts: fixture added; parser patch applied; 14 tests pass.
Next justified action: run the focused parser tests.
If they fail: inspect compatibility behavior before editing again.
```

### Evidence-audit view

Optimized for challenging the trajectory rather than restating it:

```text
Supported: parser patch addresses the recorded escaped-delimiter failure.
Unsupported: adapter change is not explained by the cited evidence.
Missing confirmation: focused tests have not yet run after the patch.
Drift signal: trajectory may be broader than the stated objective.
```

The driver trajectory and evidence audit must not be treated as two independent
votes when both were generated from the same compressed context.

## Authority And Provenance

- `session.md` remains the operator-controlled working surface.
- `events.jsonl` remains canonical durable history.
- A waypoint is a projection with source references, not a replacement for
  either surface.
- Computed facts, interpreted trajectory, and operator intent must remain
  distinguishable.
- A driver may propose trajectory; only accepted operator-owned intent may
  redirect execution.
- Missing, stale, or conflicting evidence should be visible rather than
  silently repaired by a summary.

If a durable record is eventually introduced, it should be append-only and
lineage-bound, with explicit provenance and proposed/accepted/superseded
status. A mutable hidden sidecar is not the target.

## Candidate Affordances

These names are exploratory rather than an implementation commitment:

```text
toas step
toas step-memory
toas step-memory --expand <source-ref>
toas check-trajectory
```

The first useful result may simply be an additional compact step result from
the existing operator API. New durable record types or command surfaces should
wait until the projection contract has been exercised against real records.

## First Evaluation Slice

Use an ordinary repository workflow or replayed TOAS transcript. No special
drift task is required. At selected checkpoints, compare:

1. full transcript context;
2. existing compaction/lens projection;
3. waypoint plus frontier-local evidence;
4. waypoint plus an independent evidence audit.

Introduce controlled perturbations such as premature completion, wrong-scope
edits, unexplained file changes, repeated no-progress steps, unsupported
success claims, or trajectory/evidence conflict.

The evaluation should record:

- context/token cost;
- whether the next justified action is identified;
- whether injected drift is detected;
- which source references resolve uncertainty;
- false alarms and missed drift;
- whether a larger-context human or independent evaluator reaches a different
  conclusion.

Agreement between two compressed summaries is not sufficient evidence of
correctness. The experiment is successful if it shows where eloquent
compression preserves orientation and where explicit evidence expansion is
needed to recover judgment.

## Worked Specimen: `operator-spike8`

The existing artifact
`docs/acceptance/spikes/transcripts/operator-spike8-events.jsonl` provides a
small real example. The references below are durable message IDs from that
event stream.

At `n43`, the operator asks where `/help config` is implemented, requires
discovery before reading, and forbids edits. At `n44`, the driver proposes two
searches and a code survey. At `n45`, the results report zero matches for the
initial searches and a broad survey of 159 Python files. At `n46`, the driver
narrows the next action to reading specific files and searching the source
tree.

### Operator waypoint

```text
Intent: locate the implementation of `/help config`; do not edit.

Done:
- initial exact/help-oriented searches returned no matches
- broad code survey established the repository scale
- discovery protocol remains satisfied

Trajectory:
- inspect likely CLI, dispatch, registry, and source-search surfaces
- identify the owning implementation before proposing any change

Frontier: callable discovery plan at n46.

Attention:
- zero exact matches do not establish that `/help config` is absent
- the code survey is orientation, not implementation evidence

Evidence: n43, n44, n45, n46.
```

### Driver view

```text
Do not edit. Read `src/toas/cli.py`, `src/toas/cli_dispatch.py`,
`src/toas/tools.py`, then search `src/toas/` for help handling. Report the
implementation owner and keep the result grounded in file evidence.
```

### Evidence audit

```text
Supported: the operator's discovery-first constraint is explicit; the first
searches found no literal matches; the next plan names concrete files.

Not yet supported: where `/help config` is implemented; whether the broad
survey found the relevant owner; whether the empty searches reflect naming
drift or a missing feature.

Drift risk: low but nonzero. The next plan is appropriately investigative,
provided the driver does not convert the survey into an implementation claim.
```

The same artifact also contains an earlier failure pattern: `n1` requests a
tool-assisted repository inspection, while `n2`, `n4`, `n6`, and `n8` repeat
that tools or repository access are unavailable. That history should be
represented as recovery context or attention, not allowed to dominate the
current trajectory after the later `/help tools` and prompt-reset evidence.

## Open Questions

- Should operator intent live in an ordinary transcript message, a control
  record, or an accepted waypoint record?
- Which facts can be computed deterministically from existing records?
- How should stale waypoints be detected after transcript branching?
- Should the driver receive the same waypoint as the operator, or only a
  frontier-local derivative?
- What is the cheapest useful trajectory challenge before invoking a second
  model or larger context?
