# Preserve Control Result Scope in Vim Finalization

Filed as: 261010-vim-control-result-empty-user
FKA:
AKA: empty user before control result; Vim result scope prefix
Legacy index:

keywords: surface, hardening, historical, correctness, vim, transcript, projection

Related: `569-frontier-empty-transcript-block-normalization`; `260710-vim-command-transcript-dedup`

Status: CLOSED — 2026-10-20

## Evidence

Observed in the dogfood transcript
`.toas/session-20261010-1247-preview-request-pretty-inspection.md`
after `/shell allow grep`. The corresponding history records are control
message `n100`, its `shell_scope_grant`, and successful run `9305bed01073`;
there is no empty user event in that run.

The runtime renders `## TOAS:CONTROL\n\n## RESULT\n\n...`.
`s:toas_finalize_success_text()` in `vim/plugin/toas.vim` then prepends
`## TOAS:USER\n\n\n\n` whenever the text contains `## RESULT` but no
`## TOAS:USER`, ignoring the existing control scope. A temporary headless
Vim probe using the actual result text reproduced the exact transcript suffix.

## Scope

Repair Vim success finalization and add regression coverage. Review the
extra prefix rule alongside `s:toas_ensure_projection_for_lane()`, which
already scopes bare result output. Keep runtime result provenance intact.
Do not rewrite dogfood history or repair unrelated session failures here.

## Acceptance Criteria

- A control-scoped result remains control-scoped after successful finalization,
  without an injected empty user section.
- Bare result output still receives its intended user scope, and existing
  user-scoped results retain exactly one scope header.
- Cover the successful projection-event path in Vim, including terminal
  replacement of the provisional run region.
- Inspect the concrete final Vim buffer for a control slash-command result;
  run the relevant Vim regressions and repository checks before closure.

## Progress

- Root cause and exact reproduction recorded; implementation remains open.

## Completion — 2026-10-20

The existing `toas_ensure_projection_for_lane` already preserves CONTROL and
other transcript scopes and supplies USER scope for bare results. A redundant
later fallback in `toas_finalize_success_text` undid that behavior. Removed
that fallback, preserving the existing shared scoping helper.

A regression through projection-event application and successful terminal
replacement first reproduced the extra empty USER section for CONTROL output;
bare and USER-scoped controls passed. All three now pass with the provisional
RUN region removed. Inspected the actual final Vim buffer: the original user
command is followed directly by CONTROL and RESULT, with no empty user event.

Verification: `.codex-local/bin/uvt run bash scripts/check.sh` — 3,595 passed,
nine skipped, 17 deselected; 100.00% statement coverage. All 17 acceptance
scenarios, Ruff and mypy passed on macOS.
