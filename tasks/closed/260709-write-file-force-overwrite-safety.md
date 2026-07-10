Filed as: 260709-write-file-force-overwrite-safety
FKA:
AKA: write_file force flag; untracked overwrite refusal; VCS-aware write safety; write_file append mode
Legacy index:

keywords: tooling, hardening, historical, correctness, safety, write_file, append, policy

Parent: `260622-tool-write-newline-policy-and-windows-lf-defaults`
Related: `260418-weak-model-safe-apply-patch-contract`; `260515-apply-patch-windows-crlf-hardening`

# Write File Write-Mode Safety

## Current Reality

`write_file` currently creates parent directories and overwrites any existing
target unconditionally.

That is mechanically simple, but it is too permissive for a tool that may be
driven by weaker models or by an operator who expects explicit friction before
destroying local work. In particular, an existing file that is present in the
workspace but not yet captured durably in version control is easy to clobber
accidentally.

At the same time, the current surface has no first-class non-destructive append
mode, so "add text to this file" and "replace this file" are both forced
through the same overwrite-shaped operation.

## Desired Reality

`write_file` should expose explicit text-writing modes with safety tied to the
destructiveness of the operation:

- safe create for missing files
- safe overwrite when the current file bytes are already captured durably in
  `jj`, including the working-copy commit `@`
- refused destructive overwrite when the existing file content is only
  filesystem-local, unless the caller supplies an explicit `force`-style opt-in
- lenient `append` for non-destructive text append, without requiring `force`

The newline-style policy is a separate axis:

- when appending to an existing file, `append` should retain the file's
  detected predominant newline style unless an overriding config policy says
  otherwise
- if config explicitly requires a newline style, it is acceptable to normalize
  the full file content in-policy as part of the append/write operation

## Scope

- define the write-mode contract for `write_file`
- define default write, `force`, and `append` behavior and mutual exclusivity
- define which repository/file states count as safe overwrite by default
- define how TOAS decides whether existing bytes are already captured durably
  in repository history
- define the `force` and `append` argument shape and error/response messaging
- identify tests for safe create, safe overwrite, refused overwrite, and
  newline-aware append

## Non-Goals

- newline-style policy for created or overwritten files
- propagating this contract to `replace_range`, `replace_block`, `apply_patch`,
  or other write surfaces in the same task
- hidden heuristics that silently rewrite around refusal conditions

## Final Contract

- missing target path: safe create
- existing file whose current bytes are already captured in `jj`, including
  `@`: safe overwrite
- existing file whose current bytes are already captured in Git `HEAD`: safe
  overwrite
- existing file whose current bytes are not captured in repository history:
  refuse destructive overwrite unless `force=true`
- `append=true`: safe, lenient, text-append mode that does not require `force`
- `force=true` and `append=true`: invalid together
- `append=true` creates the file when it does not exist
- append to an existing file should retain the detected predominant newline
  style unless config explicitly overrides that style

## Progress Notes

- 2026-07-09: Implemented `write_file` write-mode safety for the public tool
  surface. Default overwrite now refuses when current filesystem content is not
  proven captured in repository history; `force=true` allows destructive
  replacement; and `append=true` is a lenient non-destructive text-append path
  that can also create a missing file.
- 2026-07-09: For expediency and practicality, the implementation accepts
  either `jj file show -r @` parity or Git `HEAD` parity as the recoverability
  signal. If neither proves recoverability, overwrite remains fail-closed
  unless `force=true`.
- 2026-07-09: The implementation returns an explicit `mode` so callers can
  distinguish `create`, `append`, `safe_overwrite`, and `force_overwrite`
  outcomes.

## Exit Evidence

- [x] the safe-overwrite vs refused-overwrite states are named explicitly
- [x] the `force` and `append` contracts are chosen and documented
- [x] diagnostics distinguish create, safe overwrite, refused overwrite, force
      overwrite, and append paths
- [x] focused tests cover filesystem-local existing-file refusal, explicit
      force success, safe overwrite for `jj`-captured content including `@`,
      Git `HEAD` parity, and newline-aware append behavior

## Closure Notes

- This task closes only the `write_file` seam.
- The broader question of whether analogous overwrite guards should propagate
  to other edit surfaces remains separate follow-on work rather than hidden
  under this task's acceptance.
