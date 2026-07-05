# Root Divergence Salvage Script

Filed as: 260704-root-divergence-salvage-script
FKA:
AKA: root prompt duplicate branch salvage; repeated transcript adoption recovery
Legacy index:

Related: `260704-root-divergence-sentinel-parent`; `260627-history-recovery-tooling`; `260627-history-surface-user-intent-alignment`

keywords: tooling, implementation, historical, correctness, history, graph, recovery, salvage

## Problem

The root-divergence parent bug can produce many duplicate branch starts under
the stale first message. The real observed journal is too large and too
personal to use as durable test material, but the compact shape is enough to
exercise a recovery tool:

- old first message parented to virtual root sentinel `n0`
- repeated identical replacement first messages parented to that old first
  message
- each replacement starts a branch that may contain the useful transcript
  suffix

## Goal

Build an output-only salvage helper that recognizes this shape in a small
synthetic fixture and emits a repaired copy where the selected duplicate
replacement branch starts at the virtual root sentinel. The helper must not
mutate the source journal.

## New Requirements

- Build an equivalence map across repeated root-divergence materializations.
- Treat messages as duplicate replay noise only when role/content match and
  their parents are already equivalent.
- Preserve real divergences:
  - the stale original root remains as an abandoned branch
  - any non-equivalent children under equivalent parents remain as branches
  - divergent descendants are reparented to the canonical equivalent parent
    when that is provable
- Remap side-car records through the equivalence map:
  - `related_to`
  - `payload.message_id`
  - `payload.node_id`
- Annotate remapped records with salvage provenance instead of silently
  rewriting references.
- Keep ambiguous/unmapped side-car records out of the repaired journal unless
  they are directly tied to preserved messages.
- Produce enough report data to distinguish:
  - collapsed duplicate ids
  - canonical ids
  - preserved divergence ids
  - remapped side-car counts
  - unmapped side-car counts

## Acceptance

- A compact fixture with old root plus repeated identical replacement-root
  siblings is detected.
- The canonical replacement branch is emitted with its first parent rewritten
  to `n0`.
- The stale original root is preserved as an abandoned branch.
- Real non-equivalent branch children under equivalent parents are preserved
  and reparented to canonical equivalent parents.
- Duplicate replay messages are omitted from the repaired message slice.
- Non-message records related to kept messages are retained.
- Non-message records related to duplicate replay messages are remapped to
  canonical ids when equivalence is provable.
- Unrelated or ambiguous non-message records are not overclaimed as salvaged.
- A no-candidate journal exits cleanly as a dry diagnostic.
- Tests avoid using the real 22MB journal.

## Progress

- 2026-07-04: Added `toas.history_salvage` with output-only root-divergence
  duplicate detection and repair-copy emission.
- 2026-07-04: Added `scripts/salvage_root_divergence.py` as a thin wrapper
  around the pure salvage core. It prints diagnostics and writes only when
  `--output` is supplied.
- 2026-07-04: Added compact synthetic tests for the observed broken shape:
  stale root, repeated identical replacement-root siblings, useful suffix,
  related non-message records, and unrelated records.
- 2026-07-04: Expanded the salvage core around an equivalence map. It now
  collapses only replay messages with matching role/content under equivalent
  parents, preserves the stale root and non-equivalent divergent children, and
  remaps side-car references with salvage provenance.
- 2026-07-04: The real journal rich salvage dry run reports 209 canonical
  messages, 13 preserved divergent messages, 19,806 collapsed duplicate
  messages, 267 remapped side-car records, and 392 unmapped/unrelated records.

## Verification

- `./.codex-local/bin/uvt run python scripts/targeted_coverage.py --cov toas.history_salvage --fail-under 100 --max-missing-files 0 -- tests/test_history_salvage.py -q`
  - 3 passed, 100% targeted coverage
- `./.codex-local/bin/uvt run pytest`
  - 2603 passed, 17 deselected, 100% coverage
- Smoke run against `/tmp/toas-root-salvage-fixture.jsonl`:
  - selected stale root `n1`, replacement start `n3`, head `n4`
  - wrote repaired JSONL with `n3` parented to `n0` followed by `n4`
- Real journal candidate run:
  - command wrote `/Users/tim/Documents/.toas/events.salvaged-root-divergence.jsonl`
  - selected stale root `n1`, replacement start `n19820`, head `n20028`
  - kept 209 message events and 211 total records
  - output size is 224,256 bytes with one `You are collab` occurrence
  - `fsck_logical_history` reported ok with 0 fatal and 0 warnings
  - projected transcript is 188,855 bytes; the live transcript's one extra
    parsed block is the projected final `write_file` result, represented in the
    salvaged journal by related tool records rather than a message node
- Rich real journal candidate run:
  - command wrote
    `/Users/tim/Documents/.toas/events.salvaged-root-divergence-rich.jsonl`
  - output size is 635,861 bytes with 506 records
  - record mix: 122 user messages, 100 assistant messages, 98 `llm_call`,
    93 `tool_request`, and 93 `tool_result`
  - 267 records have salvage remap provenance
  - `fsck_logical_history` reported ok with 0 fatal and 0 warnings

## Outcome

Closed on 2026-07-04.

The salvage path is intentionally output-only: it detects the compact
root-divergence duplicate-branch shape, builds an equivalence map for repeated
materializations, emits a repaired copy with the chosen replacement branch
rooted at `n0`, and preserves/remaps side-car records only when the mapping is
provable.

The helper remains a recovery tool, not a normal history projection path. It
does not mutate the source journal and does not make broad claims about
unrelated corrupt-history shapes.
