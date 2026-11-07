Filed as: 261107-config-load-diagnostic-surfacing
FKA:
AKA: config parse errors; config load diagnostics; invalid toml warning; in-buffer config diagnostic
Legacy index:

keywords: config, toml, diagnostics, warning, operator, step, in-buffer, sources

Parent: `261107-branch-isolated-policy-state`
Related: `260920-effective-policy-provenance-inspection`

# Config Load Diagnostic Surfacing

## Intent

Surface configuration file parse and syntax errors (such as malformed TOML) to the operator
instead of silently discarding the file and falling back to defaults. Surface diagnostics
both explicitly upon config inspection (`/config`, `/config show`) and immediately in-buffer
at the tail of the step consequence when first encountered, deduplicated so subsequent steps
do not spam the transcript.

## Context & Motivation

When a discovered configuration file (e.g. `~/.config/toas/config.toml` or `<workdir>/.toas/config.toml`)
contains invalid syntax (such as unquoted strings), `load_file_config` in `src/toas/config.py`
previously caught all exceptions and silently returned `{}`. This caused TOAS to treat the
user's config file as non-existent and silently fall back to `default`, leaving the operator
without feedback as to why their configuration was not applying.

The system needs to:
1. Capture configuration load errors as structured diagnostics (`path`, `error`, `line`, `col`).
2. Surface diagnostics during `/config`, `/config show`, and `/config overview`.
3. Emit an in-buffer inert warning at the active frontier (tail of step consequences) when a
   step runs with broken configuration, checking `working` history so it only appears once per
   distinct error signature.

## In Scope

1. **Structured Config Loading with Diagnostics**:
   - Add structured diagnostic representations (e.g. `ConfigDiagnostic`).
   - Update config loading to preserve parse failures rather than silently swallowing them.
   - Update `resolve_runtime_generation_context` to capture diagnostics from all discovered config files.

2. **Config Sources & Inspection Tier**:
   - Carry diagnostics via `config_sources` (e.g. `sources["__config_diagnostics__"]`).
   - In `operator_command_config_help.py`:
     - Render a diagnostic section in `/config`, `/config show`, and `/config overview`.
     - In `/config show --sources`, annotate or display diagnostic notices.

3. **In-Buffer Step Consequence Tier**:
   - In `src/toas/runtime/step_runtime.py`, check if any config diagnostics are present.
   - Inspect `working: list[dict]` to check if an inert warning (`source=config.diagnostic`) with
     the matching diagnostic signature is already present in the active lineage.
   - If not present, append an inert warning block at the tail of `consequences` so it appears
     directly at the active frontier.

4. **Testing & QA**:
   - Unit tests for `load_file_config` diagnostic collection.
   - Unit tests for `/config show` displaying parse errors.
   - Unit tests verifying in-buffer warning emission at consequence tail and deduplication on
     subsequent turns.
   - Full `./scripts/check.sh` validation with 100.00% statement coverage.

## Out of Scope

- Modifying TOML syntax rules or auto-repairing broken TOML files on disk.
- Halting or fatal-crashing the runtime on configuration parse errors (fallback to defaults remains).

## Acceptance Criteria

1. **Syntax Error Capture**: Malformed TOML in any discovered config file produces structured
   diagnostic information containing file path, line, column, and error description.
2. **Explicit Inspection**: `/config` and `/config show` display the configuration diagnostic clearly.
3. **In-Buffer Frontier Warning**: Running a step with broken configuration emits an inert warning block
   (`source=config.diagnostic`, `potency=inert`) as the final item in the step's consequences.
4. **History Deduplication**: Subsequent steps on the same lineage do not re-emit the warning if the
   diagnostic signature is already present in `working`.
5. **Coverage & Checks**: Passes `./scripts/check.sh` with 100.00% statement coverage.

## Implementation Plan

1. **Phase 1: Config Diagnostic Data Model & Loader**
   - Define `ConfigDiagnostic` in `src/toas/config.py`.
   - Implement `load_file_config_with_diagnostics(path: Path) -> tuple[dict, tuple[ConfigDiagnostic, ...]]`.
   - Update `discover_config_paths` and runtime context assembly to collect diagnostics.

2. **Phase 2: Inspection Tier (`/config` & `/config show`)**
   - Plumb diagnostics into `build_config_sources`.
   - Update `operator_command_config_help.py` to render diagnostic sections.

3. **Phase 3: In-Buffer Frontier Warning Tier (`step_runtime.py`)**
   - Implement `_has_config_diagnostic(working, signature)` and append warning block at the tail of
     `consequences`.

4. **Phase 4: Verification & QA**
   - Comprehensive unit and integration tests across all tiers.
   - Run `./scripts/check.sh` ensuring 100.00% statement coverage.

## Outcome & Acceptance Evidence

All acceptance criteria met:
1. **Syntax Error Capture**: `load_file_config_with_diagnostics` captures `TOMLDecodeError` with parsed line, column, file path, and description into `ConfigDiagnostic` dataclasses.
2. **Explicit Inspection**: `/config` and `/config show` (including `--flat`, `--sources`, and filtered queries) display the diagnostic header prominently whenever configuration parse errors are detected.
3. **In-Buffer Frontier Warning**: `_execute_frontier_consequences` appends an inert warning block (`source=config.diagnostic`, `potency=inert`) as the final consequence node when diagnostics are present.
4. **History Deduplication**: `_has_config_diagnostic` checks both active `consequences` and prior `working` history so the warning is emitted only once per distinct error signature on a lineage.
5. **Coverage & Checks**: `./scripts/check.sh` passes completely with 100.00% statement coverage (26,046 statements), 3,877 unit tests, 17 acceptance tests, clean ruff lint, and clean mypy checks.

