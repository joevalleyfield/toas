Filed as: 261111-dispatch-main-complexity
FKA:
AKA: dispatch_main C901 complexity; CLI dispatch table refactor
Legacy index:

keywords: cli, dispatch, complexity, C901, refactor, maintainability
Depends on:
Related: `261111-toas-new-edit-sessions` (the change that pushed it over the cap)

# dispatch_main is a complexity liability: replace the elif ladder with a dispatch table

Status: CLOSED (implemented); `dispatch_main` is a command -> handler dispatch table
Follow-on: (none)

## Objective

`src/toas/cli_dispatch.py::dispatch_main` is a single top-to-bottom `if/elif`
chain that now sits at the C901 mccabe cap (80; it was pushed over by the
`new`/`edit` addition and pulled back under it by extracting
`parse_new_options`/`parse_edit_options` into `cli_dispatch_ops.py`). Every
new subcommand adds more branches to the same function, so the complexity
will keep climbing. This is a structural smell, not an acute defect.

Refactor `dispatch_main` from a vertical `elif` ladder into a
command -> handler dispatch table (dict of `command: (parser, runner)`
descriptors, or a list of `(command, handler)` pairs) so that adding a
subcommand is a table-row addition rather than a new branch in an
already-oversized function. This aligns with the repo's own
"Tabular declarations over vertical boilerplate" / "Diverge on data,
converge on instantiation" bias.

## Why now / trigger

- `261111-toas-new-edit-sessions` shipped `new`/`edit`; the inline parsing
  pushed `dispatch_main` to C901 (82 > 80), forcing the parser extraction.
  The extraction was the acute fix; the table refactor is the durable one.
- The function already has a long tail of `elif` arms, several of which
  build a `kwargs` dict and then call a dep — a pattern that maps cleanly
  to table rows.

## Scope (design truth)

- Move the per-command argv parsing + dep call into a dispatch table so
  `dispatch_main` becomes: resolve argv[0], look up the handler, run it.
- Preserve exact behavior: `--help`/`-h` routing, default-to-`step`, the
  `is None` "not configured" guards for optional deps, and the usage-string
  errors.
- Keep `DispatchDeps` as the injection seam; the table rows bind against it.
- Do not change the CLI contract, help text, or any public behavior.

## Out of scope

- Not a rename/formatting pass; the value is in the structural change
  (ladder -> table) that lowers `dispatch_main`'s complexity and makes new
  commands a one-line table addition.

## Verification

- `uv run pytest` green; `./scripts/check.sh` green; 100.00% statement
  coverage.
- `dispatch_main` mccabe complexity drops well under the C901 cap.
- The existing `tests/test_cli_dispatch.py` dispatch/help table must pass
  unchanged (it already pins the command->behavior contract).
- Add a test that registering a new command is a table-row addition
  (meta-verification that the seam is table-shaped).

## Implementation Notes (shipped)

- `src/toas/cli_dispatch.py` is now a **command -> handler dispatch table**.
  Every `elif` arm became a module-level `def _handle_<cmd>(argv, deps) ->
  None`; a module-level `_COMMANDS: dict[str, Callable[[list[str],
  DispatchDeps], None]]` maps command (and alias) names to handlers.
  `dispatch_main` shrank to: default-to-`step` (`cmd or ["step"]`), the two
  centralized `--help`/`-h` guards (argv[0] and argv[1] forms, via
  `cli_usage.get_subcommand_help`), the table lookup, and the
  `unknown command:` error.
- **Aliases are first-class registry keys**: `service -> _handle_daemon`,
  `transport -> _handle_host` (same handler object as the primary). `step-async`
  stays handled inside `_handle_step` (its parser already branches on it), so it
  is not a separate key.
- `parse_surface_options` remains a module-level name in `cli_dispatch` so the
  `test_dispatch_surface_with_reason_non_bind` monkeypatch of
  `toas.cli_dispatch.parse_surface_options` keeps working. Public seam unchanged:
  `dispatch_main` + `DispatchDeps` (imported by 4 test files).
- **Complexity (mccabe, per-function; gate aggregates as max):**
  `dispatch_main` **82 -> 7**; the max function in the module is
  `_handle_step` at **14** (async/sync split + both-session guard + kwargs
  building — the one arm that was always the most tangled). `_handle_graph` /
  `_handle_transcript` are 6 each (conditional kwargs). All other handlers are
  <=5. No function is near the C901 cap (80); the complexity is distributed
  across ~29 named, individually-bounded units instead of concentrated in one
  82-complexity function.
- **Meta-test** `test_dispatch_is_a_command_table` pins the table shape:
  `_COMMANDS` is a `dict`; alias keys (`service`/`transport`) are first-class
  entries sharing handlers with their primary; a registered command dispatches
  through the table; an unregistered command raises the exact
  `unknown command:` error from the dispatcher (not a branch).
- Verified: full suite **4062 passed / 100.00% coverage**; `./scripts/check.sh`
  green (ruff + mypy). The 49 `test_cli_dispatch.py` cases pass unchanged
  (every command routing, help form, usage error, and not-configured guard
  preserved).
