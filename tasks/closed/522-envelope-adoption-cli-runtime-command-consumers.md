# 522 Envelope Adoption In CLI Runtime Command Consumers

## Objective
Adopt envelope-first (legacy-fallback) status extraction in remaining CLI runtime command consumers that read daemon lifecycle responses.

## Scope
- identify CLI paths still reading legacy-only status/detail fields
- apply shared extraction helpers with envelope-first fallback
- keep rendered operator output unchanged

## Done When
- targeted consumers read envelope-first while preserving legacy compatibility
- tests cover envelope-present and legacy-only responses

## Related
- `518` step/cancel consumer adoption
- `519` status/backend_status response adoption
- `520` backend mutation response adoption

## Progress
- completed consumer inventory; remaining path was backend lifecycle command output in `run_backend`
- adopted envelope-first fallback in:
  - `src/toas/cli_async_commands.py`
  - status now reads from `envelope.payload.status` when present
  - detail now reads from `envelope.payload.detail` when present
- preserved output strings and legacy fallback behavior
- added focused tests for envelope-preferred backend output rendering
