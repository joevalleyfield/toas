Filed as: 260627-history-recovery-tooling
FKA:
AKA: corrupt history salvage tooling; history recovery commands; fsck recovery surfaces
Legacy index:

keywords: tooling, investigation, inception, usability, history, graph, transcript, provenance

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocked by: `260627-history-surface-corruption-semantics`; `260627-fail-closed-history-query-hardening`
Related: `260627-history-affordances-semantic-restaging`; `260626-transcript-parallelism-design-pressures`

# History Recovery Tooling

## Current Reality

TOAS now fails closed on fatal durable-history corruption for the normal
history-facing surfaces. That is the right default, but once corruption is
detected there is no explicit recovery lane for extracting useful information
from an append-only but damaged journal.

In practice, append-only ordering leaves a lot of potentially useful evidence:

- first-seen versus later duplicate message ids
- local lineage neighborhoods around conflicting records
- candidate head/frontier shapes that existed before later corruption
- transcript-shaped slices that may still be salvageable even if the journal is
  not trustworthy enough for normal projection commands

## Desired Reality

TOAS should keep normal history surfaces strict by default while offering a
clearly marked recovery/tooling path for corrupt durable history.

That recovery path should make data extraction possible without pretending the
journal has regained canonical integrity.

## Focus

- define one or more explicit recovery surfaces separate from normal `heads` /
  `history` / `transcript` behavior
- decide whether the first recovery slice should be structured diagnostics,
  transcript extraction, disambiguation tracing, or some narrow combination
- preserve the append-only evidence that helps explain how corruption evolved
- keep salvage mode visibly unsafe/diagnostic rather than silently permissive

## Candidate Directions

- `fsck --json` or similar structured corruption inventory
- recovery-only head/transcript extraction over candidate lineages
- duplicate-id disambiguation tracing showing first-seen versus later repeats
- recombination tooling that can restage extracted material into a fresh
  journal, only after explicit operator choice

## Exit Evidence

- one bounded recovery-tooling proposal with explicit command shape and safety
  framing
- examples proving corrupt history can still yield useful extracted data
  without weakening default fail-closed behavior
- explicit notes on which salvage heuristics are acceptable because of
  append-only evidence, and which would overclaim certainty
