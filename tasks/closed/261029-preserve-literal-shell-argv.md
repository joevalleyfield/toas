Filed as: 261029-preserve-literal-shell-argv
FKA:
AKA: assistant shell literal argv; shell glob expansion removal; find path predicate
Legacy index:

keywords: tooling, implementation, closed, compatibility, shell

Parent: `261015-windows-compatibility-restoration`
Related: `260621-enable-shell-globbing`; `260621-windows-shell-launcher-and-path-resolution`

# Preserve Literal Shell Argv in Assistant Context

Preserve pre-tokenized `argv` arguments in assistant-driven `shell` tool execution
without Python-side glob expansion, preventing command corruption in search
predicates like `find ... -not -path '*/.*'`.

## Current Reality

The assistant `shell` tool executes commands via `execute_shell_call(..., context="assistant")`
in `src/toas/tools_cluster/shell_ops.py`.

- `execute_shell_call` calls `_expand_globs_in_argv(argv)` on validated arguments.
- Any argument containing wildcard characters (`*`, `?`, `[`) is passed to Python's
  `glob.glob(part)`.
- If any workspace paths match the pattern (e.g. `attachments/.jj` or `tasks/.toas`
  for `*/.*`), the single pattern argument is replaced with the matched filesystem paths.
- On Windows, `glob.glob` produces native backslash-separated paths (e.g. `attachments\.jj`).
- When utilities expecting literal patterns (such as `find -path`, `find -name`, `grep`, or `sed`)
  receive expanded paths, execution fails with errors such as:
  `/usr/bin/find: paths must precede expression: attachments\.jj`
  `/usr/bin/find: possible unquoted pattern after predicate '-path'?`

## Desired Reality

The assistant-callable plain `shell` tool adheres strictly to its documented argv-oriented
contract:

- Pre-tokenized `argv` elements provided in tool arguments are passed literally to the
  underlying subprocess without undergoing Python-level glob expansion.
- Patterns intended for utilities (such as `find . -not -path '*/.*'` or `find . -name '*.py'`)
  reach the target binary intact.
- Shell-native wildcard expansion remains reserved for user shorthand (`$ ...`) via
  `run_user_shell` and assistant multiline scripts via `shell_script`.

## Gap Analysis

- `_expand_globs_in_argv(argv)` was introduced during early glob exploration and retained
  in `execute_shell_call` even after `260621-enable-shell-globbing` established that
  assistant-callable `shell` should remain an argv-oriented tool surface.
- `_expand_globs_in_argv` expands wildcards in `os.getcwd()` rather than respecting `cwd`,
  and cannot distinguish shell wildcards from utility pattern flags.
- Removing `_expand_globs_in_argv(argv)` from `execute_shell_call` (or removing the unused
  helper) restores literal `argv` semantics for the assistant `shell` tool.

## Known Facts / Assumptions / Unknowns

### Known Facts
- `execute_shell_call(..., context="assistant")` unconditionally runs `argv = _expand_globs_in_argv(argv)`.
- `_expand_globs_in_argv` is only referenced in `src/toas/tools_cluster/shell_ops.py` and `tests/test_tools_shell_ops.py`.
- User shell shorthand (`$ ...`) handles globbing via `needs_shell` and `shell_launcher_argv` (`sh -lc`), not via `_expand_globs_in_argv`.
- `shell_script` tool executes through the shell runtime where wildcard expansion is natively supported.

### Assumptions
- Assistant models calling `shell` with `argv: [...]` supply pre-tokenized arguments and expect them to be delivered literally to the target binary.

### Unknowns
- None identified.

## Transformations

- Remove `_expand_globs_in_argv(argv)` call from `execute_shell_call` in `src/toas/tools_cluster/shell_ops.py`.
- Clean up or update `_expand_globs_in_argv` references in `src/toas/tools_cluster/shell_ops.py` and `tests/test_tools_shell_ops.py`.
- Add regression tests verifying that literal wildcards in assistant `argv` (such as `find . -not -path '*/.*'`) are preserved and executed without glob expansion.

## Decisions

- Assistant plain `shell` execution strictly preserves `argv` as pre-tokenized literal strings.
- Removed `_expand_globs_in_argv` from `execute_shell_call` in `src/toas/tools_cluster/shell_ops.py` to prevent filesystem match corruption of pattern arguments (`-path`, `-name`, etc.).
- Wildcard expansion remains supported for user-facing `$ ...` shorthand and `shell_script` multiline scripts.

## Evidence

- Unit regression in `tests/test_tools_shell_ops.py`: `test_execute_shell_call_assistant_preserves_literal_wildcards_in_argv` verifies literal pass-through when matching filesystem paths (`attachments/.jj`, `test.py`) exist on disk.
- End-to-end execution of `find . -maxdepth 2 -not -path '*/.*'` returns exit code 0 and clean path output without GNU find `paths must precede expression` errors.
- Full pytest test suite (3,595 passed, 17 acceptance passed) with 100.00% statement coverage across all 23,010 statements and zero missing files.
- `ruff check src tests` and `mypy` pass cleanly with zero warnings or errors.

## Closure

Closed on 2026-10-29. Pre-tokenized arguments in assistant-callable `shell` are preserved literally without Python-side glob expansion, eliminating command corruption for utilities taking pattern arguments such as `find -path`.
