Filed as: 260830-write-file-default-seed
FKA:
AKA: write file core profile; default seed tool inventory; advertised tool parity
Legacy index:

keywords: projection, implementation, active, contract, usability, defaults, docs

Related: `474`; `260803-seed-prompt-composition-study`; `260709-write-file-force-overwrite-safety`

# Restore `write_file` To The Default Tool Seed

Add `write_file` to the effective core tool profile used by the default seed so
the advertised editing capability and the model-visible default inventory no
longer disagree.

## Source

Workspace inbox triage (`Documents/Journal/inbox.md`). Discovered 2026-08-29
during a tool audit.

## Current Contract

- `write_file` is registered and executable.
- full-profile capability guidance advertises create, append, and explicit
  overwrite behavior.
- the default `core` profile in `src/toas/capability_prompts.py` omits
  `write_file`, so `pragmatic-default_v2` does not render its signature or
  repo-work guidance.
- hidden-tool filtering already provides the policy mechanism for suppressing
  a core tool when a deployment should not expose it.

## Scope

- Add `write_file` to the core/default capability profile.
- Ensure the default seed renders its callable signature/defaults and the
  separate core repo-work surface renders concise guidance from the existing
  shared source.
- Preserve the existing `force`/`append` safety contract and newline-policy
  wording; do not weaken overwrite protection to make the prompt simpler.
- Keep effective hidden-tool filtering authoritative.
- Refresh the checked-in default-seed golden projection and focused prompt
  assertions.

## Acceptance Criteria

- `visible_tool_names(profile="core")` includes `write_file`.
- `pragmatic-default_v2` includes the effective `write_file` signature and
  safe append/overwrite defaults.
- the core repo-work capability surface includes the existing
  create/append/overwrite and newline-policy guidance.
- hiding `write_file` removes its signature and conditional guidance without
  affecting unrelated tools.
- full/debug profiles do not gain duplicate entries or divergent wording.
- the rendered prompt surfaces continue to describe explicit overwrite safety
  and the shared file newline policy accurately at their existing composition
  boundaries.
- focused prompt tests and the repository's required check set pass with the
  coverage gate intact.

## Allowed Write Surfaces

- `src/toas/capability_prompts.py`
- the checked-in `pragmatic-default_v2` golden projection
- focused prompt/capability tests
- this task file and mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- a before/after visible-tool inventory for the core profile;
- focused assertions for the default seed and hidden-tool projection;
- the full required check result;
- a progress note naming the closing commit.

## Progress

- 2026-08-30: Claimed for implementation. The initial trace points to the
  `_CORE_TOOLS` profile in `src/toas/capability_prompts.py`; focused prompt
  assertions and the checked-in `pragmatic-default_v2` golden projection will
  carry the contract change.
- 2026-08-30: Added `write_file` to `_CORE_TOOLS`. The effective inventory
  changed from `read_file, search, replace_block, apply_patch, shell,
  shell_script, capability_help, capture_task_thread` to `read_file, search,
  write_file, replace_block, apply_patch, shell, shell_script,
  capability_help, capture_task_thread`.
- 2026-08-30: The composition trace corrected one assumption in the intake
  task: `pragmatic-default_v2` embeds the shared tool-definition renderer but
  intentionally does not embed the separate on-demand repo-work page. The
  seed now renders the registered `write_file` signature plus its safe
  `append=false, force=false` defaults; the existing core repo-work renderer
  supplies the shared create/append/overwrite and newline-policy guidance.
  Pulling the complete repo-work page into every bootstrap seed was left out
  as unrelated prompt-composition expansion.
- 2026-08-30: Added focused coverage for default-seed visibility, hidden-tool
  filtering, core/debug/full uniqueness, the registered signature/defaults,
  and the shared repo-work safety guidance. Refreshed the checked-in golden
  projection.
- 2026-08-30: Verification passed: `tests/test_prompts.py` (67 tests), targeted
  coverage for `toas.capability_prompts` (100%), Ruff, mypy, and the full
  elevated suite (3026 passed, 9 deselected, 100% coverage). The unelevated
  full run first confirmed 3006 passing tests and was blocked only where the
  sandbox denied local socket binds or Vim's normal state-file access.
- 2026-08-30: Closed in change `zomouynr` (`feat(prompts): restore write-file
  to default seed`).

## Completion

The default/core prompt profile now exposes the already-registered
`write_file` capability without duplicating tool definitions or bypassing
effective hidden-tool policy. The bootstrap golden projection, on-demand
repo-work guidance, focused tests, type checks, and full suite agree on the
result.
