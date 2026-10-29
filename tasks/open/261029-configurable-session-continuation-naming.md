Filed as: 261029-configurable-session-continuation-naming
FKA:
AKA: session continuation naming; session rotation name format; session datetime slug
Legacy index:

keywords: runtime, configuration, active, session, rotation, vim

# Configurable Session Continuation Naming

Make session continuation naming configurable in session policy, defaulting to
`session-YYMMDD-HHMM-short-name` while supporting datetime-only and legacy date-slug
formats.

## Current Reality

When continuing a session via `session continue` (or `:ToasContinue` / `<leader>r` in Vim):
- `suggested_continuation_name` in `src/toas/runtime/session_rotation.py` generates names
  using `YYMMDD-slug` (e.g. `261029-focus-slug`), which creates `session-YYMMDD-short-name.md`.
- Operators frequently edit this suggestion manually to include or use hours and minutes
  (`YYMMDD-HHMM`), especially when running multiple sessions in the same day.
- `SessionPolicy` in `src/toas/config.py` does not currently expose a configuration field
  for continuation naming style or format.

## Desired Reality

- `SessionPolicy` in `src/toas/config.py` provides a `continuation_name_format` setting.
- The default format is `"datetime-slug"`, producing `YYMMDD-HHMM-short-name`
  (e.g., `261029-1628-short-name`).
- Named format options include:
  - `"datetime-slug"`: `YYMMDD-HHMM-short-name` (default)
  - `"datetime"`: `YYMMDD-HHMM`
  - `"date-slug"`: `YYMMDD-short-name` (legacy format)
  - `"slug"`: `short-name`
- `suggested_continuation_name` accepts `now: datetime | None = None` and
  `name_format: str = "datetime-slug"` to support deterministic testing and configurable formatting.
- `continue_session` respects the active session config and passes the configured
  format to `suggested_continuation_name`.
- `_resolve_target_path` safely handles names with or without `session-` prefix or `.md` suffix.

## Gap Analysis

- `SessionPolicy` lacks `continuation_name_format`.
- `_CHOICE_MAP` in `src/toas/config_parsing.py` needs choices for `session.continuation_name_format`.
- `suggested_continuation_name` hardcodes `strftime("%y%m%d")` and appends the slug without time.
- `continue_session` does not read `config.session.continuation_name_format`.

## Transformations

- Add `continuation_name_format: str = "datetime-slug"` to `SessionPolicy` in `src/toas/config.py`.
- Add choice map entry in `src/toas/config_parsing.py`.
- Update `suggested_continuation_name` and `continue_session` in `src/toas/runtime/session_rotation.py`.
- Update and add comprehensive tests in `tests/test_runtime_session_rotation.py` and `tests/test_config.py`.

## Evidence

- Unit tests for all continuation name formats (`datetime-slug`, `datetime`, `date-slug`, `slug`).
- Config serialization and choice validation tests.
- Full pytest test suite passes with 100% statement coverage.

## Next Actions

- Create and commit the open task file.
- Update `tasks/WORKBOARD.md` via `sync_workboard.py`.
- Implement `SessionPolicy.continuation_name_format` and rotation logic with tests.
