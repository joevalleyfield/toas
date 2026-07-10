Filed as: 260614-vim-test-cost-audit
FKA:
AKA: vim tests; test suite cost; stdio contract tests; test performance
Legacy index: 688

keywords: tooling, hardening, active, performance, vim, test

Parent: `260614-architecture-follow-through-coordination`

# Vim Test Cost Audit

Audit the vim driver test suite to determine whether the tests are as cheap as they could be given what they're actually verifying.

## Why Now

The vim tests dominate suite wall-clock time. Before accepting that cost as necessary, we should verify that the test structure isn't paying for setup/teardown or subprocess overhead that exceeds what the assertions actually require.

## Scope

- Profile which vim test files/cases consume the most time (`pytest --durations=20`)
- For the slowest tests, examine what they're actually asserting vs. what infrastructure they spin up
- Ask: could the same behavioral guarantee be achieved with a lighter fixture (mock subprocess, in-process call, smaller event sequence)?
- Identify any tests that are sleeping or using fixed timeouts where event-driven waits would suffice
- Flag tests that are acceptance-adjacent in cost but not marked `acceptance` (and thus always run)

## Out of Scope

- Changing what is verified, only how cheaply it can be verified
- Vim driver behavior changes

## Done When

- A short written summary of where the time goes and which tests (if any) have optimization headroom
- Any quick wins landed; slower restructuring logged as follow-on tasks

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
