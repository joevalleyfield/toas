Filed as: 260628-lint-type-routine-gate-cleanup
FKA:
AKA: advisory checks to gated checks; ruff mypy cleanup; lint type gate promotion
Legacy index:

keywords: tooling, hardening, follow-on, ci, checks, lint, typing

Parent: `260628-project-checks-and-ci-posture`

# Lint Type Routine Gate Cleanup

## Current Reality

`docs/checks.md` names `ruff` and `mypy` as advisory checks, not gated routine
checks, because both currently fail on existing backlog:

- `ruff check src tests` reports broad import sorting, unused import, upgrade,
  bugbear, and Python 3.10 syntax findings.
- `mypy` reports 11 errors across `llm.py`, `config.py`, `tools.py`, and
  `step.py`.

The green routine gate is currently default pytest with 100% coverage plus
replay-only acceptance.

### Ruff Inventory, 2026-07-03

`./.codex-local/bin/uvt run ruff check src --statistics --no-cache` reports
143 findings. `./.codex-local/bin/uvt run ruff check tests --statistics
--no-cache` reports 160 findings. The bulk is import organization, unused
imports, unused locals, and modernization rules.

Higher-signal non-import findings include:

- `src/toas/llm.py` has an `F821` annotation reference to `error.HTTPError`.
- `src/toas/operator_api.py`, `src/toas/cli_session_commands.py`,
  `src/toas/daemon/server_lifecycle.py`,
  `src/toas/runtime/operator_commands.py`, and
  `src/toas/runtime/step_generation_runtime.py` trip `PLR0913` argument-count
  checks.
- `src/toas/runtime/policy.py` assigns `os.environ` for config loading, which
  trips `B003`.
- `tests/vim/*` contains f-string quote reuse syntax that ruff treats as invalid
  under the configured Python 3.10 target.
- `tests/test_cli.py` contains repeated unused `settings` / `extra_body` locals
  in fake model callbacks.

A focused `ruff --select F` pass over the graph-sources files touched on
2026-07-03 passed, so the graph source selection slice did not add visible
undefined-name or unused-name failures.

## Desired Reality

Promote `ruff` and `mypy` into the gated routine check set once they are made
green without weakening the useful parts of either tool.

## Scope

- decide whether to fix findings, tune config, or split non-actionable checks
- make `./.codex-local/bin/uvt run ruff check src tests` green
- make `./.codex-local/bin/uvt run mypy` green
- update `docs/checks.md`, `scripts/check.sh`, and the parent task when both
  checks are ready to become gated

## Non-Goals

- hosted CI workflow design
- broad style churn unrelated to making the configured checks meaningful
- reducing the existing pytest coverage gate

## Exit Evidence

- [ ] `ruff check src tests` passes
- [ ] `mypy` passes
- [ ] `scripts/check.sh` includes lint/type checks by default
- [ ] `docs/checks.md` lists lint/type as gated rather than advisory
