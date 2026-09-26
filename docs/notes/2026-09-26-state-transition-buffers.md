# State-Transition Buffers And The TOAS Step Operator

Status: DRAFT
Normative Scope: exploratory design; no new syntax or runtime behavior is specified
Task Link: `260926-skill-state-reference-and-design`
Follow-on: `260926-state-simulation-checkpoint`

## Starting Point

The user proposed exploring a handoff at every inference turn, naturally shown
as a fresh buffer in the text editor. During a user turn they can choose calls,
inspect their results, and supply selected results alongside feedback and
steering to the next inference. The same `step` operator might accept this
shape, with explicit buffer structure or markers distinguishing it from a
transcript buffer. A new project or separate operator command is not assumed.

The immediate work is to adopt the paper as reference material and articulate
the connection. This note records that direction without promoting illustrative
ideas into a parser contract.

## What The Paper Proposes

[SKILL.state](../references/skill-state/paper.md) gives each inference the
immutable skill specification, current structured execution state, and latest
observation. The model proposes a state patch and an action. The runtime
validates the patch, applies it, and executes the action; intermediate reasoning
does not enter subsequent prompts. Schemas are authored per domain, rather
than discovered anew per task. See sections 3.1–3.3 and Algorithm 1.

The authors report reduced token consumption and improved or competitive task
performance against their tested history and compression baselines. These
results motivate an experiment; they do not establish benefits for TOAS or for
manually authored handoffs. The bounded-context argument requires the retained
state and observations themselves to remain bounded. Fresh buffers alone do
not establish that bound.

Section 7 makes the key assumption explicit: the retained state must contain
everything from the past needed for future execution. The authors identify
limits when schemas must be discovered dynamically, earlier observations turn
out to matter after being discarded, or the historical trajectory is itself
the object of the task. Section 5.7 also reports semantic state-tracking
failures in an open-weight model. Schema validity does not establish that a
state update is factually correct.

## Where TOAS Differs

TOAS's current [vision](../vision.md) makes the user-edited transcript the
working proposal against append-only durable history. Transcript reconciliation
and frontier resolution have meaning beyond prompt assembly. Revising aligned
content branches history; a transcript is an object the user operates on.

The proposed handoff buffer changes how continuity is expressed. Each inference
starts from deliberately carried context rather than implicitly continuing the
whole conversation. The user maintains continuity by choosing what survives.
That is a different interaction model, even if the same storage and execution
capabilities support it.

| Concern | Paper | TOAS exploration |
| --- | --- | --- |
| Continuity | Validated mutable state under a domain schema | Explicitly authored handoff; precise structure remains open |
| Next inference | Specification, state, latest observation | Selected instructions/context, results, feedback, and steering |
| Calls | Model action in the runtime cycle | User can choose calls and decide what reaches inference |
| Working surface | Structured execution state | Editable text buffer, potentially renewed every inference turn |
| Prior trajectory | Discarded from future reasoning context | Retained as durable evidence; inclusion in inference is explicit |
| Advancement | Repeated state-transition loop | Explicit `step`, resolving one layer of consequence |

This would be a TOAS adaptation inspired by the paper, not an implementation
of its fixed-schema execution method merely by changing buffer presentation.
User-authored context may contain prose and multiple selected results; neither
is equivalent to the paper's structured state plus latest observation.

## One Operator, Explicit Proposal Shapes

The working hypothesis is that `step` can retain a common meaning: accept the
current proposal and resolve one layer of consequence. The proposal shape
determines its interpretation:

- A transcript proposal aligns authored turns with message history and advances
  its unresolved frontier.
- A state-transition proposal explicitly supplies the context for the next
  transition, without implicitly including prior turns as model input.

The distinction must be visible to both the person and the parser. A fresh
filename alone would not define it. Buffer markers or structure would select
semantics, so their grammar, escaping, mixed-shape handling, and error behavior
need a later contract. No marker spelling is selected here.

An illustrative interaction is:

1. Open a handoff buffer containing the objective and carried context.
2. Choose or revise calls, then explicitly step to execute them.
3. Inspect results and select what matters for the next inference, adding
   corrections, feedback, or steering.
4. Explicitly step to request inference over the assembled context.
5. Compose the next handoff in a fresh buffer using the response and chosen
   evidence, then repeat when desired.

