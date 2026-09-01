Filed as: 260831-verbatim-staged-plan-restaging
FKA:
AKA: preserve heal continue; lossless failure continuation; source-fidelity restaging; verbatim yaml tail
Legacy index:

keywords: runtime, projection, implementation, active, correctness, usability, transcript, frontier, provenance, recovery

Depends on: `260803-first-failure-plan-recovery`
Related: `260621-staged-replay-healing-indent-only-mismatches`; `260830-exec-grant-policy-matchers`; `260627-history-affordances-semantic-restaging`

# Preserve Verbatim YAML During Failed-Plan Restaging

## Intent

Remove a high-friction recovery defect: when a staged multi-action YAML plan
fails, TOAS must reproduce the failed action and untouched forward tail from
the original authored YAML source, not from parsed objects reserialized by the
runtime.

The parsed plan remains authoritative for validation, execution, and locating
which operation failed. The original YAML body remains authoritative for
transcript recovery material.

> Parse semantics; preserve source.

## Confirmed recovery contract

For an original staged plan `A, B, C`, when `A` fails:

```text
failed executable frontier: source slice for A
staged continuation:        source slice for B, C
```

- The projected slices preserve authored bytes within their selected YAML
  operation spans: comments, quoting, block scalar style, key ordering,
  anchors/aliases, spacing, blank lines, and malformed-but-parseable tokens
  must not be normalized merely because recovery is being shown.
- The runtime may parse YAML to determine operation boundaries and execution
  semantics, but must retain enough source provenance to project the selected
  spans from the original fenced body.
- The failed frontier and tail must retain the existing recovery roles: the
  failed member is the sole ordinary editable executable YAML frontier; the
  unattempted suffix remains a visible `yaml staged` fence.
- A successful retry promotes the untouched tail for subsequent execution.
  Repeated failure/retry attempts at the frontier must not rewrite that tail.
- This task does not add or alter healing policy. Existing explicit mechanical
  heals, including `search_indent`, should continue to operate through the
  recovery path without making recovery itself lossy.

## Scope

- Trace the current first-failure projection path and identify where parsed
  plan data is converted back into YAML.
- Preserve original YAML source and map parsed operation positions to source
  spans at the appropriate parser/runtime seam.
- Project failed-frontier and staged-suffix material by source selection rather
  than YAML dump/normalization.
- Add focused regression coverage using presentation-sensitive YAML, including
  comments, quoting, block scalar formatting, ordering/spacing, and a visible
  malformed-but-executed token case where applicable.
- Update this task and generated workboard state with implementation evidence.

## Explicit boundaries

- Do not broaden this into a general recovery-affordance redesign.
- Do not change plan execution order, failure classification, durable record
  semantics, or the direct-user execution lane.
- Do not invent automatic healing heuristics, authorization-heal affordances,
  session identity, or multi-word command authorization in this slice.
- Do not require byte-for-byte preservation of outer recovery prose or fence
  delimiters; the preserved unit is the selected authored YAML operation span
  inside the original plan body.

## Acceptance criteria

- [x] A first, middle, and final action failure each reproduce the failed YAML
  action from its original source rather than a reserialized object.
- [x] The unattempted suffix is reproduced from its original source, in order,
  under `yaml staged`, with no key/schema translation or formatting rewrite.
- [x] Tests prove fidelity for comments, quoting, block scalar style, ordering
  or spacing, and blank-line-sensitive presentation where these occur within
  preserved spans.
- [x] An exact malformed-but-parseable command token visible in the original
  failed action remains visible in the retry projection, so recovery evidence
  is not cosmetically repaired or obscured.
- [x] Retrying the failed action never rewrites or reserializes its staged tail;
  successful retry still exposes the original tail as the next frontier.
- [x] Existing first-failure recovery behavior and relevant `/heal
  search_indent` coverage remain green.
- [x] Focused regression tests and the default suite pass.

## Implementation latitude

The implementer may choose the source-span mechanism and exact internal data
shape. Prefer the smallest change that makes source provenance explicit at the
YAML extraction/plan-execution boundary. If exact per-node spans are not
available from the current parser, a bounded source-preserving scanner that is
validated against the parsed operation sequence is acceptable; it must not
guess boundaries solely from indentation without parser-backed checks.

## Required completion evidence

- Before/after transcript fixtures showing presentation-sensitive source
  survives a first-failure restage.
- Tests covering first/middle/final failure and retry-to-tail promotion.
- A concise note naming the source-provenance seam chosen and why it preserves
  recovery output without changing execution authority.
- Focused test command/result and default suite result.

## Completion evidence

- Source seam: `src/toas/runtime/frontier_resolution.py` composes the authored
  YAML body and uses PyYAML sequence-node marks to derive parser-validated
  operation spans. `step_runtime.py` passes those spans into recovery
  rendering; parsed plans remain authoritative for validation and execution.
- Before fixture: a fenced three-operation plan containing an inline comment,
  quoted malformed-but-parseable shell token, and literal block scalar.
- After fixture: first, middle, and final failure projections retain the
  corresponding authored operation slice; the remaining slices stay under
  `yaml staged`, and retry-to-tail promotion retains the same source.
- Focused verification: `./.codex-local/bin/uvt run pytest
  tests/test_step_frontier.py tests/test_runtime_step_runtime.py -q --no-cov`
  — 140 passed.
- Lint verification: `./.codex-local/bin/uvt run ruff check
  src/toas/runtime/frontier_resolution.py src/toas/runtime/step_runtime.py
  tests/test_step_frontier.py tests/test_runtime_step_runtime.py` — passed.
- Default verification: `./.codex-local/bin/uvt run pytest -q` — 3059 passed,
  9 deselected; 100% coverage gate reached.
