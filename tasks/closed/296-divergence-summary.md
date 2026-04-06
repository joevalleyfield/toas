## Goal

Given two heads, find their common ancestor and surface the first differing messages on each branch — the minimal operator signal for understanding where and why two session branches diverged.

## Why Now

Ancestry inspection (`295`) makes individual lineage walks cheap and readable. Divergence summary is the natural next step: once you can see each branch, you want to know where they split. Common ancestor computation is the foundation for any branch-level comparison, merge reasoning, or compaction targeting.

## Scope

**`toas diff <head_a> <head_b>`** (new subcommand):

- finds the common ancestor of `head_a` and `head_b` by walking both lineage chains until they converge
- prints: common ancestor ID and its content preview
- prints: first message after the common ancestor on each branch (the divergence point)
- for each diverging message: ID, role, content preview, provenance source
- `--full`: show full content at the divergence point, not just preview

**Output shape**:

```
common ancestor: n7  [U] "..."

branch A (head n15):
  n8  [G] "..."

branch B (head n12):
  n8b [U] "..."
```

(Branch-local IDs may differ; both show the message immediately after the shared ancestor.)

**Algorithm**: walk both lineage chains to lists; find the first shared ID. O(depth_a + depth_b) with the byte-offset index in place.

## Intended Inputs

- `message_lineage()` in `graph.py`
- byte-offset index for cheap ancestry walks (`294`)
- provenance attributes for source markers (`292`, `293`)
- `toas heads` for valid head resolution

## Intended Outputs

- `toas diff <head_a> <head_b>` with common ancestor and first-diverging-message summary
- `--full` flag for full content at divergence point
- tests covering: common ancestor found correctly, divergence point identified, provenance markers present, no-common-ancestor failure (disconnected graphs), same-head edge case

## Non-Goals

- no three-way merge
- no full branch diff (all differing messages, not just first)
- no automated merge or reconciliation
- no modification of the graph structure
