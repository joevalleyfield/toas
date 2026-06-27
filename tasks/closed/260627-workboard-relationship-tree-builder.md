Filed as: 260627-workboard-relationship-tree-builder
FKA:
AKA: workboard tree builder; relationship tree rendering; sync_workboard subtree view
Legacy index:

keywords: tooling, implementation, historical, workboard, sync, graph, boundaries, usability

Related: `260524-exploratory-work-representation-model`; `260524-workboard-as-control-surface`; `260524-attention-focused-workboard-layout`

# Workboard Relationship Tree Builder

## Current Reality

TOAS task files now carry explicit relationship metadata:

- `Parent:`
- `Blocks:`
- `Blocked by:`
- `Related:`

That metadata is grep-walkable and documented in `tasks/README.md`, but the
current sync path does not build or render a task tree from it.

`tasks/scripts/sync_workboard.py` still regenerates only flat sections for:

- open tasks
- inbox items
- recent closures

The manually curated "Active Arc Map" in `tasks/WORKBOARD.md` is useful, but it
is prose-maintained rather than generated from relationship metadata.

## Desired Reality

The workboard sync path should have a real tree-builder affordance that can:

- parse relationship fields into explicit edges
- build a task tree or graph view for selected roots
- render a generated subtree section without replacing the flat open queue
- keep manual curation optional rather than mandatory for basic dependency
  visibility

## Scope

- parse `Parent:`, `Blocks:`, `Blocked by:`, and `Related:` into structured
  relationships
- define one generated tree/subtree section in `tasks/WORKBOARD.md`
- support at least root-oriented rendering for a selected task or small set of
  tasks
- preserve existing marker-driven flat sections
- make relationship rendering deterministic and grep/audit-friendly

## Non-Goals

- replacing the whole workboard with a hierarchical view
- implementing inferred dependencies
- bidirectional editing/control-surface behavior
- sophisticated ranking or prioritization logic

## Design Pressure

The affordance should help with active coordination work, especially where the
task inventory is intentionally flat but the dependency structure is not.

The likely first useful shape is:

- generated subtree for a chosen root task
- explicit display of `Parent:` and blocking edges
- minimal treatment of `Related:` so adjacency is visible without overwhelming
  the tree

This should remain compatible with separable manual triage sections and with
the existing flat "Open Queue" inventory.

## Design Choices

- First-root selection should come from a small manual root list embedded in
  `tasks/WORKBOARD.md`, so the generated tree stays intentional and editable
  without changing code.
- The generated relationship tree should replace the manually maintained
  `Active Arc Map` section, while preserving `Manual Triage` and the flat
  generated `Open Queue`.
- Tree indentation should be driven only by `Parent:` links in the first slice.
  `Blocks:` / `Blocked by:` should render as compact edge annotations, and
  `Related:` should remain a lightweight inline adjacency note.
- Repeated tasks reachable from multiple selected roots should render fully on
  first mention and as `@task-id` references thereafter so the output stays
  deterministic and loop-safe.

## Exit Evidence

- `sync_workboard.py` parses relationship fields into structured edges instead
  of only ignoring them in summaries
- `tasks/WORKBOARD.md` gains a generated subtree or arc section driven by task
  metadata
- the generated view is deterministic enough to audit by grep and review
- existing generated open/inbox/closed sections continue to work

## Notes

This is the concrete implementation follow-on for the already-landed task
relationship schema. It should not wait on broader control-surface or layout
ambitions before providing one useful generated dependency/tree view.

## Progress

- 2026-06-27: Locked the first implementation shape: manual root selection
  lives in `tasks/WORKBOARD.md`, the generated relationship tree replaces the
  prose-maintained `Active Arc Map`, and only `Parent:` creates indentation in
  v1 while blocking/related edges remain annotations.
- 2026-06-27: Implemented relationship parsing and generated tree rendering in
  `tasks/scripts/sync_workboard.py`, added marker-managed root selection in
  `tasks/WORKBOARD.md`, and verified the sync path with focused tests.

## Next Actions

- [ ] Polish generated relationship-tree labels and sync metadata (Generated tree still shows # heading fallbacks for some tasks and WORKBOARD.md keeps stale manual sync fields like Last Sync.)

## Done When

- relationship fields are parsed into structured task edges during workboard
  sync
- `tasks/WORKBOARD.md` renders a generated relationship tree from selected
  manual roots
- the flat open/inbox/closed generated sections still sync correctly
- focused tests cover relationship parsing, root extraction, and repeated-node
  rendering

## Completion Summary

The workboard sync path now parses task relationship fields and renders a
deterministic generated tree in `tasks/WORKBOARD.md` from a small manual root
set. The old prose-maintained active arc map has been replaced by marker-driven
generation, while the flat open, inbox, and recent-closure sections continue to
sync as before.
