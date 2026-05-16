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
