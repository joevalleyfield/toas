# Template: Architecture Role Review Passes

## Purpose

Use focused roles to critique and refine architecture work in small, auditable
passes instead of asking one review to do every kind of thinking at once.

This template is useful when a design document, architecture task, or subsystem
proposal needs top-down critique before implementation.

## Trigger Model

- `architecture_draft`: a new architecture proposal exists and needs review
- `pre_implementation`: an accepted direction is about to drive code movement
- `post_discovery`: discovery found enough shape to critique boundaries

Record the trigger explicitly in the run or task using this template.

## Inputs

- Target architecture document or task
- Current roadmap/capabilities/runtime ownership notes
- Relevant implementation files when the pass needs concrete evidence
- Prior role outputs, if this is part of a sequence

## Output

For each role pass, produce one of:

- direct document edits
- critique notes in the target task/doc
- extracted decisions or follow-up tasks
- an explicit "no edit; keep as context" result

When a pass creates decisions, mark their status as `proposed`, `accepted`,
`rejected`, or `unresolved`.

## Suggested Sequence

1. Author
2. Reader
3. Force Mapper
4. State Ownership Architect
5. Flow Architect
6. Failure Ownership Architect
7. Split-or-Merge Architect
8. Architecture Decision Extractor
9. Editor
10. Boundary Invariant Architect
11. Port / DI Architect
12. Implementer
13. Maintainer
14. Verifier
15. Risk Reviewer
16. Decision Recorder
17. Editor, again if the document has accumulated new material

The sequence is not mandatory. Pick the next role that exposes the sharpest
remaining uncertainty. Keep one role active at a time, even when several roles
run in the same work session.

## Role Templates

### Author

Ask:

- What is this document trying to make easier?

Review for:

- clear job
- intended reader
- non-goals
- whether the document or task is meant to orient, justify, preserve decisions,
  guide implementation, constrain future change, or support review

Return:

```text
This document exists to...
It is not trying to...
The primary reader is...
```

### Reader

Ask:

- Can someone unfamiliar recover the shape without already knowing it?

Review for:

- missing context
- undefined terms
- hidden assumptions
- jumps in abstraction
- diagrams or examples that need to exist

Return:

- what a cold reader can recover
- what requires warm context
- terms that need definition
- examples or diagrams that would make the shape recoverable

### Force Mapper

Ask:

- Does each proposed domain exist because of a real architectural force?

For each proposed domain:

1. Name the force that justifies its existence.
2. Say whether the domain is a noun bucket or a force boundary.
3. Identify forces currently mixed together.
4. Identify forces that are missing entirely.
5. Propose better domain names only where the current name hides the force.

Return:

- force boundary assessment per domain
- missing forces
- naming changes that clarify forces

### State Ownership Architect

Ask:

- Who owns each kind of state?

Find durable, ephemeral, derived, cached, projected, and externally-owned state.

For each state item:

1. Where does it live?
2. Who may mutate it?
3. Who may derive from it?
4. Who may cache it?
5. What must never be duplicated?
6. What happens across restart/reconnect/crash?

Return:

- state ownership table
- top unresolved ownership risks

### Flow Architect

Ask:

- Do concrete cross-domain flows preserve the proposed ownership map?

Walk concrete flows relevant to the design. Suggested baseline flows:

1. User edits transcript, then steps.
2. Model starts an async tool run.
3. Subscriber reconnects after terminal event.
4. Host dies mid-activity.
5. Config changes while backend is alive.
6. Backend health passed, then process dies.

For each flow:

- Which domains participate?
- What state is read/written?
- What event or command crosses each boundary?
- Which domain owns the final consequence?
- Where could responsibility become ambiguous?

Return:

- flow table
- flow-derived invariants or ambiguity risks

### Failure Ownership Architect

Ask:

- Who owns detection, recording, recovery, and operator exposure for failures?

Focus especially on:

- host/process death
- stale RPC compatibility
- transcript branch ambiguity
- stream reconnection
- cancellation
- config changes

For each failure mode:

1. Who detects it?
2. Who records it?
3. Who decides recovery?
4. Who exposes it to the operator?
5. What durable meaning, if any, changes?
6. What must not be silently retried or hidden?

Return:

- failure ownership table
- top unresolved failure ownership gaps

### Split-Or-Merge Architect

Ask:

- Which soft boundaries should remain split, merge, or stay experimental?

For each soft boundary:

1. Argument for keeping it split.
2. Argument for merging it.
3. State ownership implication.
4. Failure ownership implication.
5. Testability implication.
6. Naming implication.
7. Recommended decision or experiment.

Return:

- split/merge table
- recommended splits, merges, and experiments

### Architecture Decision Extractor

Ask:

- What decisions are already implied by the draft and critique?

For each decision:

1. Decision statement.
2. Status: `proposed`, `accepted`, `rejected`, or `unresolved`.
3. Forces.
4. Consequences.
5. Rejected alternatives.
6. Evidence needed.
7. Follow-up owner/pass.

