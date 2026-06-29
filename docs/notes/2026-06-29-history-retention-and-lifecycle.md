# History Retention And Lifecycle

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-history-surface-user-intent-alignment`

## Purpose

Brainstorm retention classes for TOAS history. This note separates what the
system may need to remember from how storage is physically implemented.

The guiding tension:

```text
TOAS should preserve visible truth without pretending every raw byte must live
forever in one undifferentiated retention class.
```

## Raw Message Events

Why keep it?

- adopted transcript content is the spine of lineage, branch, projection, and
  recovery semantics
- message events explain what the operator and assistant actually committed to
  the durable conversation

How long might it need to live?

- active lineage: long-lived
- abandoned branches: policy-dependent
- published or task-significant branches: likely durable
- noisy/private experimental branches: maybe summarized then expired

Can it be summarized?

- yes, but summary should be derived from raw events and marked as such
- summary should not silently replace raw lineage unless a retention event says
  that happened

Can it be deleted?

- yes under explicit retention/redaction policy, but deletion changes what can
  be reconstructed
- deletion should leave a tombstone or provenance marker when future surfaces
  might otherwise imply the history never existed

What breaks if it is missing?

- transcript projection
- LCP reconciliation for that lineage
- branch navigation
- auditability of user/assistant decisions
- model-input reconstruction

Privacy or noise risk:

- may contain secrets, private thoughts, credentials, unreviewed generated text,
  and large amounts of low-value conversational noise

## Tool Calls And Results

Why keep it?

- proves what the runtime executed
- separates actual effects from assistant claims
- supports recovery, duplicate-execution prevention, audit, and debugging

How long might it need to live?

- terminal facts should live at least as long as the related message lineage
- raw payloads may have shorter retention than request/result status
- high-value validation/tool facts may become durable semantic evidence

Can it be summarized?

- yes, especially bulky stdout/stderr and search/listing output
- summaries should preserve status, command/tool identity, relevant paths, and
  enough diagnostic detail for trust

Can it be deleted?

- raw output can often be deleted or externalized
- request/result existence and terminal status are harder to delete without
  weakening accountability
- secrets may require redaction rather than retention

What breaks if it is missing?

- runtime may repeat consequences after restart
- review cannot prove tests or commands ran
- recovery loses failure diagnostics
- transcript may show results without durable backing

Privacy or noise risk:

- tool output can contain secrets, absolute paths, environment details, huge
  logs, vendor text, or irrelevant listings

## Model Calls And Results

Why keep it?

- records provider-facing input/output provenance
- helps diagnose weak-model protocol failures
- explains why a later assistant message exists
- supports replay-adjacent debugging and prompt evolution

How long might it need to live?

- active/debug period: useful raw
- after task closure: often summarized
- for protocol research or regressions: selectively durable

Can it be summarized?

- yes, raw request/response can often become a summary of prompt shape,
  selected context, model identity, outcome, and errors
- summaries should identify when exact raw input is unavailable

Can it be deleted?

- yes, especially raw prompts/responses that include sensitive material
- deleting raw calls weakens reproducibility and forensic debugging

What breaks if it is missing?

- cannot reproduce or inspect provider input
- weak-model failure analysis becomes guesswork
- prompt/policy drift is harder to understand
- assistant output may lose provenance

Privacy or noise risk:

- prompts may contain the whole working context, secrets, private text, and
  large copied artifacts
- responses may contain hallucinated sensitive material or useless verbosity

## Task State Changes

Why keep it?

- connects transcript activity to task lifecycle
- explains openings, pivots, blocking, closure, and follow-ons
- helps reorientation after time passes

How long might it need to live?

- usually long-lived for project memory
- raw operational details around state changes may be shorter-lived than the
  semantic transition

Can it be summarized?

- yes, state changes are already semantic summaries in many cases
- a task timeline can be compact while preserving durable meaning

Can it be deleted?

- rarely if tied to project/task truth
- mistaken task records might be superseded rather than erased

What breaks if it is missing?

- task files drift from actual operator work
- project planning loses causality
- later users cannot tell why a task moved or was closed

Privacy or noise risk:

- lower than raw messages/tools, but may expose private priorities, failed
  attempts, or internal strategy

## Decisions

Why keep it?

- decisions are the durable semantic memory of the work
- they explain why alternatives were rejected and what assumptions are active

How long might it need to live?

- long-lived, often longer than raw operational history
- should remain available while code/docs/artifacts depend on it

Can it be summarized?

- decisions are often already summary material
- later synthesis can roll several decisions into a higher-level design note,
  preserving links to source evidence when possible

Can it be deleted?

- should usually be superseded, amended, or marked obsolete rather than deleted
- deletion risks re-litigating the same design questions

What breaks if it is missing?

- implementation can contradict design intent
- contributors lose rationale
- future history stitching lacks semantic anchors

Privacy or noise risk:

- may reveal strategic thinking or private constraints, but usually lower
  noise than raw operational logs

## Artifacts

Why keep it?

- artifacts are the concrete outputs: files, docs, tasks, commits, generated
  assets, reports, and exported projections
- history needs to explain their provenance and validation

How long might it need to live?

- repository artifacts live under repository lifecycle
- generated/exported artifacts may be temporary, published, or archival
- provenance links may outlive the raw artifact copy

Can it be summarized?

- yes, artifact metadata and provenance can be summarized
- the artifact itself may remain in the repo while history keeps only links and
  change context

Can it be deleted?

- yes, according to artifact lifecycle
- deletion should not necessarily erase provenance that the artifact existed

What breaks if it is missing?

- review cannot connect history to project state
- task outcomes become vague
- reproducibility and artifact inspection may be lost

Privacy or noise risk:

- artifacts may contain secrets, generated mistakes, copyrighted material, or
  large binary/noisy content

## Indexes

Why keep it?

- speed up lookup, graph traversal, search, and projection
- support bounded operations over large histories

How long might it need to live?

- as long as fresh and useful
- fully rebuildable indexes can be short-lived caches
- expensive or derived indexes may have medium-term lifecycle

Can it be summarized?

- not usually; indexes are derived accelerators rather than narrative memory
- index metadata can describe coverage, freshness, and source scope

Can it be deleted?

- yes, if rebuildable
- stale or untrusted indexes should be discarded

What breaks if it is missing?

- performance and boundedness
- some surfaces may need to refuse or rebuild before answering
- semantic truth should not break if the index is genuinely derived

Privacy or noise risk:

- indexes may leak content, terms, paths, or source presence even when raw
  records are redacted

## Projections

Why keep it?

- projections are useful surfaces: transcript renderings, LLM input, graph
  views, published/shareable histories, previews
- retained projections can aid review and reproducibility

How long might it need to live?

- active projections may be ephemeral
- published/shareable projections may be durable artifacts
- provider-input projections may be retained for debug, then summarized

Can it be summarized?

- yes, especially graph previews and large context windows
- summaries must preserve that they are projections over a declared scope

Can it be deleted?

- yes if reproducible from retained source history
- no or not easily if it was published as an artifact or used as audit evidence

What breaks if it is missing?

- convenience and review snapshots
- exact provider-call replay if LLM input projection is gone
- published history links if the projection was externally referenced

Privacy or noise risk:

- projections can aggregate sensitive material from multiple sources into a
  more revealing bundle than any one event

## Summaries

Why keep it?

- compress long history into durable semantic memory
- support reorientation, search, retention, and cross-project insight
- let raw history age out without total forgetting

How long might it need to live?

- often long-lived if it replaces or indexes older raw material
- short-lived if it is just a preview cache

Can it be summarized?

- yes, summaries can be synthesized into higher-level summaries
- summary chains need provenance and freshness markers

Can it be deleted?

- yes, if raw source remains or summary is obsolete
- if raw source is gone, deleting summary may erase the remaining semantic
  memory

What breaks if it is missing?

- long-term navigation and reorientation
- retention story for expired raw history
- cross-history search and insight

Privacy or noise risk:

- summaries can distort, omit uncertainty, or preserve sensitive facts even
  after raw data is removed

## Redactions And Tombstones

Why keep it?

- make deletion/redaction explicit rather than silently rewriting the past
- preserve auditability without retaining sensitive content
- explain gaps in projections, indexes, and summaries

How long might it need to live?

- often as long as related history references might exist
- redaction metadata may need to outlive the redacted payload

Can it be summarized?

- yes, but the existence and scope of redaction should remain clear
- detailed reason text may be minimized for privacy

Can it be deleted?

- rarely, because deletion of tombstones makes absence ambiguous
- there may be privacy cases where even tombstone metadata must be minimized

What breaks if it is missing?

- users cannot distinguish never-existed from deleted, redacted, expired, or
  unavailable
- derived indexes/projections may appear inconsistent
- trust in visible truth weakens

Privacy or noise risk:

- tombstones can reveal that sensitive material existed
- detailed redaction reasons may leak what was removed

## Cross-Cutting Lifecycle Pressures

- Raw operational facts and durable semantic facts need different retention
  horizons.
- Deletion should be explicit when later interpretation would otherwise be
  misleading.
- Summaries should be provenance-linked and should not masquerade as raw truth.
- Indexes and previews should be treated as scoped, freshness-checked derived
  material.
- Published/shareable projections need a different lifecycle than private local
  harness history.
- Retention policy must account for secrets and noisy tool/model output early,
  not as an afterthought.
- Missing history should degrade into declared limits or refusals, not silent
  false reconstruction.

