# Procedure-Step Taxonomy for Coordinated Transcript Work

Status: DIRECTIONAL
Task Link: `260716-procedure-step-taxonomy`
Related: `260626-transcript-parallelism-design-pressures`; `561`

## Decision

Use **coordination procedure** for the larger operator-directed process that
groups multiple transcript surfaces. It is distinct from the existing
`procedure` capability, which is a static YAML plan of tool operations, and
from an async activity, whose `run_done` only reports one live execution's
terminality.

The first durable primitive should be an append-only `coordination_state`
record. It is an explicit assertion about one subject's position at one
coordination-procedure step. A read-only projection can group the latest
assertions into barriers, cohorts, and exception lanes. Neither the record nor
its projection schedules child work or infers state from transcript text.

## Record Shape

The proposed first payload is:

```yaml
id: cs-42
procedure_id: repair-root-divergence-v1
step_id: verify
subject_surface_id: docs
status: reached_barrier
summary: focused repair committed; targeted test passes
evidence_refs: [n71, commit:abc123]
cohort_key: repaired-cleanly
supersedes: cs-31
```

Required fields are `id`, `procedure_id`, `step_id`, `subject_surface_id`,
`status`, and a non-empty `summary`. `subject_surface_id` uses the durable
surface identity supplied by `561`; a future packet identifier may supplement
it, but is not a prerequisite for the first slice.

Optional fields are:

- `evidence_refs`: durable ids or stable external artifact references;
- `cohort_key`: an operator-declared grouping key, never an inferred class;
- `needs` and `blocked_by`: compact unmet dependency descriptions;
- `exception_reason`: why the subject no longer rhymes with its shared path;
- `supersedes`: the preceding assertion for this
  `(procedure_id, step_id, subject_surface_id)` tuple.

Records are append-only. The current coordinator view selects the latest valid
assertion per tuple by log order (or the explicit `supersedes` link when
present); it never rewrites an earlier state.

## Initial Status Contract

| Status | Coordinator meaning | Minimum additional evidence |
| --- | --- | --- |
| `in_progress` | subject remains on the current shared procedure step | summary |
| `reached_barrier` | subject is ready for comparable review at this step | evidence ref or explicit operator attestation |
| `blocked` | subject cannot safely continue its current step | `needs` or `blocked_by` |
| `off_track` | subject no longer belongs to the current shared path | `exception_reason` |

`cohort_key` is valid only for `in_progress` and `reached_barrier`. A blocked
or off-track subject is visible in an exception lane until an explicit later
assertion returns it to a shared path. Starting a later procedure step requires
a new assertion; a `run_done`, tool result, transcript edit, or watcher event
cannot advance procedure state implicitly.

## Ownership Boundary

- **Durable State** owns the record schema, append/query helpers, and
  latest-valid projection index.
- **Operator Semantics** owns explicit declaration validation and the rule that
  evidence supports but does not automatically create an assertion.
- **Projection And Rendering** owns compact coordinator views grouped by
  `procedure_id`, `step_id`, `status`, and `cohort_key`.
- **Activity Lifecycle** continues to own live run status and terminality only.
  A completed child run is evidence a declaration may cite, not a barrier
  transition.

The first write path should be an explicit operator action; a worker may
propose a declaration, but it becomes durable only through that action. This
preserves the no-hidden-loop rule and prevents model interpretation from
becoming queue authority.

## Worked Shapes

### Cohort barrier

Three surfaces execute different numbers of local TOAS turns while following
the `verify` procedure step. Each explicitly writes `reached_barrier` with
`cohort_key: clean`. The coordinator's view groups the three records for one
serial QA pass. It does not claim that their local transcripts, heads, or runs
are identical.

### Exception lane

One surface discovers a missing fixture during the same `verify` step. It
writes `off_track` with `exception_reason: fixture absent` and references the
failed check. The coordinator view removes it from the `clean` cohort and
shows it in the exception lane. A later explicit `in_progress` assertion may
place it in a remediation cohort; no inferred recovery occurs.

## Implementation Cut

The first implementation slice is deliberately small:

1. durable `coordination_state` writer and latest-valid query;
2. explicit declaration validation for the four statuses and their required
   fields;
3. a read-only coordinator projection grouped by procedure/step/status/cohort;
4. deterministic tests proving append-only supersession, invalid declaration
   rejection, cohort grouping, and that activity terminality alone produces no
   coordination state.

Queues, claims, automatic cohort formation, packet identity, multi-journal
history, and scheduler behavior remain out of scope until this explicit fact
model is demonstrated useful.
