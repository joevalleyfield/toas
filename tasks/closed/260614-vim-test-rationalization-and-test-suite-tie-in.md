Filed as: 260614-vim-test-cost-audit
FKA: 260614-vim-test-cost-audit
AKA: vim tests; test suite cost; stdio contract tests; test performance; vim test rationalization; test-suite tie-in
Legacy index: 688

keywords: tooling, hardening, historical, performance, vim, test

Parent: `260614-architecture-follow-through-coordination`

# Vim Test Rationalization And Test-Suite Tie-In

Rationalize the Vim test surface so the active test suite keeps the highest-value production-facing coverage without dragging along stale demo harnesses or dormant plugin fixtures.

## Why Now

This started as a cost audit, but the more important question turned out to be which Vim tests still deserved to count in the active suite at all. Once the worst wall-clock suspicion no longer held, the better debt payoff was to retire stale harnesses, keep the live plugin/runtime checks, and tie the highest-value dormant plugin-surface cases into pytest-visible verification.

## Scope

- Confirm where Vim-related wall-clock time actually goes in the default suite
- Retire stale or demo-heavy Vim harnesses that no longer protect meaningful production behavior
- Keep or add active pytest-visible checks for the real Vim plugin/runtime surface where the behavior is still worth protecting
- Promote the highest-value dormant `.vader` plugin-surface cases into the active test suite when they cover real production-facing behavior
- Leave transport-pump micro-behavior and archive/demo fixtures below the line unless a concrete plugin-only risk justifies promotion

## Out of Scope

- Reviving the old experiment harnesses for their own sake
- Promoting every dormant `.vader` asset regardless of value
- Broad Vim/plugin feature work unrelated to test-surface rationalization

## Done When

- The task records the real conclusion about Vim-test cost in the default suite
- Stale or demo-heavy Vim harnesses are retired or explicitly left behind as archive/reference material
- The highest-value production-facing Vim plugin behaviors are tied into active pytest-visible coverage
- The remaining dormant Vim fixtures are explicitly understood as lower-value archive/transport cases unless a new concrete risk changes that judgment

## Closure

- Closed on 2026-07-09 after the stale Vim experiment harnesses were retired,
  the highest-value plugin-surface cases were promoted into active pytest
  coverage, and the remaining dormant `.vader` assets were intentionally left
  as lower-value archive/reference material.

## Audit Notes

### 2026-07-07 snapshot

- Default suite timing is already much healthier than this task's original
  framing implied: `./.codex-local/bin/uvt run pytest tests --durations=30 -q`
  completed in 13.62s with only two dedicated Vim driver tests in the top
  cluster:
  `tests/test_vim_driver_phase2_async.py::test_vim_driver_phase2_async_smoke`
  at 1.23s and `tests/test_vim_driver_contract_plugin.py::test_contract_plugin_burst`
  at 0.57s.
- The heavier wall-clock costs now sit mostly in non-Vim host-stdio
  integration tests, not in the legacy Vim-driver cluster.
- The default run no longer carries a separate Vim-experiment quarantine.
  Only tests that still serve the real plugin/runtime surface should remain in
  the suite at all.

### Decision

- Retire the old phase-driver `vim_experiment` cluster rather than keeping a
  collection of one-off harnesses that mostly duplicate lessons now covered by
  runtime host-stdio tests and current plugin-surface Vader tests.
- Keep the lightweight real-Vim checks that still touch live surface behavior,
  especially `tests/test_vim_driver_phase2_async.py` and
  `tests/test_vim_driver_contract_plugin.py`.
- Prefer new Vim coverage to land either as current plugin-surface tests under
  `tests/vim/*.vader` or as narrowly scoped runtime/host integration tests,
  not as additional bespoke phase drivers.

### Current assessment

- The broad "Vim tests dominate suite wall-clock time" claim is no longer
  true for the default verification path.
- The right debt paydown here was test-surface cleanup: retire stale demo
  harnesses, keep live plugin checks, and bias future effort toward the actual
  Vim plugin surface.

### Follow-through landed

- Added pytest-visible production-surface Vim checks instead of reviving the
  retired phase drivers:
  `tests/test_vim_plugin_local_host_prompt_progress.py` exercises real
  local-host plugin rendering of streamed prompt-progress plus answer output
  against a fake LLM backend, and `tests/test_vim_plugin_real_host_smoke.py`
  covers a narrow real-host end-to-end success path.
- The follow-on audit also confirmed a broader testing posture issue: many
  `.vader` plugin-surface assets are useful reference material but are not
  part of the active pytest verification path, so the highest-value ones
  should be promoted into pytest-visible real-Vim checks over time.
- Those additions exposed a real plugin gap: `ToasWatch --follow` in the
  local-host path was not rendering `prompt_progress` events even though the
  timer-driven watcher path already knew how to track them. The plugin now
  renders those progress events consistently in the manual follow path too.
- Added another pytest-visible Vim plugin guard for malformed streamed
  transcript finalization:
  `tests/test_vim_plugin_local_host_hallucinated_follow_on.py` exercises the
  success-finalization path that previously skipped leading assistant/tool-call
  prelude text whenever a later fake `## RESULT` or transcript marker
  appeared. The plugin now preserves that leading assistant/tool prelude and
  trims hallucinated follow-on turns instead of canonizing them.
- Promoted two more dormant `.vader` plugin-surface cases into active pytest
  coverage via `tests/test_vim_plugin_local_host_projection_cases.py`:
  one keeps the raw tool-result scope-marker path honest, and the other keeps
  runtime projection-lane rendering from regressing into assistant fallback
  text. That continues the higher-value pattern of turning real Vim surface
  behaviors into active checks instead of preserving a larger archive of
  unexecuted demos.
- Finished the final worthwhile follow-watch promotions from the dormant Vim
  archive: `tests/test_vim_plugin_local_host_follow_edge_cases.py` now covers
  resubscribe event-seq dedup, stream-policy persistence across resubscribe,
  and cancelled terminal convergence through the real Vim plugin surface.
  At this point the remaining `.vader` assets skew more toward transport-pump
  micro-behavior or demo/archive value than toward high-leverage production
  plugin behavior.
