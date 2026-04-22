## Goal

Reduce `src/toas/daemon/__init__.py` facade weight by extracting remaining server/bootstrap ownership into focused daemon modules.

## Why Now

`code_survey` still reports `daemon/__init__.py` at `556` lines after prior handler/run-store extractions; the package entrypoint should remain a transition facade, not a new monolith.

## Scope

- extract remaining server/bootstrap/process wiring from `daemon/__init__.py` into focused modules (`daemon/server.py`, `daemon/bootstrap.py`, or equivalent)
- keep `python -m toas.daemon` and existing daemon command contracts stable
- preserve compatibility wrappers until direct call sites are migrated
- add focused tests for moved bootstrap lifecycle paths

## Intended Behavior

- daemon package root stays intentionally thin
- daemon lifecycle edits become localized to dedicated modules with clear ownership

## Constraints

- no transport/lifecycle semantic drift (start/stop/status/serve)
- preserve current fallback behavior and pid/socket cleanup contracts
- avoid opportunistic rewrites outside daemon package-facade reduction

## Done When

- `daemon/__init__.py` no longer holds the bulk of server/bootstrap logic
- moved lifecycle/bootstrap modules have focused tests
- full `uv run pytest` passes

## Result

- extracted daemon server/bootstrap lifecycle to `src/toas/daemon/server_lifecycle.py`
  - `serve_forever`, `start`, `stop`, `status`, `main`, healthcheck helpers
- retained `daemon/__init__.py` as compatibility facade with injected dependency wiring for test/monkeypatch parity
- added focused tests in `tests/test_daemon_server_lifecycle.py`
- verified parity with `uv run pytest` (pass)
