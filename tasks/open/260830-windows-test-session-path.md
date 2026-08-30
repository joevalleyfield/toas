Filed as: 260830-windows-test-session-path
FKA:
AKA: Windows test compatibility; symlink-free session fixture; default session path tests
Legacy index:

keywords: tooling, migration, active, compatibility, windows, tests, defaults

Related: `260621-windows-shell-launcher-and-path-resolution`

# Windows-Compatible Default Session Path Tests

Make the CLI test setup work on Windows without requiring filesystem symlink
support.

## Current Reality

The autouse fixture `_link_default_session_path` in `tests/test_cli.py` creates
`.toas/session.md` as a symlink to the temporary working-directory
`session.md`:

```python
os.symlink("../session.md", default)
```

This was a compatibility workaround that kept older tests from needing to be
updated when default session-path behavior changed. Windows test runs may not
be able to create that symlink, and the workaround may now preserve obsolete
test assumptions rather than the behavior the tests should exercise.

## Desired Reality

The CLI tests should run on Windows without elevated symlink privileges and
should express the current default-session-path contract directly. Tests that
need a session file should create or select it through the supported path
configuration rather than relying on a linked duplicate.

## First Issue

- Remove or replace the `os.symlink` use in `_link_default_session_path`.
- Audit the tests that depend on the linked `.toas/session.md` and update their
  setup/assertions to match the current default-path semantics.
- Preserve coverage for bootstrap behavior and any intentional distinction
  between the workspace `session.md` and `.toas/session.md`.

## Exit Evidence

- The affected CLI tests pass on a Windows environment without symlink
  privileges.
- The fixture no longer requires `os.symlink`.
- Tests still prove the intended default session-path behavior rather than only
  proving that two paths happen to reference the same file.
