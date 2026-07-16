Filed as: 260716-procedure-step-taxonomy
FKA:
AKA: procedure states; cohort barrier declarations; worker progress taxonomy
Legacy index:

keywords: exploration, decomp, active, contract, transcript, projection, provenance

Parent: `260626-transcript-parallelism-design-pressures`
Depends on: `561`
Related: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260509-multi-operator-orchestration`

# Procedure-Step Taxonomy for Coordinated Transcript Work

## Current Reality

TOAS can address distinct transcript surfaces, but it has no declared process
state that lets a coordinator distinguish a child that is still progressing
from one that has reached a review barrier, is blocked, or has fallen out of a
shared procedure. Counting local TOAS steps cannot provide that distinction:
workers may require different numbers of local turns to reach the same
procedure barrier.

## Desired Reality

Define the smallest explicit procedure-state declaration model that lets a
coordinator group bounded child work for review without treating transcript
projection, activity transport, or inferred model output as durable truth.

The model must make it possible to say, durably and audibly:

- which procedure step and subject a declaration concerns;
- whether the subject is `in_progress`, `reached_barrier`, `blocked`, or
  `off_track`;
- what compact summary, evidence, need, or exception reason justifies it; and
- when a `cohort_key` is meaningful versus when the item belongs in an
  exception lane.

## Scope

- Distinguish a procedure step from a local TOAS step and from an activity
  lifecycle event.
- Define a minimal declaration shape, ownership, and append-only provenance
  requirements.
- Name valid first-pass statuses and their coordinator-facing meanings.
- State which evidence may support a declaration (explicit operator/worker
  declaration, command result, artifact/commit, verification result, or a
  step-kind-specific evaluator) without allowing implicit autonomous
  scheduling.
- Provide two worked examples: a coherent cohort reaching a barrier and an
  off-track item entering an exception lane.
- Decide whether this evidence shows a focused record/projection follow-on is
  ready, or instead exposes a prerequisite in surface visibility.

## Non-Goals

- Implementing queues, claims, a scheduler, or automatic cohort assignment.
- Introducing multiple event journals or merge provenance unless the proposed
  declaration model demonstrates a concrete need.
- Making transcript text or watcher rendering the authority for procedure
  state.

## Completion Evidence

- A design note states the declaration taxonomy, durable-versus-projected
  boundary, and transition/validation invariants.
- The two worked examples demonstrate that one coordinator can perform serial
  review at a barrier while preserving an explicit exception path.
- A named follow-on (if warranted) has bounded ownership, allowed write
  surfaces, acceptance criteria, and test evidence; otherwise this task records
  why implementation is premature.

## Allowed Write Surfaces

- `docs/notes/` for the design contract
- `tasks/open/` and `tasks/closed/` plus generated `tasks/WORKBOARD.md` for
  decomposition and disposition
