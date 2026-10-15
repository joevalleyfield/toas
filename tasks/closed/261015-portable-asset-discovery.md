# Portable Packaged Asset Discovery

Filed as: 261015-portable-asset-discovery
FKA:
AKA: Windows prompt discovery; slash-separated asset references
Legacy index:

keywords: tooling, hardening, historical, compatibility, windows, prompts

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-15; emit portable slash-separated packaged asset references

## Cause and Resolution

`list_packaged_assets` used `str(relative_path)`, returning backslashes on
Windows. Prompt prefix filtering and dynamic/static identity use slash-separated
logical references, so nested prompts disappeared from discovery even though
direct loading worked. Use `relative_path.as_posix()` in the shared loader,
covering prompt, procedure, and state-template discovery at their common seam.

## Evidence

- Reproduced failure in `test_list_prompt_assets_can_filter_by_prefix` and
  actual `uv run toas prompts session-start/start-here` before the fix.
- Added a failing nested-reference regression test that verifies portable
  identifiers and list/load round-trip behavior; now passes.
- 124 tests passed across assets, prompts, procedures, and the formerly failing
  CLI listing/top-level browse tests (`-o addopts= -q`).
- Targeted loader coverage: 28 tests passed, 32 statements, 100%, zero missing
  files using `scripts/targeted_coverage.py`.
- Ruff passed for both changed Python files.
- Inspected real CLI output: three distinct start-here prompts, canonical `/`
  identifiers, category, name, and useful descriptions. No traceback.

Native Windows verification is complete for this slice. POSIX verification of
the combined restoration remains a master-task closure requirement.
