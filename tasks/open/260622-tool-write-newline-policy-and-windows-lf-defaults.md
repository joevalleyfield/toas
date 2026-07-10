Filed as: 260622-tool-write-newline-policy-and-windows-lf-defaults
FKA:
AKA: write_file CRLF; tool-created mixed endings; windows tool write newline policy
Legacy index:

keywords: tooling, hardening, active, compatibility, newline, windows, write_file, patch

Related: `513`; `303`; `260622-staged-replay-trailing-edge-newline-healing`; `260709-write-file-force-overwrite-safety`

# Tool Write Newline Policy And Windows LF Defaults

## Current Reality

On Windows, tool-created or tool-overwritten file content can pick up CRLF line
endings via Python text-mode defaults even when the surrounding repository and
editor workflow are LF-oriented.

This is undesirable because TOAS is often being driven from Vim in LF-ended
files, `jj`/diff workflows are line-ending-sensitive in practice, and mixed
endings accumulate repo noise even when downstream tools are technically
tolerant.

## Desired Reality

New content written by file-writing tool calls should follow an explicit TOAS
newline policy rather than inheriting host-platform defaults blindly.

At minimum, LF-oriented repositories should not accumulate mixed endings simply
because a Windows host created or overwrote content through `write_file` or a
similar tool surface.

The policy should be configurable through the standard TOAS config surfaces and
precedence chain rather than hidden in tool-local behavior.

## Gap Analysis

- `run_write_file(...)` currently uses `Path.write_text(...)`, which will use
  platform-default text-mode newline handling.
- Session/transcript writing already has newline-style-aware helpers, but tool
  file creation/overwrite paths do not obviously reuse that policy.
- We have not yet decided whether the right contract is:
  - always write LF for tool-created content
  - preserve existing file newline style on overwrite
  - expose configurable policy with sensible defaults

## Known Facts

- `src/toas/tools_cluster/basic_ops.py` currently writes tool-created file
  content via `path.write_text(content, encoding="utf-8")`.
- Runtime/session writing already has explicit newline-style helpers in
  `src/toas/runtime/session_file_edges.py` and
  `src/toas/runtime/rendering_edges.py`.
- There is already an open Windows/CRLF task for `apply_patch` (`513`), but
  this seam is about write-surface defaults and mixed-ending creation, not
  patch matching diagnostics.

## Questions

- Should new files written by tool calls default to LF on all platforms?
- Should overwrites preserve the existing file’s newline style when the target
  file already exists?
- Which tool surfaces besides `write_file` need to share the same policy?

## Decisions

- This wants an explicit config surface, resolved through the standard TOAS
  config priority locations, not a hidden platform-default behavior.
- The remaining design question is the default and overwrite behavior, not
  whether the policy is configurable.

## Progress Notes

- 2026-07-09: Landed a first implementation slice for `write_file` newline
  policy. Added `tool_writes.newline_style = "auto" | "lf" | "crlf"` through
  the standard config surfaces; `auto` preserves the detected newline style of
  an existing target file and otherwise defaults new files to LF.
- 2026-07-09: This slice intentionally does not yet implement overwrite-safety
  / `force` behavior or append mode; those remain tracked separately in
  `260709-write-file-force-overwrite-safety`.

## Follow-Ons

- `260709-write-file-force-overwrite-safety` now carries the separate
  overwrite-refusal / `force` semantics question so this task can stay focused
  on newline-policy ownership and defaults.

## Remaining Evidence

Ready to close when:

- the newline policy is shared intentionally across the remaining relevant
  file-writing tool surfaces, or the exceptions are written down explicitly
- representative Windows-focused tests cover the adopted shared-policy seams,
  not only `write_file`
- docs/help text reflect the now-real `tool_writes.newline_style` policy where
  operators would expect to discover it

## Next Actions

- Inventory file-writing tool surfaces that still rely on platform-default
  text-mode writes.
- Decide which of those surfaces should adopt `tool_writes.newline_style`
  unchanged versus which should remain intentionally separate.
- Update operator-facing help/docs once the shared-policy boundary is settled.
