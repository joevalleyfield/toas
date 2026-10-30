Filed as: 261030-shell-argv-scalar-coercion
FKA:
AKA: shell argv scalar coercion; shell argv integer arguments; shell argv validation error
Legacy index:

keywords: runtime, tools, shell, validation, coercion, error-diagnostics

Parent:
Depends on:
Blocks:
Blocked by:
Related:

# Shell Argv Scalar Coercion and Diagnostic Validation

Auto-coerce numeric and boolean scalars in `shell` `argv` to strings, and provide
clear, pinpoint diagnostic error messages when an `argv` element is invalid.

## Current Reality

1. In YAML tool calls, unquoted numbers (e.g. `- 3` for `-maxdepth 3`) are
   parsed as `int` or `float`, and unquoted boolean literals (`true`/`false`)
   are parsed as `bool`.
2. `validate_shell_args()` in `src/toas/tools_cluster/shell_ops.py` checks:
   ```python
   if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
       raise RuntimeError("invalid arguments for tool shell: argv must be a non-empty list[str]")
   ```
   This collapses three distinct failure modes into one generic error message:
   - `argv` is not a list
   - `argv` is empty
   - an element inside `argv` is not a `str`
3. When an operator or LLM passes `-maxdepth 3`, TOAS rejects the call with
   `[ERROR] shell: invalid arguments for tool shell: argv must be a non-empty list[str]`.
   Because `argv` is visibly a non-empty list, the operator is misled into believing
   the list itself was not recognized or parsed, rather than realizing an individual
   element was an integer instead of a string.
4. User shell argument resolution (`_resolve_user_argv` and `run_user_shell`) has
   the same strict string requirement and collapses errors similarly.

## Desired Reality

1. `validate_shell_args()`, `_resolve_user_argv()`, and `run_user_shell()` normalize
   `argv` elements:
   - string elements remain strings as-is
   - boolean elements (`bool`) normalize to lowercase `"true"` or `"false"`
   - numeric scalar elements (`int`, `float`) coerce to strings (e.g. `3` -> `"3"`)
2. If `argv` is not a list or is empty, the error clearly states that `argv` must be a
   non-empty list:
   `invalid arguments for tool shell: argv must be a non-empty list[str]`
3. If an `argv` element is of an unsupported type (such as a mapping, list, or `None`),
   the error pinpoints the exact element index, value, and invalid type:
   `invalid arguments for tool shell: argv element at index {idx} ({part!r}) must be a string or scalar, got {type_name}`
4. Repair hint rendering in `rendering.py` recognizes both `argv must be a non-empty list[str]`
   and invalid element errors to offer the shell repair template.
5. All tests pass with 100.00% statement coverage via `./scripts/check.sh`.

## Acceptance Criteria

- [x] Unquoted integers and numbers in `argv` (e.g. `find . -maxdepth 3`) execute successfully without requiring string quotes in YAML.
- [x] Booleans in `argv` coerce to `"true"` / `"false"`.
- [x] Invalid non-scalar elements in `argv` raise an error that identifies the element index, value representation, and type name.
- [x] Structural errors (missing `argv`, non-list, empty list) retain their contract and repair hint guidance.
- [x] Both assistant tool execution and user shell paths share this normalization.
- [x] Tests cover coercion of int/float/bool, pinpoint errors on invalid elements, and full test suite passes with 100.00% coverage.

## Verification Evidence

1. `normalize_shell_argv()` added to `src/toas/tools_cluster/shell_ops.py` to normalize strings, booleans, and numeric scalars (`int`, `float`), and pinpoint unsupported types by index and type name.
2. `validate_shell_args()`, `run_user_shell()`, and `_resolve_user_argv()` integrated with `normalize_shell_argv()`.
3. `_repair_hint_for_error()` in `src/toas/tools_cluster/rendering.py` updated to provide repair hints on element-level errors as well as list-level errors.
4. Targeted unit tests in `tests/test_tools_shell_ops.py` and `tests/test_tools_rendering.py` cover scalar coercion (`int`, `float`, `bool`), pinpoint error messages on dict/NoneType/list elements, and repair hint formatting.
5. Full test suite `./scripts/check.sh` passed cleanly with 100.00% statement coverage (3616 passed, 0 statements missed across 23097 stmts), ruff clean, and mypy clean.
6. End-to-end artifact inspection confirmed unquoted `-maxdepth 3` executes with `[OK] shell: exit=0`, and invalid element dictionaries yield pinpoint diagnostic errors alongside next-valid-shape repair hints.
