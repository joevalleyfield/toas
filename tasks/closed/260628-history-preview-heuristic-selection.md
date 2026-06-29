Filed as: 260628-history-preview-heuristic-selection
FKA:
AKA: history preview line selection; common-surface preview heuristics; low-signal wrapper skipping
Legacy index:

keywords: surface, implementation, historical, usability, history, preview, heuristics, heads

Parent: `260627-history-surface-user-intent-alignment`
Related: `260628-history-root-to-head-lineage-contract`; `260628-durable-derived-history-previews`

# History Preview Heuristic Selection

## Current Reality

History-facing common surfaces such as `heads` and lineage-oriented views still
rely heavily on cheap first-line previews from message content.

That keeps the surface fast and substrate-honest, but it often produces low
operator value when the first visible line is mostly wrapper material:

- fenced block openers such as ````yaml`
- `## RESULT`
- blank lines
- transcript boilerplate or shell-shaped scaffolding

The result is not that previews are imperfect in a tolerable way. The result
is that some rows become actively unhelpful even though the underlying message
contains a much better short preview a line or two later.

## Desired Reality

Preview-bearing common surfaces should keep their current cheap/no-extra-model
runtime behavior while selecting more useful message previews from existing
content.

The heuristic version should:

- stay deterministic and cheap
- avoid hidden semantic rewriting
- prefer the first substantive operator-facing line over wrapper noise
- degrade gracefully when a message really does have no more useful preview

## Focus

- define which wrapper or low-signal lines should be skipped
- decide whether preview extraction should stay purely "first substantive line"
  or allow a tiny synthesized fallback from nearby content
- identify which surfaces share the heuristic preview logic (`heads` first, and
  possibly sibling lineage/topology surfaces if they use the same preview seam)
- keep tests tight so preview tuning remains intentional instead of drifting

## Candidate Heuristics

- ignore blank leading lines
- ignore code-fence openers/closers
- ignore `## RESULT`
- ignore transcript scaffolding that is structurally common but not preview-useful
- fall back to the true first line only when no better substantive line exists

## Exit Evidence

- [x] at least one common history-facing surface uses the improved preview
  heuristic
- [x] obvious wrapper-noise previews are replaced by more useful substantive lines
- [x] unchanged cases stay stable where the old first-line behavior was already
  good enough
- [x] focused tests capture both wrapper-skipping wins and important non-regression
  cases

## Decision

Closed the first implementation slice with a deterministic `heads` preview
heuristic in `toas.runtime.history_view_edges.head_first_line`.

The selector remains cheap and non-semantic: it scans existing message content
for the first operator-facing line, skipping leading blank lines, fenced-code
markers, and `## RESULT`. If the message contains no better substantive line,
it falls back to the original first line so all-wrapper content remains honest
rather than synthesized.

This deliberately leaves richer transcript-scaffolding rules and durable
derived previews to future focused follow-ons.

## Closure

Closed 2026-06-28 after `heads` adopted the heuristic and focused edge tests
captured wrapper-skipping plus fallback behavior.

Verification:

```text
./.codex-local/bin/uvt run python scripts/targeted_coverage.py --cov toas.runtime.history_view_edges --fail-under 100 --max-missing-files 0 -- tests/test_runtime_history_view_edges.py -q
4 passed

./.codex-local/bin/uvt run pytest tests/test_operator_api.py -q --no-cov
34 passed
```