This is an interaction sketch, not a required sequence of new commands. A user
turn may include several calls before inference. A fresh buffer per inference
does not necessarily mean a new buffer after every tool-resolution step.
Whether TOAS creates a draft successor or the user authors it remains open.

## Durable History And Authored State

Omitting earlier turns from inference does not require deleting durable
history. TOAS should retain exact submitted context, calls, results, and model
responses through its durable record model. A current-state projection could
be rebuilt from appended facts without mutating earlier entries. The record
schema and relationship between transitions remain design work.

The distinction to preserve is between model-visible continuity and durable
provenance. Earlier buffers can remain inspectable without becoming implicit
input. Likewise, a claim copied into a handoff is authored context, not proof
that a tool succeeded. Links to results should retain their evidentiary role.

Editing a handoff should correct the proposal for subsequent work without
rewriting recorded execution. How editing an already submitted buffer selects
a new transition or branch is unresolved. We should not casually reuse
transcript alignment rules or invent a second hidden parentage mechanism.

Direct user intent must stay distinct from model-addressable capability.
Selecting an assistant-proposed call for execution needs an explicit authority
contract; merely carrying its text forward must not silently widen permission.
Similarly, a state buffer's content must not become a replacement authority
store for grants or other operational policy.

## Existing TOAS Connections

- [Successor continuation](../../tasks/closed/260803-session-rotation-lifecycle.md)
  already establishes an explicit handoff into a bounded successor transcript.
  It remains transcript-shaped continuation, with a compaction handoff and
  durable successor relationship. Per-inference state buffers should be
  compared against this before introducing another lifecycle mechanism.
- [Operator/driver working memory](2026-08-10-operator-driver-working-memory-design.md)
  explores compact orientation between steps. It explicitly leaves the
  transcript in place; the present idea could make the handoff itself the
  working proposal, which goes further.
- [Operational state versus conversational projection](2026-05-15-operational-state-vs-conversational-projection.md)
  supplies the distinction between carried context and actual policy authority.
- [Runtime ownership](../runtime-ownership.md) separates reconciliation,
  operator semantics, durable state, model invocation, and rendering. A shared
  `step` command does not imply that these proposal shapes share every internal
  reconciliation rule. CLI and editor adapters should not own that distinction.

## Refinement From The Conversation

The first user-authored handoff sketch above is exploratory. Closer reading
established that the paper uses sparse state patches: unchanged state survives
through the runtime's merge, rather than requiring a whole-state rewrite at
every turn. A faithful initial experiment should preserve that distinction.
Recursive merge details, domain prompts, API roles, and action-failure behavior
are not fully specified by the paper; choices there must be documented.

The user prefers exploring generic repository work before a SWE-specific
schema. Independent generic and Pi SWE implementations provide candidate
instruction artifacts, not the authors' original prompts. The
[simulation checkpoint](2026-09-26-state-simulation.md) records those sources,
current instructions, and structured state alongside the continuing conversation.

State diffs could support inspection without entering inference context.
Instruction mutability in this exercise is experiment-design refinement, not
a requirement that the executing model modify its own procedure. Native
structured notes are accepted for the simulation; runtime syntax remains open.

The user also reports using empty user turns to advance TOAS under an
action-oriented prompt, even without a tool result. An empty observation can
therefore be explored as a continuation signal: select existing authorized next
work without manufacturing evidence or approving pending proposals. This note
does not assert new parser behavior or a hidden loop.

## Questions For A Later Design Pass

1. What makes a buffer unambiguously state-transition-shaped, and what parts
   are instructions, carried state, steering, callable intent, and evidence?
2. Is a schema useful or required? Who authors it, and what can validation
   actually establish for prose-heavy, exploratory work?
3. What is carried automatically, what requires user adoption, and how can the
   exact next model input be inspected before inference?
4. What identifies a submitted transition and its predecessor? What happens
   when the user revises, re-steps, or forks an earlier buffer?
5. What happens after partial tool failure, interrupted inference, or a repeated
   submission? How do unresolved consequences remain visible across buffers?
6. Can transcript and state-transition proposals alternate along one line of
   work, and what explicit conversion would preserve their differing meaning?

The useful next evidence would be a small editor walkthrough on a real task:
compare ordinary transcript work, existing successor continuation, and repeated
authored handoffs. Observe what is omitted, how recovery works, the effort of
curation, and the actual model inputs. That evidence should precede selecting
syntax, committing to a state schema, or opening implementation follow-ons.
