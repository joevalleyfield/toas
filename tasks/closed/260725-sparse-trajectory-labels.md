# Establish Sparse Trajectory Labels for Small-Step Agent Work

Filed as: 260725-sparse-trajectory-labels
FKA: ddd-add-sparse-trjactory-labels-for-small-step-agent-work
AKA: sparse trajectory labels; trajectory labels; probe cluster intent; trajectory taxonomy
Legacy index:

keywords: transcript, projection, intent, trajectory, conversation, closed

Related: `260823-intent-tail-focus-trace`; `260823-conversation-map-projection`; `260926-state-step-requirements`

Status: CLOSED 2026-10-16; superseded by per-turn intent tail structure and state-step conversation metadata

## Disposition and Resolution

This task explored introducing a soft taxonomy of 2-3 word trajectory labels (`Active line`, `Current move`, `Move reason`, `Expected signal`, `Stop condition`, etc.) into tool-call metadata to avoid terse, context-free probe chains during small-step turns.

In practice, this low-level tool-call trajectory schema was overtaken by higher-level mechanisms:
1. In conversation mode, per-turn intention tail tracking (see `260823-intent-tail-focus-trace`) and conversation map projection (`260823-conversation-map-projection`) ground focus shifts without imposing structured metadata blocks onto individual tool calls.
2. In state-step mode, the protocol established in `260926-state-step-requirements` and `261010-direct-tool-artifact-capture` handles trajectory steering and context through `state.notes`, `state.artifacts`, and tool `label`/`target` parameters.

The exploratory design and vocabulary analysis below are archived for historical reference.

## Current Reality

TOAS uses small, stepped turns rather than autonomous loops. This gives the operator frequent control points, but it also means the visible transcript often lacks the accumulated explanatory glue that longer assistant responses or loop agents accidentally produce.

The current tool-call metadata has a single `intent` field. That field is useful, but overloaded. It can mean the immediate action, the broader investigation line, the reason for the action, the expected evidence, or the stopping condition.

When agents are instructed to be terse, they often preserve action while deleting trajectory. The result is a string of file reads, searches, and listings with too little visible explanation of where the agent is going or why.

## Desired Reality

Tool use should stay compact while making the agent’s trajectory legible.

The agent should have a small vocabulary of sparse, human-readable trajectory labels. These labels should be available when useful, not mechanically required.

The labels should help the operator quickly understand:

* what line of investigation is active
* why the current move matters
* what result would change direction
* what would make the line stop or checkpoint
* what changed after a probe cluster

The labels should also support proactive context management across:

* user-visible transcript
* LLM-visible working register
* event/scratch recall space

## Gap Analysis

The current `intent` field does not provide enough structure to distinguish immediate action from longer-term trajectory.

One-word labels are compact but ambiguous. Labels such as `signal`, `delta`, or `line` require the human to remember what kind of blank is being filled.

Two- or three-word labels are slightly more token-expensive but much easier to read and mirror. The redundant tokens reduce interpretation cost.

The missing capability is not a rigid schema. It is a soft taxonomy with stable meanings and sparse use.

## Known Facts

Small-step TOAS turns make trajectory projection more important, not less.

The transcript should not be treated as the whole workspace. It should be a rendered view of the current working state.

Append-only event history can remain authoritative while the current working view is updated through projection, supersession, parking, and closing.

The agent and the operator can both change direction at any step. The goal is not to enforce a loop-control protocol, but to make trajectory visible enough that movement feels intelligible.

## Assumptions

Sparse labels will reduce friction more than they increase it if they are optional and idiomatic.

The agent will mirror labels more reliably if the opening task frame demonstrates the vocabulary.

Longer labels are preferable to one-word labels because they are self-decoding.

The labels should be used around bounded probe clusters, not before every low-level tool call.

## Unknowns

Which labels are the smallest sufficient set?

How much trajectory metadata should live in the user-visible transcript versus the LLM-visible register?

Should the runtime store these labels as structured fields, plain text, or both?

How should scratch/event records represent parked fronts, closed lines, and superseded beliefs?

What projection cadence gives enough visibility without creating process noise?

## Investigations

### Label Set Evaluation

Evaluate the following candidate vocabulary:

* Active line
* Current move
* Move reason
* Expected signal
* Stop condition
* Observed finding
* Belief delta
* Likely next
* Parked front
* Closed line
* Superseded belief

