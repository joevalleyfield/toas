Filed as: 260627-history-surface-corruption-semantics
FKA:
AKA: corrupt history surface behavior; duplicate-id surface audit; subcommand corruption semantics
Legacy index:

keywords: surface, investigation, inception, contract, history, projection, graph, transcript

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocked by: `260627-event-log-fsck-contract`
Blocks: `260627-fail-closed-history-query-hardening`
Related: `260627-history-affordances-semantic-restaging`; `260627-split-storage-rebuild-and-projection-parity`

# History Surface Corruption Semantics

## Current Reality

TOAS exposes multiple history-facing surfaces (`heads`, `history`,
`transcript`, `llm-input`, `rebuild`, `graph`), but they do not currently share
one corruption contract.

Under duplicate-id history, different surfaces normalize the same damage in
different ways:

- lineage/projection paths use last-write-wins id maps
- `graph` keeps the first occurrence and skips later duplicates
- `rebuild` uses a different storage read path from most sibling surfaces

That means a naive user can receive several mutually inconsistent answers from
the same corrupted durable history.

## Desired Reality

Each history-facing surface should have an explicit behavior contract under
fatal durable-history corruption:

- what integrity gate it consults
- whether it refuses, degrades, or reports partial results
- what error text or diagnostic summary it emits

The first goal is semantic clarity, not implementation.

## Focus

- enumerate behavior expectations for `heads`, `history`, `transcript`,
  `llm-input`, `rebuild`, and `graph`
- decide whether any surface may remain permissive under known corruption
- define consistency expectations across hot-only and logical-history reads
- capture acceptance-style examples for duplicate ids and related graph-shape
  failures

## Exit Evidence

- a surface-by-surface behavior matrix for fatal and non-fatal integrity issues
- examples showing the same corrupt history yields coherent refusal semantics
  across subcommands instead of silent divergence
- explicit notes on where rebuild mutation behavior needs stronger preflight

