# 511 Test Surface Modernization (Remove Legacy Compatibility Adapters)

## Why

Recent daemon/step latency instrumentation surfaced that several tests still monkeypatch legacy module-level compatibility surfaces (`toas.cli.*`, `toas.step.Settings`) rather than current canonical seams. We added adapters to keep stability, but they increase maintenance drag and hide real interface boundaries.

## Goal

Port tests to current runtime surfaces so compatibility adapters can be removed without losing coverage or confidence.

## Scope

- migrate tests away from patching legacy compatibility exports in `toas.cli` and `toas.step`
- patch canonical modules/seams directly (`toas.llm`, daemon module, injected dependencies)
- remove now-unnecessary compatibility adapters once tests are migrated
- keep behavior and coverage expectations unchanged

## Acceptance

- no tests depend on `toas.cli` compatibility `__getattr__` for llm/daemon symbols
- no tests depend on `toas.step.Settings` module-level compatibility export
- compatibility adapters are removed (or reduced to zero legacy test dependencies with explicit rationale)
- `uv run pytest` passes

## Notes

- Stage this as a follow-up to `510` so latency/perf work can stay merged while test surfaces are modernized incrementally.