Check whether each label has a clear blank and whether it reduces ambiguity compared with a one-word equivalent.

### Projection Policy Evaluation

Decide when labels should appear in the user-visible transcript.

Candidate rule:

Show trajectory labels when they clarify direction, especially before or after bounded probe clusters.

Avoid labels for obvious mechanics, repeated file boilerplate, raw scratch notes, or dead-end detail unless the detail affects the next decision.

### Runtime Representation Evaluation

Determine whether tool-call metadata should continue using a single `intent` field plus optional free-text notes, or whether it should support a small structured trajectory object.

Candidate shape:

```yaml
trajectory:
  active_line:
  current_move:
  move_reason:
  expected_signal:
  stop_condition:
```

Sparse population only. No assertions that every field must exist.

## Models

### Soft Taxonomy Model

The labels are available handles, not required fields.

Soft rule:

Use one to three labels when they clarify direction.

Hard rule:

When a label is used, it has a stable meaning.

### Projection Model

Event space remains append-only.

The working register is mutable by projection.

The user-visible transcript is a compact rendered view of the current trajectory.

### Probe Cluster Model

Low-level tool calls are grouped under an investigation frame.

Before a cluster, show the active line and move reason when useful.

After a cluster, show observed finding, belief delta, likely next, or stop condition when useful.

## Forecasts

This should reduce the “where the hell is it going?” failure mode.

It should make terse agents more tolerable because they can compress mechanics without omitting investigative intent.

It should give the operator a vocabulary for steering without needing to write long corrections.

It should make future scratch recall more useful because records will have stable trajectory handles.

## Risks

The taxonomy could become paperwork if labels are treated as mandatory fields.

The agent may overuse labels and make every step feel bureaucratic.

The distinction between user-visible projection and LLM-visible register may become blurry.

A too-large label set could increase friction instead of reducing it.

Runtime support might over-structure what should remain idiomatic and language-native.

## Transformations

### Replace overloaded `intent` usage

Move from one overloaded field:

```yaml
intent: Inspect serializer.
```

Toward sparse trajectory framing:

```yaml
Active line: trace where lane metadata is lost.
Current move: inspect serializer after constructor looked clean.
Stop condition: first boundary where expected lane metadata disappears.
```

### Add trajectory labels to initial task framing

Opening task frames should demonstrate the vocabulary so the agent can mirror it.

Example:

```text
Active line: tighten small-step TOAS tool use so investigations stay legible without becoming verbose.

Current bet: a single `intent` field is overloaded. Use sparse trajectory labels when they clarify direction.

Preference: use one to three labels when useful. Do not fill fields mechanically. I care most about active line, move reason, expected signal, and stop condition.
```

### Support nearly-write-only context records

Use append-only records with lifecycle projection:

* Parked front
* Closed line
* Superseded belief
* Observed finding
* Belief delta

Do not mutate history. Mutate the working view by appending projection records.

## Evidence

Useful labels should be tested against real TOAS-style file/search/tool sequences.

A successful interaction should show fewer unexplained probe chains.

The operator should be able to understand why the agent is looking at a file before the file is read, or understand after a probe cluster why the line continued, changed, parked, or closed.

The labels should be readable without memorizing a schema.

## Decisions

Use two- or three-word labels instead of one-word labels.

Prefer sparse, opportunistic use over required schema completion.

Treat the labels as vocabulary for trajectory projection, not as mandatory tool-call assertions.

Keep `Stop condition` as a named available concept because it gives curiosity a visible boundary.

Use labels around probe clusters rather than every low-level action.

## Open Fronts

Define the minimal final label set.

Decide whether the runtime should store labels structurally or as compact text notes.

Design scratch/event record types for trajectory projection.

Define projection cadence for user-visible transcript updates.

Test the vocabulary on an actual TOAS debugging or implementation session.

Decide how much of the working register should be visible by default.

## Next Actions

Draft compact system instructions for sparse trajectory labels.

Create a short initial-task framing template that demonstrates the vocabulary.

Run the template against a real tool-heavy task and observe whether the agent mirrors the labels.

Compare one-word labels against two- and three-word labels in real transcript excerpts.

Refine the label set down to the smallest vocabulary that remains self-decoding.
