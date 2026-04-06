## Goal

Expose the message lineage walk as an operator-facing CLI surface, and enrich `toas heads` with depth, turn counts, and provenance markers.

## Why Now

Provenance (`292`, `293`) makes lineage walks richer: the ancestry path now carries creation-time attribution. The byte-offset index (`294`) makes per-hop cost acceptable at scale. With both in place, a useful inspection surface can be built without forcing a full event log scan on every command.

## Scope

**`toas heads` enrichment**:

- current output: bare list of head node IDs and roles
- enriched output: depth from root, turn count (user/assistant alternations), provenance breakdown (how many `llm_generated`, `user_authored`, `user_correction`, `adopted` nodes in the chain)
- format: tabular or structured; operator-readable at a glance

**`toas ancestry <message_id>`** (new subcommand):

- walks the parent chain from the given message back to the root
- prints each node: ID, role, content preview, provenance source
- `--depth <n>`: limit walk depth
- `--full`: show full content, not just preview

**Provenance markers in output**:

- `llm_generated` → `[G]`
- `user_authored` → `[U]`
- `user_correction` → `[C→<corrects_id>]`
- `adopted` → `[A]`
- unknown/absent → `[?]`

## Intended Inputs

- `message_lineage()` in `graph.py`
- provenance attributes on message nodes (written by `292`, `293`)
- byte-offset index for cheap per-hop access (`294`)
- existing `toas heads` output path

## Intended Outputs

- enriched `toas heads` output with depth, turn counts, provenance breakdown
- `toas ancestry <message_id>` with depth limit and full-content option
- provenance markers in ancestry output
- tests covering: enriched heads output, ancestry walk to root, depth limit, provenance markers on each source type, graceful handling of nodes without provenance

## Non-Goals

- no diff between branches (that is `296`)
- no graph visualization
- no modification of message content or structure
