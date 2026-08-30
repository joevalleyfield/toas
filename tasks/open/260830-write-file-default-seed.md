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
- Ensure the default seed renders both its callable signature and concise
  repo-work guidance from the existing shared sources.
- Preserve the existing `force`/`append` safety contract and newline-policy
  wording; do not weaken overwrite protection to make the prompt simpler.
- Keep effective hidden-tool filtering authoritative.
- Refresh the checked-in default-seed golden projection and focused prompt
  assertions.

## Acceptance Criteria

- `visible_tool_names(profile="core")` includes `write_file`.
- `pragmatic-default_v2` includes the effective `write_file` signature and
  its create/append/overwrite guidance.
- hiding `write_file` removes its signature and conditional guidance without
  affecting unrelated tools.
- full/debug profiles do not gain duplicate entries or divergent wording.
- the rendered seed continues to describe explicit overwrite safety and the
  shared file newline policy accurately.
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