Do not invent decisions. Extract only what is present or strongly implied.

Return:

- decision ledger
- items that are important but not decision-ready

### Editor

Ask:

- Can the document be shorter, sharper, and less ambiguous?

Review for:

- structure
- headings
- paragraph order
- vocabulary consistency
- duplicated claims
- reader affordances
- whether appendices or raw critique notes should be compressed or moved

Return:

- document edits or a precise edit plan
- remaining sections that are still too long or ambiguous

### Boundary Invariant Architect

Ask:

- What hard invariants protect each boundary?

For each boundary:

1. What is this domain allowed to know?
2. What is it forbidden from deciding?
3. What may cross the boundary?
4. What must not cross the boundary?
5. What failure would prove the boundary is wrong?

Return:

- short normative invariant statements per domain
- candidate guardrails for future implementation and review

### Port / DI Architect

Ask:

- Which dependency boundaries should be ports, and which injections are hiding
  missing ownership?

Use the rule:

> Inject ports, not implementation steps.

For each domain:

1. What ports may it depend on?
2. What implementation steps must not be injected?
3. What concrete dependency would be a smell?
4. What fake/test double should be easy to provide?
5. What dependency would cause semantic leakage across domains?

Return:

- port/DI table
- cross-cutting DI rules
- candidate ports for the first implementation slice

### Implementer

Ask:

- Could I build or change code from this?

Review for:

- actionable interfaces
- module, file, function, and package boundaries
- sequencing and migration steps
- API contracts
- test surfaces
- places where the document hand-waves over implementation reality

The implementer is allowed to say:

```text
I understand the concept, but I still don't know what file/module/function
boundary changes.
```

Return:

- first implementation slice sketch
- candidate module/file targets
- contract shapes to design
- tests needed before adapters or compatibility paths
- unresolved implementation questions that should route back to architecture
  roles

### Maintainer

Ask:

- Will this still help six months later?

Review for:

- operational burden
- naming stability
- future edits
- ownership and stewardship
- extension paths
- stale-prone sections
- whether durable architecture is separated from temporary plan

Return:

- sections that are durable architecture
- sections that are current migration plan
- stale-prone claims to move, qualify, or delete
- ownership and update expectations for the document
- naming or structure changes that would age better

### Verifier

Ask:

- What would prove the architecture is doing its job?

Pull out:

- invariants
- test obligations
- observability hooks
- acceptance evidence
- QA notes
- must-not-regress behaviors

Return:

```text
Evidence needed:
- test ...
- manual scenario ...
- invariant ...
- trace/example ...
```

### Risk Reviewer

Ask:

- Where is the design brittle, expensive, or overfit?

Review for:

- accidental complexity
- hidden global state
- migration traps
- concurrency hazards
- unclear ownership
- too-clever abstractions
- tool/model behavior assumptions
- agent misuse risk
- token/cost risk
- transcript/state ambiguity
- human recovery path

Return:

- premortem risks
- likelihood and impact where useful
- mitigations that belong in the architecture
- mitigations that belong in tests, operations, or tasks
- risks to leave visible rather than solve immediately

### Decision Recorder

Ask:

- Are decisions explicit enough to survive disagreement?

For each decision:

```text
Decision:
Rationale:
Rejected alternatives:
Consequences:
Open follow-up:
```

Review for:

- decisions hidden in prose
- alternatives that were rejected but not named
- consequences that will surprise future contributors
- open questions that should not masquerade as decisions
- decision statuses that need to be changed, split, or downgraded

Return:

- decision records suitable for the target doc or ADR log
- ambiguous decisions that need another architecture pass
- open follow-ups with an owner/pass

## Run Record Skeleton

```md
# Architecture Review Run: <topic>

Date:
Trigger: architecture_draft | pre_implementation | post_discovery
Target doc/task:

## Roles Run

- [ ] Author
- [ ] Reader
- [ ] Force Mapper
- [ ] State Ownership Architect
- [ ] Flow Architect
- [ ] Failure Ownership Architect
- [ ] Split-or-Merge Architect
- [ ] Architecture Decision Extractor
- [ ] Editor
- [ ] Boundary Invariant Architect
- [ ] Port / DI Architect
- [ ] Implementer
- [ ] Maintainer
- [ ] Verifier
- [ ] Risk Reviewer
- [ ] Decision Recorder
- [ ] Editor revisit

## Summary

## Decisions Extracted

## Notes Kept As Critique

## Follow-Up Tasks
```

## Guardrails

- Keep each role focused; do not let one pass solve all architecture questions.
- Prefer small transactions and commit or squash intentionally between groups of
  related passes.
- Mark raw role findings as critique notes until they become decisions.
- Promote decisions only after their forces, consequences, and evidence needs
  are clear.
- When a pass finds implementation work, decide whether to create a focused task
  or leave it as critique material.
