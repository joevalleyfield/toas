# Explicit-State Conversation Simulation

Status: DRAFT
Normative Scope: experiment design and checkpoint; no shipped runtime contract
Task Link: `260926-state-simulation-checkpoint`

## Working Artifact

[Current instructions and state](2026-09-26-state-simulation.yaml) consolidate
the shadow-state exercise alongside the full Codex conversation. The YAML has
three parts: `instructions` governing the next simulated turn,
`instruction_revisions` recording experiment-design history, and `state`
carrying the working context. Revision history is for inspection; it need not
enter simulated inference input. No runtime loader consumes this file.

Version 1 was consolidated in the conversation. Version 2 records accepted
native notes structure and the empty-turn continuation rule drawn from the
user's TOAS workflow. These are local simulation instructions, not the paper's
instructions or a proposal for runtime self-modification.

## Baseline And Adaptations

The starting candidate is
[vitkuz573/skillstate's generic procedure](https://github.com/vitkuz573/skillstate/blob/main/skill-spec.json),
reviewed September 26, 2026. It uses `goal`, `progress`, `next_steps`, `artifacts`,
`blockers`, and `notes`. This checkpoint is our authored adaptation, not a
vendored copy or an author-provided benchmark artifact. The URL names a moving
branch, not a pinned reproduction source.

The generic source declares `notes` as a string. Our conversation produced
native YAML categories for constraints, accepted decisions, pending proposals,
and uncertainties. The user accepted preserving this structure rather than
fencing or escaping a subdocument into a string. Enumerated categories helped
elicit the structure; future schema validation must agree with that representation.
Structured artifact entries remain provisional. We also distinguish actual
blockers from non-blocking unknowns and milestones from ongoing activities.

For later comparison:

- [Pi SWE instructions and schema](https://github.com/toadharvard/pi-skill-state-runtime/blob/main/examples/software-task.json)
  distinguish phase, facts, hypotheses, files, completed work, next action, and
  verification. Generic repository work remains the first candidate.
- [Minimal Python implementation](https://github.com/kissishka/skill-state-minimal)
  offers a scripted warehouse example and concrete retry/rollback choices.
  Those are independent implementation choices, not evidence of the authors'
  exact execution semantics.

## Running The Simulation

Show proposed state changes each turn, including meta discussion, or explicitly
report no change. Unmentioned state survives. The conversation's `append`,
`prepend`, and `remove` displays are readable edit notation, not an adopted
runtime patch grammar. They do not imply that arrays recursively merge.

An empty user turn can signal continuation: choose useful next work already
supported by the goal, state, and authority. It supplies no new evidence and
does not approve pending choices. Do not treat a previous result as newly
observed or infer success from missing feedback. An eventual explicit empty
observation or continuation signal has no selected serialization yet. This
does not request a hidden execution loop.

The user explicitly requested this repository checkpoint. Empty-turn behavior
is described here, not tested against TOAS's parser or frontier implementation.
Instruction revisions are explicit design work between simulated turns; retain
their reason and effective version rather than rewriting the experiment silently.

## Evidence And Next Work

The exercise has advanced from an initial dump to visible patches, instruction
clarification, and a saved checkpoint. Simulation remains ongoing. Full
conversation access means this does not establish retained-state sufficiency
or reproduce the paper's benchmark results.

Use the checkpoint to guide another real repository-work turn and inspect what
is missing, ambiguous, or needlessly retained. Isolated-context evaluation is a
later experiment requiring its own scope.

See the [buffer design note](2026-09-26-state-transition-buffers.md) and the
[vendored paper](../references/skill-state/paper.md).
