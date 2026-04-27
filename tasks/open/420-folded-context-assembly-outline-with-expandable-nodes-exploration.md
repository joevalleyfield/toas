## Goal

Explore a folded context-assembly strategy that projects prior work as outline/summary nodes plus explicit hidden-node counts, with selective expansion when needed.

## Why Now

Transcript growth is increasingly dominated by completed-work text that is rarely needed in full. This creates avoidable token pressure, especially on backends without strong prefix caching.

## Scope

- define a deterministic folded packet shape for model input with:
  - section outline entries
  - compact summaries
  - hidden-node/depth counters
  - stable expansion handles (IDs/paths)
- prototype a fold selector that prefers summaries by default and expands only high-signal branches
- define expansion triggers:
  - explicit reference by ID/path
  - recency/frontier proximity
  - contradiction/uncertainty signals
- add observability for packet composition:
  - folded vs expanded token budget
  - node counts by depth
  - expansion reasons

## Intended Behavior

- default model input is compact and structurally informative
- unresolved/important threads remain discoverable via explicit branch markers
- full raw text is still recoverable when expansion criteria are met

## Constraints

- no hidden semantic fork: folded packets must be derivable from durable history/lens artifacts
- deterministic assembly under fixed inputs
- preserve lineage clarity and replay safety

## Done When

- a prototype folded packet builder exists behind an explicit seam
- tests cover deterministic ordering and at least one expansion-trigger path
- docs include a practical operator workflow for inspecting folded vs expanded packets

## Notes

- likely integrates with `344` (context assembly), `356`/`362` (replay workflows), and `365` (checkpoint/tail scaling) rather than replacing them
- objective is not lossy summarization by default; objective is reversible compaction with explicit structure signals

## Progress

- 2026-04-26: Landed first folded-outline prototype seam in `runtime/context_assembly.py`:
  - added deterministic folded-outline builder/renderer (`build_folded_packet_outline`, `render_folded_packet_outline`) with explicit node shape (`title`, compact `summary`, `depth`, `hidden_ref_count`, visible refs).
  - added hidden-node and hidden-ref counters plus stable expanded-ref handles in output (`expanded_refs`).
  - added explicit expansion-trigger path via requested source-pointer refs (`expanded_refs` -> `expansion_reason=explicit_ref`).
  - added regressions for determinism, hidden-count reporting, and expansion-trigger behavior.
- 2026-04-26: Wired operator-facing folded inspection mode:
  - `/lens packet` now accepts folded inspection flags: `--folded` and `--expand <id,...>`.
  - `--expand` auto-selects folded mode and projects explicit expansion-reason markers in output.
  - updated slash-command usage/help surface for the folded packet command shape.
  - added handler regressions for folded output and explicit expansion-trigger rendering.
- 2026-04-26: Added folded-packet observability metrics:
  - folded outlines now include deterministic text-budget diagnostics (`folded_text_chars` vs `expanded_text_chars`).
  - added node-count-by-depth projection (`depth_counts`) alongside existing visible/hidden counts.
  - folded render output now surfaces these metrics in `/lens packet --folded` output.
  - added regressions for budget/depth metrics and rendering shape.
- 2026-04-26: Added practical operator workflow docs for folded inspection:
  - documented folded-vs-expanded inspection commands and handle-driven expansion (`/lens packet --folded --expand ...`) in `docs/capabilities.md`.
  - documented how to use budget/structure counters (`text_budget_chars`, `depth_counts`, `hidden_refs`) as decision signals before lens edits.
- 2026-04-26: Added frontier/recency expansion trigger prototype:
  - `ContextPacket` now carries deterministic recent-message handles (`recent_message_ids`).
  - folded outline builder now supports `expansion_mode=auto_frontier`, expanding source refs that intersect recent frontier IDs with reason tag `frontier_ref`.
  - folded render output now includes expansion-reason counts for observability.
  - added regressions for recent-ID packet capture and frontier-triggered expansion behavior.
