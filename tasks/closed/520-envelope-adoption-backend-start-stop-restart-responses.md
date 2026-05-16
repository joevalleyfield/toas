# 520 Envelope Adoption For Backend Start/Stop/Restart Responses

## Objective
Extend envelope-compatible shaping to `backend_start`, `backend_stop`, and `backend_restart` daemon responses while preserving legacy response fields and CLI output behavior.

## Scope
- add envelope shaping for backend lifecycle mutation responses
- preserve legacy payload fields (`mode`, `managed`, `status`, `pid`, `detail`)
- add parity tests across success and failure/blocked paths

## Done When
- backend mutation responses include envelope payloads
- existing CLI output remains unchanged
- focused + full-suite tests pass

## Related
- `519` status/backend_status envelope adoption
- `470` operator API seam migration

## Progress
- completed response shaping in daemon handlers:
  - `src/toas/daemon/handlers.py`
  - `handle_backend_start` => envelope added
  - `handle_backend_stop` => envelope added
  - `handle_backend_restart` => envelope added
- preserved legacy payload fields and existing op names
- added/updated parity tests for backend mutation handler response shapes
- validated with full suite:
  - `uv run pytest -q -n 14`
