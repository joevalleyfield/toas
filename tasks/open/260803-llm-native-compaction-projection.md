Filed as: 260803-llm-native-compaction-projection
FKA:
AKA: llm-native compact; assisted compaction; abridge command; compact projection
Legacy index:

keywords: projection, decomp, inception, contract, compaction, transcript, defaults, llm

Related: `514`; `234`; `260727-one-turn-projection-tail-frame`; `260803-session-rotation-lifecycle`

# LLM-Native Compaction As Projection

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

- [ ] `/compact` invokes the selected LLM through the normal model-transport
  boundary and produces a compact projection without mutating prior events.
- [ ] `/abridge` (or the settled equivalent) preserves current deterministic
  collapse, dry-run, threshold, and idempotence behavior.
- [ ] Help and migration messaging make the command rename discoverable.
- [ ] A compaction projection records source lineage and model-call evidence
  sufficient to inspect how it was produced.
- [ ] The compacted view preserves current objective, decisions, constraints,
  completed work, failures/indeterminate outcomes, and explicit forward plan
  in representative fixtures.
- [ ] Durable operational state remains effective even when absent from or
  summarized in compacted conversational text.
- [ ] Failed or invalid LLM compaction leaves the active transcript/projection
  unchanged and exposes a useful failure result.
- [ ] Reprojection and transcript/history inspection can still recover the
  uncompacted source material.
- [ ] Tests distinguish projection selection from history mutation and cover
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
