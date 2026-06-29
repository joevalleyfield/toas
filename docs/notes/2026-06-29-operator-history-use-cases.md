# Operator History Use-Cases

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-history-surface-user-intent-alignment`

## Purpose

Brainstorm operator-facing reasons TOAS needs durable history while staying at
the product/use-case layer. This note intentionally avoids implementation
proposals.

TOAS history is not the project itself. Repository artifacts are the durable
public body of the project. TOAS history is the local operator harness memory:
how work moved, what was tried, what was trusted, what was abandoned, and what
must remain recoverable when the current transcript is too narrow.

## Active Work Continuity

User story:

```text
I am in the middle of a task, the transcript has become long or messy, and I
need to recover the current thread without rereading everything.
```

History must preserve:

- adopted user and assistant turns
- selected lineage or active task thread
- tool calls and relevant results
- model-call failures or interruptions
- current frontier and unresolved state

History may omit:

- old noisy tool output
- stale branches unrelated to current work
- verbose raw logs once summarized

Expected surface:

- compact current-lineage history view
- transcript-shaped resume projection
- later, a task or thread summary projection

If only the current transcript existed:

- edits, truncation, or projection loss could erase why the current state
  exists
- the user could not distinguish current truth from recently rendered text
- recovery after interruption would depend on fragile text state

## Recovery After Breakage

User story:

```text
Something went wrong: a command failed, a model hallucinated, the session got
interrupted, or I edited the transcript badly. I need to get back to a
trustworthy point.
```

History must preserve:

- known-good prior states
- branch points
- tool requests and results around the failure
- failed model calls and error causes
- enough parentage to reconstruct selected lineage

History may omit:

- unrelated successful tool noise
- full raw stdout after a compact diagnostic is durable
- branches the user explicitly discards under retention policy

Expected surface:

- recovery-oriented history view
- graph or lineage selector
- diagnostics explaining corrupt or ambiguous history
- resume-from-here projection

If only the current transcript existed:

- a bad edit could destroy the recovery path
- failures would be flattened into prose or disappear
- the user would not know whether a visible result was executed, copied,
  regenerated, or imagined

## Review And Audit

User story:

```text
I want to review how this change happened before I trust it, commit it, or
explain it.
```

History must preserve:

- user request
- assistant plan or rationale when available
- files and tools touched
- test commands and outcomes
- important decisions and reversals
- provenance of generated versus user-authored content

History may omit:

- repetitive intermediate output
- exact token stream details
- failed exploratory branches unless relevant

Expected surface:

- task review timeline
- command and test summary
- provenance-rich transcript projection
- links from repository changes back to history events

If only the current transcript existed:

- the transcript may contain the final story but not the chain of evidence
- the user cannot audit whether tests really ran
- review becomes narrative trust instead of evidence-backed trust

## Trust-Building With Weak Or Local Models

User story:

```text
I am using a model that may misunderstand protocol or fabricate confidence. I
need durable evidence of what happened.
```

History must preserve:

- model requests and responses
- tool calls separated from assistant prose
- denials, parsing failures, and malformed actions
- repair attempts
- explicit user approvals or intent

History may omit:

- raw reasoning streams unless intentionally retained
- repeated protocol noise once categorized
- backend-specific chatter not needed for accountability

Expected surface:

- protocol/debug history view
- tool/result ledger
- "why did TOAS do this?" explanation
- mismatch or repair report

If only the current transcript existed:

- assistant claims and actual effects blur together
- malformed tool attempts may vanish
- the user cannot tell whether TOAS enforced boundaries or merely got lucky

## Task Planning And Reorientation

User story:

```text
I am returning after hours or days and need to understand what this task is,
what changed, and what remains.
```

History must preserve:

- task pivots
- decisions and open questions
- links between task files, docs, commits, and transcript episodes
- branch or lineage summaries
- why some paths were deferred

History may omit:

- every token of old brainstorming
- raw command output after summarization
- irrelevant abandoned exploration

Expected surface:

- task-centered timeline
- where-we-left-off projection
- decision log
- unresolved-question list

If only the current transcript existed:

- planning context depends on whatever happens to still be rendered
- the user may lose why a decision was made
- task files and actual operator history can drift apart

## Navigation Across Branches Or Attempts

User story:

```text
I tried several directions. I want to compare them or return to one without
treating them as a linear chat.
```

History must preserve:

- branch parentage
- selected heads
- summaries or previews of branch content
- task or epoch boundaries
- enough identity to distinguish similar turns in different contexts

History may omit:

- full deep history for branches not being inspected
- raw logs for abandoned branches
- duplicate restaged content when alignment proves equivalence

Expected surface:

- graph or topology view
- heads view
- branch preview
- selector by task, time, project, or lineage

If only the current transcript existed:

- branching collapses into text editing
- alternate attempts are lost or manually copied around
- the user cannot navigate history as a set of possible continuations

## Understanding Personal Work Patterns

User story:

```text
I want TOAS history to help me understand how I work across tasks, projects,
days, or epochs.
```

History must preserve:

- task transitions
- recurring decisions
- repeated failure modes
- tool and test habits
- summaries with provenance
- cross-project or time-window alignment anchors

History may omit:

- secrets
- noisy raw tool output
- full transcripts after derived summaries are sufficient
- private details under explicit retention policy

Expected surface:

- project, epoch, or task history projections
- search and filtered timelines
- derived summaries
- cross-transcript views

If only the current transcript existed:

- insight is trapped inside individual sessions
- project boundaries become accidental walls
- long-term understanding depends on manual note-taking

## Artifact Provenance

User story:

```text
I see a doc, task file, commit, or code change. I want to know where it came
from.
```

History must preserve:

- creation and edit events
- user request that motivated the artifact
- assistant or tool actions that produced it
- validation status
- links to repository state when available

History may omit:

- full intermediate drafts
- raw generation chatter
- unrelated parallel context

Expected surface:

- artifact history view
- backlink from file, task, or commit to event lineage
- provenance summary

If only the current transcript existed:

- artifacts become detached from the work that produced them
- later review cannot tell whether a file reflects a decision, a guess, or an
  unfinished experiment

## Safe Forgetting And Retention

User story:

```text
I want the system to remember enough to be useful, but not keep everything
forever in raw form.
```

History must preserve:

- retention decisions
- summaries or replacements as derived facts
- deletion or redaction provenance
- enough semantic continuity to explain what changed

History may omit:

- raw secrets
- bulky outputs
- expired operational logs
- redundant snapshots

Expected surface:

- retention/audit view
- "raw unavailable, summary retained" markers
- policy explanation

If only the current transcript existed:

- forgetting is just disappearance
- the user cannot tell whether absence means never happened, deleted,
  summarized, or lost

## Implied Storage Pressures

- History needs scopes: project, task, transcript, epoch, selected lineage, and
  time window.
- Active work must stay cheap; ancient history cannot be mandatory for every
  step.
- Raw operational history and durable semantic history need different
  retention rules.
- Identity cannot be only global message ids; selected and aligned history
  matters more.
- Branches, independent roots, and cross-project joins need explicit selection.
- Corruption should be isolated to a source or scope where possible.
- Summaries and indexes should be derived, provenance-linked, and discardable
  or replaceable.
- Published or shareable history should be a projection, not the raw local
  harness log.

