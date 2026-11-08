Filed as: 261107-test-suite-user-config-isolation
FKA:
AKA: user config test isolation; hermetic test home; conftest isolate home config
Legacy index:

keywords: tests, conftest, config, isolation, hermetic, environment

Parent: `260920-effective-policy-provenance-inspection`
Related: `261107-host-transcript-snapshots`; `261105-user-turn-and-result-telemetry-decorations`

# Test Suite User Config Isolation

## Status

Closed on 2026-11-07. An autouse fixture in `tests/conftest.py` isolates `HOME`
and `XDG_CONFIG_HOME` to a temporary directory for all test runs with teardown
cleanup. `./scripts/check.sh` passes 100% cleanly across all 3,880 unit tests,
17 acceptance tests, ruff, and mypy with 100.00% statement coverage.

## Intent

Ensure the TOAS test suite executes hermetically by isolating test processes from
the developer's personal machine configuration (`~/.config/toas/config.toml` and
`~/.toas.toml`), preventing developer preferences or dogfood configuration from
leaking into test expectations and breaking baseline verification.

## Context & Motivation

TOAS discovers configuration paths via `discover_config_paths(*, workdir, home)` in
`src/toas/config.py`, which defaults `home` to `Path.home()` (derived from `HOME` on
POSIX). In an unmocked test environment, `Path.home()` resolves to the developer's
real home directory.

When a developer sets configuration options in their personal `~/.config/toas/config.toml`
(for instance, `[session] telemetry_decorations = "compact"` for local dogfooding or editing),
unit tests that assert unannotated node structures, empty `metadata: {}`, or bare
`## RESULT\n\n` markers unexpectedly fail. In task `261107-host-transcript-snapshots`,
this environmental leak caused 9 unit test failures and 1 acceptance failure to be
misdiagnosed as pre-existing baseline failures in parent commit `aac9657e`.

While `tests/conftest.py` already includes guards against writing live workspace
sessions and isolates `TOAS_LLM_*` environment variables, it previously lacked
an isolation fixture for user-level configuration files.

## In Scope

1. **Hermetic Test Home Fixture in `tests/conftest.py`**:
   - Provide an autouse fixture isolating `HOME` and `XDG_CONFIG_HOME` to an
     isolated temporary directory for all pytest runs.
   - Ensure clean teardown so changes within isolated home do not persist across tests.
2. **Guards Verification in `tests/test_conftest_guards.py`**:
   - Add unit tests verifying that `HOME` and `XDG_CONFIG_HOME` point to the isolated
     environment and that global config discovery is shielded from the real user home.
3. **Full Suite Verification**:
   - Verify that `./scripts/check.sh` passes 100% cleanly (including the 9 previously
     blocked unit tests and all acceptance tests) while preserving 100.00% statement
     coverage.

## Out of Scope

- Changing production config discovery order or precedence in `src/toas/config.py`.
- Disabling user configuration for real CLI invocations outside tests.

## Acceptance Criteria

1. **Isolation**: When `~/.config/toas/config.toml` exists with arbitrary overrides,
   running `uv run pytest` ignores those user-level overrides by default.
2. **Pass Rates**: All 3,878+ unit tests and 17 acceptance tests pass without modifying
   or deleting `/Users/tim/.config/toas/config.toml`.
3. **Coverage**: 100.00% statement coverage maintained across the codebase under `./scripts/check.sh`.

## Implementation & Evidence

- **Conftest Isolation Fixture**:
  Added session fixture `_isolated_user_home` and autouse fixture `isolate_user_config`
  in `tests/conftest.py`, dynamically setting `HOME` and `XDG_CONFIG_HOME` to the
  isolated directory for each test and resetting test-created files via
  `_clean_isolated_user_home`.
- **Guard Tests**:
  Added `test_isolate_user_config_fixture_isolates_home_and_cleans_up` and
  `test_isolate_user_config_cleans_isolated_dir` in `tests/test_conftest_guards.py`.
- **Full Suite Verification**:
  `./scripts/check.sh` succeeded across 3,880 unit tests, 17 acceptance tests,
  `ruff check src tests`, and `mypy`, achieving 100.00% statement coverage
  (25,981 / 25,981 statements).
