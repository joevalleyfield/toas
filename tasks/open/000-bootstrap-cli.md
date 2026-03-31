
## Goal

Have a runnable `toas step` command that executes without error and touches the expected files.

## Scope

- Create `src/toas/cli.py`
- Implement `main()` with:
  - default → `step`
  - explicit → `step`, `jump`
- Wire entrypoint from `pyproject.toml`

## Behavior

- `toas step`:
  - ensures `events.jsonl` exists
  - ensures `session.md` exists
  - prints placeholder output (e.g. "step not implemented")

- `toas jump N`:
  - prints placeholder

## Notes

- No argparse
- No real logic yet
- This is just making the operator invokable

## Done When

- `uv run toas step` runs without error
- Can be used via `:r !toas step` in vim
