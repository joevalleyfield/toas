# History Storage Alternatives

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-history-surface-user-intent-alignment`

## Purpose

Compare possible TOAS history storage models from a use-case perspective. This
note is intentionally biased toward the current working hypothesis, but it does
not make a final decision.

The current preview bias:

```text
TOAS probably wants segmented append-only journals now, with content-addressed
ideas and summarized memory later. Artifact-first reality remains important
because TOAS history supplements repository artifacts rather than replacing
them.
```

## Evaluation Axes

- visible truth: can the user inspect what happened without trusting opaque
  machinery?
- recovery: can TOAS return to a trustworthy prior point?
- active-step performance: can ordinary step stay cheap and bounded?
- graph/history surfaces: can history support branches, lineages, previews, and
  cross-scope navigation?
- cold/archive behavior: can old history become stable, compressed, or scoped
  without changing current work semantics?
- deletion/redaction: can privacy and lifecycle policy be explicit?
- implementation complexity: how much machinery is required before the model
  is safe?
- user mental model: can the operator understand what is authoritative?

## One Forever Append-Only Log

Description:

```text
Every durable event goes into one append-only events file forever.
```

Visible truth:

- strongest simple story: open one file and inspect the record
- weakens once surfaces need filters, indexes, redactions, or derived summaries

Recovery:

- good if the file remains healthy
- poor failure isolation: corruption or size/pathology affects everything

Active-step performance:

- fine while history is small
- eventually forces every active operation to either scan too much or grow
  hidden indexing machinery

Graph/history surfaces:

- conceptually straightforward for one project-local history
- cross-task, cross-transcript, or cross-project selection becomes filtering
  over one giant namespace

Cold/archive behavior:

- weak; archival becomes external to the model or requires special offsets and
  compaction rules

Deletion/redaction:

- awkward in pure append-only form
- redaction can be represented as later events, but raw sensitive bytes remain
  unless the log is rewritten or encrypted by segment-like units

Implementation complexity:

- lowest initial complexity
- complexity leaks later into performance, retention, and filtering

User mental model:

- excellent early: "the history is in this file"
- degrades when that file becomes too large or too mixed for ordinary use

Use-case pressure:

- good bootstrapping model
- does not satisfy lifecycle, scope, and failure-isolation needs once history
  becomes a real substrate

## Segmented Append-Only Journals

Description:

```text
History is held in scoped append-only journals or segments. One hot journal is
active; sealed/cold journals remain inspectable and can carry manifests,
indexes, or lifecycle policy.
```

Visible truth:

- preserves file-backed inspectability
- visible truth now requires source/scope explanation, not just one file path

Recovery:

- strong if segments are ordered, source-scoped, and integrity-checked
- corruption can be isolated to a journal or segment

Active-step performance:

- strong; ordinary step can remain hot-local
- requires discipline so cold traversal does not sneak back into active paths

Graph/history surfaces:

- good fit for selected/aligned history
- supports independent roots, bounded windows, task/epoch scopes, and future
  cross-project joins
- requires explicit source-local identity and stitch/refusal semantics

Cold/archive behavior:

- strong; sealing, compression, manifests, and indexes all fit naturally
- old history can become stable without disappearing

Deletion/redaction:

- better than one forever log because lifecycle can attach to segment/source
  boundaries
- still needs explicit tombstones or redaction records for visible truth

Implementation complexity:

- moderate
- main complexity is semantic: scopes, journal-local ids, stitching, and
  refusal when alignment is missing

User mental model:

- understandable if presented as "hot working history plus sealed history"
- confusing if surfaces pretend segmentation is invisible while also changing
  behavior

Use-case pressure:

- best near-term fit for TOAS's current direction
- needs high-level proof models before claiming consistency

## Snapshot Plus Recent Journal

Description:

```text
Keep a compact snapshot of current state plus a recent append-only journal for
new changes.
```

Visible truth:

- weaker unless snapshots are richly provenance-linked
- user can see the recent journal, but old causality may be compressed away

Recovery:

- strong for fast resume to snapshot points
- weaker for forensic recovery before the snapshot unless raw history remains

Active-step performance:

- excellent; runtime reads compact state plus recent events

Graph/history surfaces:

- good for current state
- weaker for branch/history exploration unless snapshots retain graph shape and
  provenance

Cold/archive behavior:

- natural for compaction
- risks treating history as state replacement rather than visible record

Deletion/redaction:

- easier to drop raw history after snapshot
- difficult to explain what was lost unless snapshot provenance and tombstones
  are first-class

Implementation complexity:

- moderate to high
- requires snapshot schema, provenance, invalidation, and reconstruction
  semantics

User mental model:

- familiar database-ish model
- less aligned with "I can inspect the durable event record"

Use-case pressure:

- attractive later for performance and compaction
- risky as the primary model before visible-truth semantics are mature

## Artifact-First Storage With Minimal Event History

Description:

```text
Repository artifacts, task files, docs, transcripts, and commits are primary.
Event history records only enough to repair, explain, or supplement them.
```

Visible truth:

- strong for project outputs because artifacts are the truth users already
  inspect
- weak for operator process unless enough event history survives

Recovery:

- good when artifacts are sufficient
- weak when the user needs branch, consequence, or tool-call recovery

Active-step performance:

- good; runtime can ignore most old event history
- may need extra reconciliation between artifacts and event facts

Graph/history surfaces:

- limited unless artifacts carry or link to rich provenance
- branch and attempt navigation can disappear into file diffs and task notes

Cold/archive behavior:

- natural: artifacts follow repository lifecycle
- operational history may become disposable

Deletion/redaction:

- easier because less raw event history is retained
- risk: absence becomes ambiguous unless minimal history still records
  deletion/redaction facts

Implementation complexity:

- low to moderate
- complexity shifts to artifact conventions, provenance links, and task hygiene

User mental model:

- very natural for TOAS as a local coding harness: repo artifacts remain
  primary
- less satisfying when the operator wants to understand how work unfolded

Use-case pressure:

- TOAS already lives partly here because it supplements repository artifacts
- insufficient alone for recovery, accountability, and history navigation

## Content-Addressed Object Store

Description:

```text
Messages, tool facts, artifacts, summaries, and maybe projections become
addressed objects. Journals or refs point to objects and edges.
```

Visible truth:

- strong if object storage remains file-inspectable and refs are clear
- weaker if it becomes too abstract for ordinary inspection

Recovery:

- strong; immutable objects and refs can make reconstruction and dedupe robust

Active-step performance:

- potentially strong with refs/manifests
- may be overkill if required for every basic event

Graph/history surfaces:

- excellent identity story for content, occurrence, equivalence, and
  cross-project joins
- supports dedupe, alignment, summaries, and provenance well

Cold/archive behavior:

- strong; objects can be packed, retained, expired, or shared by policy

Deletion/redaction:

- complicated: content addressing makes leaked objects durable unless
  encryption, garbage collection, and redaction policy are designed carefully

Implementation complexity:

- higher than segmented journals, but not necessarily enormous if introduced
  as derivative identity first
- heavy if made the primary storage substrate too early

User mental model:

- harder than files-as-journals
- can become understandable if framed like "objects plus selected refs," but
  that is a bigger conceptual jump

Use-case pressure:

- very attractive for later identity, dedupe, and cross-boundary selection
- likely best introduced incrementally as hashes/manifests/equivalence
  material, not as an immediate replacement for journals

## Database-Backed Event Table

Description:

```text
Store events in a database table with indexes, constraints, and query
projections.
```

Visible truth:

- weaker than JSONL files unless export and inspection tooling are excellent
- stronger machine constraints can improve confidence but reduce immediacy

Recovery:

- strong if database durability, backups, and migrations are handled well
- weaker if local users cannot easily inspect or repair damaged state

Active-step performance:

- strong; indexes and queries are natural

Graph/history surfaces:

- strong; graph queries and filters are easier
- cross-scope views become query problems rather than file traversal problems

Cold/archive behavior:

- good with partitions or attached archives
- less transparent than sealed files

Deletion/redaction:

- easier operationally
- auditability depends on tombstone/event discipline and backup retention

Implementation complexity:

- moderate to high
- adds migrations, schema versioning, database repair, and export concerns

User mental model:

- familiar to engineers, but less aligned with TOAS's inspectable local harness
  spirit

Use-case pressure:

- attractive if query complexity dominates
- not the best first move while semantic storage contracts are still in flux

## Summarized Memory With Raw Expiration

Description:

```text
Raw history is retained temporarily. Long-term memory is mostly summaries,
decisions, derived previews, and semantic state.
```

Visible truth:

- risky unless summaries explicitly carry provenance and raw-expiration facts
- can preserve semantic truth while losing forensic truth

Recovery:

- good for reorientation
- weak for exact replay, detailed audit, or branch reconstruction after raw
  expiration

Active-step performance:

- strong; active context stays small

Graph/history surfaces:

- good for high-level navigation
- weak for precise graph lineage unless summaries preserve enough structure

Cold/archive behavior:

- excellent from a storage-cost perspective
- but cold archive becomes semantic memory, not raw operational truth

Deletion/redaction:

- strong privacy posture if designed intentionally
- summaries may accidentally retain sensitive facts after raw deletion

Implementation complexity:

- deceptively high
- needs provenance, freshness, uncertainty, redaction propagation, and clear
  user-facing semantics

User mental model:

- good if framed as "memory, not raw transcript"
- dangerous if users expect summaries to be evidence

Use-case pressure:

- important later for long-term ergonomics and personal work insight
- should be derived and explicit, not the base truth model

## Recommendation Pressure

The use-case pressure points toward this direction:

- keep repository artifacts primary for project truth
- use segmented append-only journals as the near-term event-history substrate
- keep ordinary active step hot-local
- treat cold/full history as selected, explicit, or diagnostically visible
- introduce content-addressed ideas first as derived hashes, manifests,
  equivalence classes, and provenance aids
- let summaries become derived semantic memory, not silent replacements for raw
  truth
- make deletion, redaction, and raw expiration explicit lifecycle events or
  policies
- postpone database-backed storage unless query needs clearly outrun the
  file-backed visible-truth model

This is recommendation pressure, not a final storage decision. The next proof
step should be scale-model scenarios that show which use-cases each model must
support or explicitly reject.

