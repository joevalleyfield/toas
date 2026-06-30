# Scale-Model History Scenarios

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260627-split-storage-rebuild-and-projection-parity`; `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-history-surface-user-intent-alignment`

## Purpose

Define small, realistic TOAS history scenarios that can later become fixtures.
Each scenario is intended to test semantic behavior across runtime, operator
surfaces, storage scope, and integrity handling.

These are scale models, not implementation designs. They should stay small
enough to hand-inspect while still resembling real operator situations.

## Scenario 1: Hot-Only Active Lineage

Name:

```text
hot_only_active_lineage
```

User-facing situation:

- the user is working in a normal fresh TOAS session
- all current history is in the active hot journal
- no cold storage exists

Physical storage layout:

- `.toas/events.jsonl` contains one coherent message lineage plus any local
  tool/model facts
- `.toas/segments/` is absent or empty

Expected step behavior:

- ordinary step reconciles against hot history only
- continuation, branching, callable execution, and no-op behavior match the
  single-file baseline

Expected history behavior:

- `history` shows the selected root-to-head lineage
- `heads` sees leaf nodes in the hot graph

Expected transcript behavior:

- `transcript` renders the selected lineage into editable transcript form
- `RESULT` projections remain projections, not durable message events

Expected graph behavior:

- `graph` shows the hot message topology
- local ids are sufficient because there is only one source scope

Expected fsck behavior:

- valid source-local ids and parents pass
- duplicate ids or missing parents inside the hot journal are fatal

Expected refusal/warning behavior:

- no storage-scope warning is expected
- ordinary semantic refusals still apply for malformed frontier/tool state

## Scenario 2: Rolled History With Redundant Hot Context

Name:

```text
rolled_history_redundant_hot_context
```

User-facing situation:

- older task context has been sealed into cold storage
- the hot journal retains enough overlapping context for active work
- the user continues from the hot transcript without needing deep cold history

Physical storage layout:

- `segments/000001-events.jsonl` contains older root-to-mid lineage
- `.toas/events.jsonl` contains a restaged overlap plus newer hot continuation
- overlapping records may have the same content and local ids or may need
  explicit alignment rules, depending on the fixture variant

Expected step behavior:

- ordinary step uses the hot journal as authority
- step does not scan the cold segment merely because it exists
- duplicate physical occurrences caused by restaging do not produce duplicate
  active transcript turns

Expected history behavior:

- hot-scoped history can show the active lineage
- full/stitched history must either align the overlap or clearly state that the
  requested scope needs alignment

Expected transcript behavior:

- default transcript projection follows the selected active lineage
- cold-inclusive projection must not render overlapped content twice

Expected graph behavior:

- hot graph remains coherent on its own
- cold-inclusive graph may show source-qualified occurrences or a proven
  equivalence class for aligned overlap

Expected fsck behavior:

- each source is checked locally
- same local ids across sources are not source-local corruption

Expected refusal/warning behavior:

- no warning is expected merely because separate sources reuse local ids
- semantic stitched surfaces refuse if they cannot prove overlap alignment

## Scenario 3: Independent Hot Root After Rotation

Name:

```text
independent_hot_root_after_rotation
```

User-facing situation:

- old history exists, but the active hot journal intentionally starts a new
  independent root
- both old and hot histories may use local ids such as `n1`

Physical storage layout:

- `segments/000001-events.jsonl` contains one complete older lineage
- `.toas/events.jsonl` contains a separate root and active continuation
- the two sources have no proven parentage or alignment relationship

Expected step behavior:

- step continues from the hot root/lineage
- cold history does not influence active reconciliation

Expected history behavior:

- selected hot-lineage history shows the active lineage only
- full topology may show both independent roots if the surface supports that
  declared scope

Expected transcript behavior:

- transcript projection renders the selected hot lineage
- it does not prepend or stitch cold content by matching raw ids

Expected graph behavior:

- graph can show two source-local roots
- same local ids across sources must be source-qualified or otherwise disambiguated

Expected fsck behavior:

- each source passes if internally valid
- same local ids across sources are normal, not corruption

Expected refusal/warning behavior:

- stitched selected-lineage projection refuses if asked to treat both sources
  as one lineage without explicit selector/alignment evidence
- refusal language should say journal-local ids need alignment, not that the
  history is corrupt

## Scenario 4: Aligned Cold/Hot Continuation

Name:

```text
aligned_cold_hot_continuation
```

User-facing situation:

- hot history restages a boundary from sealed history and then continues
- the user expects old and new history to read as one coherent lineage when an
  explicit cold-inclusive view is requested

Physical storage layout:

- cold segment contains an older lineage ending at a boundary message
- hot journal begins with restaged boundary/context and then newer messages
- fixture carries enough content, parentage, or provenance for alignment to be
  provable

Expected step behavior:

- ordinary step uses hot-local authority
- step does not need cold traversal to continue

Expected history behavior:

- hot history works as a local active view
- cold-inclusive selected history can present one aligned lineage once proof is
  available

Expected transcript behavior:

- transcript projection over the aligned lineage renders each semantic turn
  once
- provider-facing projection still applies LLM-input rules separately

Expected graph behavior:

- graph can show source-qualified occurrences plus an alignment/equivalence
  relation, or a derived stitched view with clear identity semantics

Expected fsck behavior:

- source-local integrity passes
- same local ids across sources remain non-fatal

Expected refusal/warning behavior:

- no refusal if alignment proof is sufficient for the requested scope
- surfaces that cannot explain source qualification should refuse or narrow
  scope rather than emit storage warnings

## Scenario 5: Ambiguous Same Local Ids

Name:

```text
ambiguous_same_local_id_across_sources
```

User-facing situation:

- multiple journals contain the same local message ids
- there is not enough evidence to know whether they are restaged equivalents,
  independent roots, or unrelated imports

Physical storage layout:

- one or more cold segments and the hot journal contain overlapping id labels
- content and parentage are insufficient or contradictory for alignment

Expected step behavior:

- hot-local step may proceed if hot history is internally valid and
  self-sufficient
- step should not silently consult ambiguous cold history

Expected history behavior:

- hot-scoped history works
- cold-inclusive selected-lineage history refuses without a selector or
  alignment proof

Expected transcript behavior:

- selected hot transcript works
- stitched transcript refuses rather than rendering a guessed combined lineage

Expected graph behavior:

- topology may show source-qualified nodes if graph is explicitly in
  multi-source topology mode
- any view that implies one unified node identity must refuse

Expected fsck behavior:

- source-local validity determines fatality
- same local ids across sources do not produce warnings

Expected refusal/warning behavior:

- refusals explain that semantic stitching requires alignment or explicit
  selection

## Scenario 6: Source-Local Corruption

Name:

```text
source_local_corruption
```

User-facing situation:

- one journal source is malformed or internally inconsistent
- the operator needs diagnostics and recovery options without confusing this
  with ordinary cross-source id reuse

Physical storage layout:

- hot or cold source contains duplicate local ids, missing source-local parents,
  malformed message shapes, or invalid metadata
- other sources may be valid

Expected step behavior:

- if the hot source is corrupt, active step fails closed
- if only unrelated cold source is corrupt, hot-local step should not be
  blocked unless the requested operation crosses that cold scope

Expected history behavior:

- surfaces whose declared scope includes the corrupt source refuse or report
  diagnostics
- surfaces scoped to valid hot history may proceed when semantically safe

Expected transcript behavior:

- projection over a corrupt selected lineage refuses
- projection over an unaffected valid selected lineage may proceed if scope is
  explicit

Expected graph behavior:

- graph over the corrupt source refuses or marks the source as invalid
- graph over valid scopes should avoid pretending corrupt records are usable

Expected fsck behavior:

- fatal issues are reported with source/path/line where possible
- corruption is source-local, not inferred from same local ids across sources

Expected refusal/warning behavior:

- fatal corruption language is reserved for invalid source-local history
- refusal should distinguish corruption from missing alignment

## Scenario 7: Non-Message Facts Across Scopes

Name:

```text
non_message_facts_across_scopes
```

User-facing situation:

- history contains messages, tool requests/results, model calls, heads, binds,
  anchors, and projected result blocks
- operator surfaces must not confuse durable operational facts with message
  turns

Physical storage layout:

- cold and hot journals contain mixed message and non-message records
- tool/model facts may refer to message frontiers in their own source scopes

Expected step behavior:

- step uses relevant hot-local consequence facts to avoid duplicate execution
- non-message cold facts do not alter active frontier unless explicitly within
  selected authority scope

Expected history behavior:

- message lineage views show message events
- audit/debug views may include tool/model/control facts as separate records

Expected transcript behavior:

- transcript projection renders message turns and projected `RESULT` blocks
  according to projection policy
- projected results are not adopted as durable message events

Expected graph behavior:

- message graph remains distinct from operational fact graph
- richer topology may show fact edges without renumbering message events

Expected fsck behavior:

- message integrity checks ignore non-message records unless their shape
  affects declared integrity rules
- malformed non-message records may belong to a separate validation class

Expected refusal/warning behavior:

- warning/refusal should explain when an operational fact references a missing
  or ambiguous message occurrence
- message-surface projection should not fail merely because unrelated
  non-message facts exist

## Scenario 8: Raw Expired, Summary Retained

Name:

```text
raw_expired_summary_retained
```

User-facing situation:

- old raw operational history has been expired or redacted
- a derived summary, decision record, or tombstone remains
- the user needs to understand what can and cannot be reconstructed

Physical storage layout:

- sealed old raw records are absent, redacted, or tombstoned
- summary/decision/provenance records remain in a retained source
- indexes or projections that depended on the raw source may be stale or
  unavailable

Expected step behavior:

- active step proceeds if hot-local history is self-sufficient
- expired raw history is not treated as active reconciliation input

Expected history behavior:

- history surfaces show summary/tombstone limits when crossing the expired
  scope
- exact old lineage reconstruction refuses if raw lineage is unavailable

Expected transcript behavior:

- transcript projection cannot recreate redacted raw messages unless retained
  material explicitly includes them
- summary projection may be available as a different surface

Expected graph behavior:

- graph shows gaps, tombstones, or summary nodes according to declared mode
- graph must not invent missing raw edges from summary prose

Expected fsck behavior:

- tombstoned/expired scope is not corruption if retention policy explains it
- stale indexes over missing raw storage are invalid or discardable

Expected refusal/warning behavior:

- refusal distinguishes retention-limited unavailable history from corruption
- warning explains when only derived memory remains

## Scenario Selection Pressure

These scenarios should become fixtures before deeper implementation claims:

- hot-only behavior remains the regression baseline
- hot-local step authority must survive cold storage, ambiguity, and unrelated
  cold corruption
- same local ids across sources are normal until source-local rules are
  violated
- cold-inclusive surfaces need proof, source qualification, or refusal
- summaries and tombstones are semantic facts, not substitutes for raw lineage
  unless a surface explicitly asks for that mode
