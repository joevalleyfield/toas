Filed as: 260627-workboard-relationship-tree-builder
FKA:
AKA: workboard tree builder; relationship tree rendering; sync_workboard subtree view
Legacy index:

keywords: tooling, implementation, active, workboard, sync, graph, boundaries, usability

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
