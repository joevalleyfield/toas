# Preserve Control Result Scope in Vim Finalization

Filed as: 261010-vim-control-result-empty-user
FKA:
AKA: empty user before control result; Vim result scope prefix
Legacy index:

keywords: surface, hardening, active, correctness, vim, transcript, projection

Related: `569-frontier-empty-transcript-block-normalization`; `260710-vim-command-transcript-dedup`

Status: OPEN; preserve already scoped result projections when Vim finalizes a successful run

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
