Filed as: 260830-search-subprocess-output-guard
FKA:
AKA: search stdout None; ripgrep output guard; search retry failure
Legacy index:

keywords: tooling, hardening, historical, correctness, compatibility, search

Related: `260830-windows-test-session-path`

# Harden Search Subprocess Output Handling

Keep the search tool from turning an unusual subprocess result into an
unhelpful `AttributeError` while preserving the existing search contract.

## Current Reality

`run_search()` assumes `subprocess.run(..., capture_output=True, text=True)`
always provides string values for `stdout` and `stderr`. A Windows retry or
replay-shaped subprocess result can provide `None`, causing `.strip()` to fail
before the tool can return a bounded result or diagnostic.

## Desired Reality

Search treats absent captured output as empty output and keeps its result/error
shape stable. The guard is intentionally narrow; timeout ownership and any
replay-state explanation remain separate follow-up questions.

## Exit Evidence

- `stdout=None` is covered by a focused regression test.
- The search implementation guards both captured streams before stripping.
- Focused and full relevant test verification is recorded with the change.

## Completion Evidence

- 2026-08-30: `run_search()` now treats missing captured `stdout` and `stderr`
  as empty strings before stripping.
- 2026-08-30: Added regression coverage for both `stdout=None` success results
  and `stderr=None` failure results.
- 2026-08-30: `uv run pytest tests/test_tools_basic_ops.py tests/test_cli.py
  -q --no-cov` passes with 249 tests.
