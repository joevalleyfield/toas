Filed as: 261111-dispatch-main-complexity
FKA:
AKA: dispatch_main C901 complexity; CLI dispatch table refactor
Legacy index:

keywords: cli, dispatch, complexity, C901, refactor, maintainability
Depends on:
Related: `261111-toas-new-edit-sessions` (the change that pushed it over the cap)

# dispatch_main is a complexity liability: replace the elif ladder with a dispatch table

Status: OPEN; design intent, awaiting a scoped refactor spike

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
