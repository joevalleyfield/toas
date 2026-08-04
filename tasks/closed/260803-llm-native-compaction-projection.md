Filed as: 260803-llm-native-compaction-projection
FKA:
AKA: llm-native compact; assisted compaction; abridge command; compact projection
Legacy index:

keywords: projection, historical, completed, contract, compaction, transcript, defaults, llm

Related: `514`; `234`; `260727-one-turn-projection-tail-frame`; `260803-session-rotation-lifecycle`

# LLM-Native Compaction As Projection

## Status

Completed on 2026-08-04. Production use exposed and corrected two related
adoption errors: the visible result contained only `compact: selected LLM
handoff projection`, while `session_update` overwrote the transcript file with
the handoff. The settled behavior is append-only at the transcript surface:
project the full handoff as the command result and do not replace the working
transcript.

## Objective

Make LLM-assisted compaction the default meaning of `/compact`, retain the
current deterministic RESULT-block collapsing behavior under `/abridge` (or a
similarly explicit mechanical name), and define compaction as a repeatable
projection over durable history rather than a one-off transcript mutation.

## Current Reality

`/compact` mechanically replaces large projected `RESULT` blocks with character
count placeholders and writes the modified transcript back through a session
update. It is deterministic and useful, but it cannot synthesize decisions,
open questions, constraints, or the minimum context needed for continued work.

The command name now blocks the more useful product meaning: ask an LLM to
produce a smaller faithful working projection while retaining append-only
history as source truth.

## Desired Contract

- `/compact` requests an LLM-generated compact working projection.
- `/abridge` preserves deterministic threshold-based RESULT collapsing,
  including dry-run behavior and explicit thresholds.
- Both are projection operations over selected durable lineage; neither deletes
  or rewrites prior history events.
- The compact projection preserves active user intent, achieved results,
  unresolved decisions, execution state, explicit constraints, and references
  needed to recover omitted detail from history.
- Operational state such as grants, config, session-control facts, queued work,
  and indeterminate execution outcomes remains authoritative outside compactable
  conversational prose.
- Re-running the projection is observable and reproducible enough to audit its
  source lineage, prompt/version, and model-call evidence.

## Requirements Parent Questions

- Is the output adopted into the active transcript, exposed as a selectable
  projection, or both?
- What record, if any, durably states that a compact projection was selected
  without making the generated prose canonical history?
- What source boundary does `/compact` use: current head, active transcript
  alignment, explicit range, or a session-rotation boundary?
- Which schema should the LLM produce: free-form transcript, structured
  synthesis plus renderer, or a hybrid?
- How is compaction failure handled without damaging the current working
  transcript?
- What minimum evidence enables drill-back from a compacted statement to its
  source events?
- Should mechanical abridgement run before LLM synthesis to control input
  size, and if so how is that preprocessing made visible?

## Acceptance Criteria

- [x] `/compact` invokes the selected LLM through the normal model-transport
  boundary and produces a compact projection without mutating prior events.
- [x] `/abridge` (or the settled equivalent) preserves current deterministic
  collapse, dry-run, threshold, and idempotence behavior.
- [x] Help and migration messaging make the command rename discoverable.
- [x] A compaction projection records source lineage and model-call evidence
  sufficient to inspect how it was produced.
- [x] The compacted view preserves current objective, decisions, constraints,
  completed work, failures/indeterminate outcomes, and explicit forward plan
  in representative fixtures.
- [x] Durable operational state remains effective even when absent from or
  summarized in compacted conversational text.
- [x] Failed or invalid LLM compaction leaves the active transcript/projection
  unchanged and exposes a useful failure result.
- [x] Reprojection and transcript/history inspection can still recover the
  uncompacted source material.
- [x] Tests distinguish projection selection from history mutation and cover
  native-chat plus `single_user_blob` request rendering where relevant.

## Non-Goals

- Deleting historical events or defining archive retention.
- Treating an LLM summary as canonical durable truth.
- Folding session lifecycle/rotation policy into the summarization algorithm.
- Guaranteeing semantic equivalence for arbitrary unstructured summaries
  without a bounded output contract and evaluation fixtures.

## Allowed Write Surfaces

- operator command handling under `src/toas/runtime/`
- model invocation and projection seams under `src/toas/runtime/` and
  `src/toas/llm.py`
- prompt assets under `src/toas/prompts/`
- `src/toas/graph.py` only for a justified projection-selection/evidence record
- CLI/help surfaces and focused tests under `tests/`
- relevant projection/command documentation
- this task file and mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- settled projection and adoption contract;
- migration proof for mechanical `/compact` -> `/abridge`;
- golden fixtures evaluating retained intent/state and omitted bulk;
- before/after transcript, history, and model-call evidence;
- failure-path proof and default suite result.

## Operator Input Welcome

Useful additions include preferred compaction prompts, sample good/bad summaries,
schemas or prior artifacts, desired drill-back affordances, and examples of
state that must survive compaction verbatim.

## Operator-Supplied Resume Contract

The established compaction prompt produces a structured `# Handoff Summary`
with objective, working state, prioritized plans, observations, actions,
version-control state, durable procedure changes, open questions, one immediate
next step, and a short verbatim-preservation section.

That verbatim section must also carry an explicit rehydration recipe:

- files to restore into context;
- commands to run after restoration;
- `AGENTS.md` among the restore files whenever it would otherwise be omitted.

The operator's current manual continuation ritual is to execute one
`$ cat <file>` command per restore file, then the listed `$ <command>` entries.
The assisted projection should preserve that transparent, editable sequence
rather than hiding restoration in an implicit runtime loop.

## Settled Contract

- Accepted handoffs are appended as graph-native user-facing projection
  messages tagged `llm_compaction`; the generated prose is derived context, not
  a rewrite of source messages.
- The exact handoff is also the visible `RESULT` returned by `/compact`, so the
  editor appends it to the existing working transcript. `/compact` emits no
  `session_update` and does not replace the transcript file behind the editor.
- A `compaction_projection` control record selects that message and records the
  source IDs, source head, and `compaction/handoff_v1` prompt reference.
- Runtime reconciliation binds the working transcript at the selected
  projection message. Operational records continue resolving from the complete
  event log.
- `/abridge` owns the old deterministic RESULT collapsing flags and behavior.
- Invalid shape or generation failure produces an explicit error result and no
  session/projection update.

## Completion Evidence

- Added the versioned operator-supplied handoff prompt with literal files-to-
  restore and commands-to-run sections, including the `AGENTS.md` safeguard.
- Added projection persistence, model-call association, active bind resolution,
  safe repeated projection, and migration help/documentation in
  `docs/compaction-projections.md`.
- Focused command, graph, persistence, and reconciliation coverage passes.
- Full suite: `2764 passed, 9 deselected`; required coverage remains 100%.
- Production correction proof: `/compact` now returns the exact validated
  handoff as its `RESULT` and carries no `session_update`. The side-effect
  fixture proves the predecessor transcript remains byte-for-byte unchanged
  while the `llm_compaction` message, model call, and selection record remain
  durable. Rotation fixtures now consume handoffs appended under `## RESULT`,
  including a repeated compact/rotate cycle. Focused regression surfaces: 513
  passed; final full suite: 2,787 passed, 9 deselected, 100% coverage.
