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

That gap is more obvious after a surface-by-surface naive-user audit of
`heads`, `history`, `transcript`, `llm-input`, `rebuild`, and `graph`.
Before fail-closed refusal landed, those commands could give several plausible
but mutually inconsistent answers from the same damaged history. Now that they
refuse together, the next user-facing question becomes:

```text
okay, history is corrupt; what can I still safely inspect or extract?
```

That is especially important because the six surfaces serve different user
intent even when they are all "history-facing":

- `transcript` and `llm-input` are projection surfaces a user may want to
  salvage into a human-usable conversation slice
- `heads` and `graph` are topology/branch-shape surfaces a user may want for
  disambiguation
- `history` is the fastest coarse audit surface and should likely become the
  easiest place to point users toward recovery affordances
- `rebuild` is a mutating surface, so any recovery-adjacent use must be
  especially explicit about refusal, unsafe modes, and operator intent

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

It should also explain itself in terms a naive operator can act on:

- what failed
- which normal surfaces are intentionally refusing
- which recovery surface to run next
- what kind of result that recovery surface can and cannot guarantee

## Focus

- define one or more explicit recovery surfaces separate from normal `heads` /
  `history` / `transcript` behavior
- decide how refusal output on the normal surfaces should hand users off to the
  recovery lane without dumping them into internals-only terminology
- decide whether the first recovery slice should be structured diagnostics,
  transcript extraction, disambiguation tracing, or some narrow combination
- preserve the append-only evidence that helps explain how corruption evolved
- keep salvage mode visibly unsafe/diagnostic rather than silently permissive

## Concrete Pressure From The Audit

The six-surface exploration suggests a likely recovery priority order:

1. structured `fsck` diagnostics that identify the exact integrity failure and
   name candidate next actions
2. duplicate-id / parentage disambiguation views that help an operator
   understand competing lineage shapes
3. recovery-only transcript or head extraction over explicitly chosen
   candidate lineages
4. only later, any restaging/recombination flow that writes a fresh canonical
   journal

The audit also suggests a messaging constraint:

- the new fail-closed behavior is correct, but a refusal-only experience is
  still incomplete if the operator cannot tell whether they should inspect
  topology, salvage transcript text, or abandon the damaged journal entirely

## Candidate Directions

- `fsck --json` or similar structured corruption inventory
- human-readable `fsck` output that can be surfaced directly from refusal
  paths, possibly with "try next" hints
- recovery-only head/transcript extraction over candidate lineages
- duplicate-id disambiguation tracing showing first-seen versus later repeats
- recombination tooling that can restage extracted material into a fresh
  journal, only after explicit operator choice

## Exit Evidence

- one bounded recovery-tooling proposal with explicit command shape and safety
  framing
- explicit mapping from normal-surface refusal to recovery affordance
- examples proving corrupt history can still yield useful extracted data
  without weakening default fail-closed behavior
- explicit notes on which salvage heuristics are acceptable because of
  append-only evidence, and which would overclaim certainty
