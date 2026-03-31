## Goal

Have a runnable operator surface for `toas step` and `toas jump`.

## Scope

- Create `src/toas/cli.py`
- Implement `main()` with:
  - default -> `step`
  - explicit -> `step`, `jump`
- Wire entrypoint from `pyproject.toml`

## Behavior

- `toas step`:
  - reads `session.md` as the working proposal
  - reads `events.jsonl` as append-only history
  - appends any accepted transcript divergence to the log
  - emits only newly produced consequences to stdout
  - does not rewrite `session.md`

- `toas jump N`:
  - records or applies a manual binding override
  - does not alter existing log entries
  - does not rewrite transcript content

## Notes

- No argparse
- Keep the CLI thin; core semantics live below it
- `jump` is the explicit override for alignment/binding
- Missing-file bootstrap can stay minimal, but should not define the steady-state semantics

## Done When

- `uv run toas step` is invokable from the shell/editor
- `uv run toas jump N` is invokable from the shell/editor
- `:r !toas step` inserts only new consequences
